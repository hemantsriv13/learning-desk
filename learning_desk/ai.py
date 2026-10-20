"""The three AI actions: review a session, generate questions, give answer feedback.

Every action follows the same steps:
  1. Read the SAVED session from the database (never unsaved text on screen).
  2. Freeze it as a snapshot and number its sections.
  3. Build the request: fixed instructions in `system`, session content in `messages`.
  4. Send it once (provider.send). No retries.
  5. Parse and validate the reply against a schema.
  6. Record everything in ai_calls, whether it worked or not.

Your notes are never modified here. AI output is stored only in ai_calls,
question tables and (when you accept a suggestion) the queue.
"""

import json
import time
from dataclasses import dataclass, field

from pydantic import BaseModel, ValidationError

from . import db, prompts, provider, sections


@dataclass
class AIResult:
    ok: bool
    call_id: int
    error: str | None = None
    parsed: BaseModel | None = None
    warnings: list[str] = field(default_factory=list)


def prepare_snapshot(session_id: int) -> tuple[int, dict, list[dict]]:
    session = db.get_session(session_id)
    if session is None:
        raise ValueError(f"Session {session_id} does not exist")
    content = sections.build_snapshot_content(session, db.list_queue(session_id=session_id))
    numbered = sections.number_sections(content)
    content["sections"] = numbered
    snapshot_id = db.get_or_create_snapshot(session_id, content)
    return snapshot_id, content, numbered


def _session_block(content: dict, numbered: list[dict]) -> str:
    return f"<session>\n{sections.render_sections(content, numbered)}\n</session>"


def _run(*, action: str, version: str, instructions: str, schema: dict, model_cls: type[BaseModel],
         session_id: int, snapshot_id: int, user_text: str, question_id: int | None = None) -> AIResult:
    request = provider.build_request(system=instructions, user_text=user_text, schema=schema)
    record = {
        "session_id": session_id,
        "snapshot_id": snapshot_id,
        "question_id": question_id,
        "action": action,
        "prompt_version": version,
        "requested_model": request["model"],
        "request_json": provider.redact(request),
    }

    started = time.perf_counter()
    try:
        response = provider.send(request)
    except provider.ProviderError as e:
        record.update(_response_fields(e.raw, e.returned_model, e.stop_reason, e.usage))
        return _fail(record, started, str(e))
    except Exception as e:  # anything unexpected is still recorded, never hidden
        return _fail(record, started, f"Unexpected error: {type(e).__name__}: {e}")
    record.update(_response_fields(response.raw, response.returned_model, response.stop_reason, response.usage))

    try:
        parsed = model_cls.model_validate(json.loads(response.text))
    except (json.JSONDecodeError, ValidationError) as e:
        return _fail(record, started, "The model's reply did not match the expected format, so it was "
                                      f"not used. Your notes are unchanged. Details: {e}")

    record["elapsed_ms"] = _elapsed_ms(started)
    record["status"] = "ok"
    record["parsed_json"] = parsed.model_dump_json(indent=2)
    call_id = db.insert_ai_call(record)
    return AIResult(ok=True, call_id=call_id, parsed=parsed)


def _response_fields(raw, returned_model, stop_reason, usage) -> dict:
    usage = usage or {}
    return {
        "raw_response": raw,
        "returned_model": returned_model,
        "stop_reason": stop_reason,
        "usage_json": json.dumps(usage) if usage else None,
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
    }


def _elapsed_ms(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)


def _fail(record: dict, started: float, message: str) -> AIResult:
    record.update(status="error", error=message, elapsed_ms=_elapsed_ms(started))
    return AIResult(ok=False, call_id=db.insert_ai_call(record), error=message)


# ---------------------------------------------------------------- actions

def review_session(session_id: int) -> AIResult:
    snapshot_id, content, numbered = prepare_snapshot(session_id)
    result = _run(action="review", version=prompts.REVIEW_VERSION, instructions=prompts.REVIEW_INSTRUCTIONS,
                  schema=prompts.REVIEW_SCHEMA, model_cls=prompts.Review, session_id=session_id,
                  snapshot_id=snapshot_id, user_text=_session_block(content, numbered))
    if result.ok:
        known = {s["id"] for s in numbered}
        unknown = sorted({r for r in result.parsed.all_refs() if r not in known})
        if unknown:
            # Keep the review, but flag citations that point at nothing.
            result.warnings.append("The model cited section numbers that do not exist in this snapshot: "
                                   + ", ".join(f"S{r}" for r in unknown))
        # An unusable highlight is minor: recorded for Technical details, not shown as a warning.
        recorded = result.warnings + result.parsed.emphasis_notes()
        if recorded:
            _save_warnings(result.call_id, recorded)
    return result


def generate_questions(session_id: int) -> AIResult:
    snapshot_id, content, numbered = prepare_snapshot(session_id)
    result = _run(action="questions", version=prompts.QUESTIONS_VERSION,
                  instructions=prompts.QUESTIONS_INSTRUCTIONS, schema=prompts.QUESTIONS_SCHEMA,
                  model_cls=prompts.QuestionSet, session_id=session_id, snapshot_id=snapshot_id,
                  user_text=_session_block(content, numbered))
    if result.ok:
        db.create_question_set(session_id, snapshot_id, result.call_id,
                               [q.model_dump() for q in result.parsed.questions])
    return result


def answer_feedback(question_id: int) -> AIResult:
    question = db.get_question(question_id)
    if question is None:
        raise ValueError(f"Question {question_id} does not exist")
    if not question["answer"].strip():
        raise ValueError("Save an answer before asking for feedback")
    session_id = db.session_id_for_question(question_id)
    snapshot_id, content, numbered = prepare_snapshot(session_id)
    user_text = (f"{_session_block(content, numbered)}\n\n"
                 f"<question kind=\"{question['kind']}\">\n{question['text']}\n</question>\n\n"
                 f"<answer>\n{question['answer']}\n</answer>")
    return _run(action="answer_feedback", version=prompts.FEEDBACK_VERSION,
                instructions=prompts.FEEDBACK_INSTRUCTIONS, schema=prompts.FEEDBACK_SCHEMA,
                model_cls=prompts.AnswerFeedback, session_id=session_id, snapshot_id=snapshot_id,
                user_text=user_text, question_id=question_id)


def _save_warnings(call_id: int, warnings: list[str]) -> None:
    db.set_ai_call_warnings(call_id, json.dumps(warnings))
