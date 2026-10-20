# Learning Desk

A local notebook for an AI learning journey. Capture a session, ask a model to review it,
answer understanding questions, and keep a queue of what to revisit.

Start session → capture notes → request AI feedback → answer questions → save next steps → return later.

## Setup and launch

Requires Python 3.10 or newer.

**Windows (PowerShell)**

```powershell
git clone <your-repo-url> learning-desk
cd learning-desk
python -m venv .venv                                      # once
.venv\Scripts\python -m pip install -r requirements.txt   # once
.venv\Scripts\python -m streamlit run app.py
```

**macOS / Linux**

```bash
git clone <your-repo-url> learning-desk && cd learning-desk
python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt   # once
.venv/bin/python -m streamlit run app.py
```

The app opens at http://localhost:8501 and listens only on this computer (`.streamlit/config.toml`).
Stop it with Ctrl+C in the terminal. The commands below use the Windows paths; on macOS/Linux
replace `.venv\Scripts\python` with `.venv/bin/python`.

## Configuration

Settings come from environment variables. If you prefer a file, copy `.env.example` to `.env`
and edit it there (`.env` is ignored by Git). Variables already set in your environment take priority.

| Variable | Default | Meaning |
|---|---|---|
| `ANTHROPIC_API_KEY` | none | Anthropic API key. Without it, the AI buttons are disabled; everything else works. |
| `LEARNING_DESK_MODEL` | `claude-opus-5-5` | Any model ID your key can use. Checked only when you make a call. |
| `LEARNING_DESK_EFFORT` | `medium` | Anthropic `effort` (low/medium/high/xhigh/max). Empty = not sent. |
| `LEARNING_DESK_MAX_TOKENS` | `8000` | Output limit per call. A cut-off reply is rejected, not used. |
| `LEARNING_DESK_TIMEOUT` | `180` | Seconds to wait for a reply. |
| `LEARNING_DESK_DB` | `data/learning_desk.db` | Where the database lives. |

An API key is billed per use and is separate from a Claude.ai or ChatGPT subscription.
Never paste a key into a chat. The app never displays, stores or logs it.

## Using it

