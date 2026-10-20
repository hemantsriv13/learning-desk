"""Test setup: a throwaway database per test, and no real network calls.

Every test runs against a fake provider. Nothing here contacts Anthropic.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from learning_desk import db, provider  # noqa: E402


class FakeProvider:
    """Stands in for provider.send(). Queue up replies; every request is recorded."""

    def __init__(self):
        self.requests: list[dict] = []
        self.replies: list = []

    def reply(self, payload, **meta):
        text = payload if isinstance(payload, str) else json.dumps(payload)
        self.replies.append(provider.ProviderResponse(
            text=text, returned_model=meta.get("model", "fake-model-for-tests"),
            stop_reason="end_turn", usage={"input_tokens": 100, "output_tokens": 50},
            raw=json.dumps({"fake": True, "content": text})))

    def fail(self, message="Simulated provider outage"):
        self.replies.append(provider.ProviderError(message))

    def __call__(self, request):
        self.requests.append(request)
        if not self.replies:
            raise AssertionError("The app made a model call the test did not expect")
        item = self.replies.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("LEARNING_DESK_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "placeholder-not-a-real-key")
    monkeypatch.setenv("LEARNING_DESK_MODEL", "test-model")
    fake = FakeProvider()
    monkeypatch.setattr(provider, "send", fake)
    db.init_db()
    yield fake


@pytest.fixture
def fake(isolated):
    return isolated


REVIEW_OK = {
    "main_takeaway": {"text": "The API does not remember earlier requests; the client resends the history.",
                      "section_refs": [3]},
    "clarification": {"text": "Your explanation says the server stores history, but your test suggests "
                              "it may not.", "section_refs": [2, 3]},
    "next_step": {"kind": "task", "text": "Send the same question twice, once with the history included."},
    "supporting_evidence": [{"text": "A second, separate request did not know the name.", "section_refs": [3]}],
    "general_explanations": [{"topic": "Statelessness", "explanation": "Each request stands alone."}],
}

# A review in the original review-v1 format, as stored before reviews were shortened.
REVIEW_V1_OK = {
    "summary": "The session tests whether the API keeps conversation state.",
    "observations": [{"text": "A second, separate request did not know the name.", "section_refs": [3]}],
    "interpretations": [{"text": "The learner thinks the server stores history.", "section_refs": [2]}],
    "possible_gaps": [{"hypothesis": "State may live in the client, not the server.",
                       "how_to_check": "Send the history yourself and compare.", "section_refs": [2, 3]}],
    "general_explanations": [{"topic": "Statelessness", "explanation": "Each request stands alone."}],
    "suggested_experiments": [{"text": "Count input tokens as history grows.", "section_refs": []}],
    "suggested_next_steps": [{"kind": "task", "text": "Plot input_tokens against message count"},
                             {"kind": "question", "text": "Where does ChatGPT store history?"}],
}

QUESTIONS_OK = {"questions": [
    {"kind": "limitations", "question": "When would resending history fail?"},
    {"kind": "explanation", "question": "Explain why the second request forgot the name."},
    {"kind": "application", "question": "How would you design memory for a support bot?"},
]}

FEEDBACK_OK = {
    "explains_well": ["States that each request is independent."],
    "missing_or_possibly_incorrect": [{"point": "Context limits", "why": "Not mentioned."}],
    "follow_up_exercise": "Send 50 messages and watch input_tokens.",
}


def make_session(**overrides) -> int:
    fields = {"title": "Context windows", "topic": "LLM state", "goal": "Why does it forget?",
              "explanation": "The server stores history.",
              "notes": "First block.\n\nSecond block with a result.\n\n```python\nx = 1\n\ny = 2\n```",
              "sources": "https://example.com/a"}
    fields.update(overrides)
    return db.create_session(**fields)


def store_v1_review(session_id: int) -> int:
    """Insert a review-v1 record directly, the way older versions of the app stored it."""
    from learning_desk import ai
    snapshot_id, _, _ = ai.prepare_snapshot(session_id)
    return db.insert_ai_call({
        "session_id": session_id, "snapshot_id": snapshot_id, "action": "review",
        "prompt_version": "review-v1", "requested_model": "old-model", "returned_model": "old-model",
        "request_json": "{}", "raw_response": json.dumps(REVIEW_V1_OK), "status": "ok",
        "parsed_json": json.dumps(REVIEW_V1_OK), "elapsed_ms": 1000})