1. **Home** → *Start session*. Or *Settings & About → Load fictional example session* to try it out.
2. **Notes tab**: fill in what you want to understand, your current explanation, and notes
   (Markdown and ``` code fences are supported). Click **Save**. The bar shows when you last saved and
   warns about unsaved changes.
3. **Questions & next steps tab**: unresolved questions and tasks for this session. Edits save automatically.
4. **Review this session**: one model call. Feedback appears in a bordered "AI feedback" box,
   separate from your notes. Older reviews stay available; you can compare two side by side.
   Suggested next steps go into your queue only when you click *Add* (you can edit them first).
5. **Test my understanding**: generates three questions (explanation, application, limitations)
   with no answers or hints. Write and *Submit* an answer, then *Get feedback on my answer*.
   There are no scores.
6. **Queue**: all open items across sessions, sorted by the priority you set. Mark them *Done*
   or *Reopen* them.
7. **Search & export**: plain text search, and *Download all data (JSON)*. Each session also has a
   Markdown export in its *Export* tab. Exports work without an API key or internet.

## What happens when you click "Review this session"

1. **Ordinary code:** unsaved edits are saved first. The saved session and its open questions
   and next steps are copied into a **snapshot**, which is stored and never changed afterwards.
2. **Ordinary code:** the snapshot is split into numbered sections `[S1]`, `[S2]` and so on. Notes are
   split at blank lines, but never inside a code block.
3. **Ordinary code:** a request is built. The fixed instructions go in the `system` field. Your
   sections go inside a `<session>` element in the user message, along with a JSON schema
   describing the reply's required shape.
4. **The LLM:** Anthropic's API runs the model once. No automatic retries and no fallback model
   are used, so one click means at most one billed request.
5. **Ordinary code:** the reply is parsed and checked against the same shape again with Pydantic. If it
   doesn't fit, the reply is rejected and shown as an error. Nothing is made up to replace it, and
   your notes are untouched.
6. **Ordinary code:** citations are matched to the snapshot's text, so you can open "Cited: S3" and
   read exactly what the model was pointing at. Citations to sections that don't exist are flagged.
7. Everything is recorded. **Inspect AI call** shows:
   - the action and instruction version
   - the full request, without credentials
   - the requested model and the model the API returned
   - the raw response
   - elapsed time
   - token usage as reported by the provider
   - any error

   It does not show the model's internal reasoning.

Only steps 4–5 depend on the LLM. The judgement in the feedback comes from the model and can be
wrong. Everything else is ordinary, deterministic software.

## Storage, backup, privacy

- All data lives in one SQLite file, `data\learning_desk.db` by default. Nothing is uploaded
  anywhere except when you click an AI button.
- **Back up**: stop the app and copy that file, or download the JSON export.
  **Restore**: put the file back.
- An AI call sends only the current session's saved content (plus your answer, for feedback).
  Other sessions are never sent, and there is no memory across sessions.
- Notes are marked as data, not instructions. This **reduces but does not prevent** prompt
  injection: pasted text can still influence what the model writes.
- Pasted code is never executed. Model and user text is rendered without HTML, and Markdown images
  are disabled so that rendering a page never contacts outside addresses.
- `.env`, `data/` and `exports/` are in `.gitignore`.

## Limitations (V1)

- Single user, single machine. No accounts, sync or deployment.
- Search is a plain substring match.
- Unsaved typing lives in the browser tab. Closing or refreshing the tab loses it, so save often.
- Source URLs are listed, never fetched. No file uploads or PDFs.
- The model's grounding claims are checked only for whether the cited section exists, not for
  whether the section really supports the claim. That check is yours to make.

## Troubleshooting

| Symptom | Fix |
|---|---|
| AI buttons are greyed out | `ANTHROPIC_API_KEY` is not set in the environment that started the app. Set it, then restart. |
| "Model ... was not found (404)" | Set `LEARNING_DESK_MODEL` to a model your key can use. |
| "The API key was rejected (401)" | The key is wrong or revoked. Create a new one in the Anthropic Console. |
| "did not match the expected format" | The reply was rejected. Open *Inspect AI call* to see the raw response, then try again. |
| "cut off at the token limit" | Raise `LEARNING_DESK_MAX_TOKENS` or split a very long session. |
| Port 8501 in use | `.venv\Scripts\python -m streamlit run app.py --server.port 8502` |

## Tests

```powershell
.venv\Scripts\python -m pytest -q
```

All tests use a temporary database and a **fake** provider. They check the app's behaviour around
the model, not the model itself, and they never contact Anthropic.

## Key files

| File | What it holds |
|---|---|
| `app.py` | Entry point: page setup and navigation. |
| `learning_desk/db.py` | SQLite schema and all reads and writes (`update_session`, `list_queue`, `get_or_create_snapshot`, `insert_ai_call`, ...). |
| `learning_desk/sections.py` | `build_snapshot_content`, `split_blocks`, `number_sections`: turns a session into numbered sections. |
| `learning_desk/prompts.py` | Instructions, version strings, JSON schemas and Pydantic validators for the three actions. |
| `learning_desk/ai.py` | `review_session`, `generate_questions`, `answer_feedback`; the shared `_run` does build → send → validate → record. |
| `learning_desk/provider.py` | The only Anthropic-specific code: `build_request` and `send`. Replace this file to change provider. |
| `learning_desk/export.py` | `session_markdown`, `all_data_json`. |
| `learning_desk/ui/session_page.py` | Session editor (draft handling), review display, questions, per-session queue. |
| `learning_desk/ui/other_pages.py` | Home, Queue, Search & export, Settings & About. |
| `learning_desk/ui/common.py` | `inspect_call`, `safe_md`, queue widgets, messages. |
| `tests/` | Storage, AI-handling, export and UI tests. |

## Three small changes to learn from

1. **Change an instruction and watch it travel.** In `prompts.py`, ask for "1-2 sentences" in the
   review summary instead of "2-4" and set `REVIEW_VERSION = "review-v2"`. Run a review, then
   compare the two in *Inspect AI call*. The version tells you which instructions produced which output.
2. **Add a field to the schema.** Add `"confidence_note": {"type": "string"}` to `QUESTIONS_SCHEMA`
   and a `confidence_note: str` field to `QuestionSet`. Run `pytest` and see which test fails, and why
   a schema and its validator must change together.
3. **Change how notes are numbered.** In `sections.split_blocks`, also start a new block at every
   Markdown heading (a line starting with `#`). Add a test to `tests/test_storage.py`, then look at
   how the `[S#]` sections change in *Inspect AI call*.

## License

MIT. See [LICENSE](LICENSE).
