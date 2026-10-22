# Learning Desk

A local, connected learning environment: **Explore → Read → Practise → Resume**.
Built with Streamlit, Python, and SQLite. Home puts one *Continue learning* action first, followed by
your current topics and suggested lessons. There are no streaks, automatic tasks, or mastery scores.

## Launch

Requires Python 3.11 or newer. In PowerShell, from this repository:

```powershell
.venv\Scripts\python -m streamlit run app.py
```

For a new installation:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m streamlit run app.py
```

On macOS/Linux use `.venv/bin/python`. The app listens locally at http://localhost:8501.
The existing model/provider configuration is unchanged. Set configuration through your environment
or local `.env` as before. Never commit credentials. Reading, notes, history, deterministic
multiple-choice grading, and exports work without an API key; generation needs your configured key.

## First use

Open **Library → Add a resource**, paste a short passage, and save it. Choose **Quick read**
when you want a summary, or **Check my understanding** for a three-question quiz.
The optional starter path links to official Python, JSON Schema, and MDN documentation.
Starter suggestions are separate from your history; saving a starter bookmark does not import its content.

## Explore and lessons

**Explore** maps ten topics, from Python data shapes to AI product trade-offs. It ships **14 finished
lessons**; the other 15 entries are clearly labelled *outlines* (planned objectives only) and cannot be opened
as lessons. Each finished lesson has a learning objective, prerequisites, introduction, key ideas, a
walkthrough of explanation sections, a worked example, a misconception or limitation, a hands-on activity,
deterministic quick-check questions, sources, and deeper reading.

Every lesson offers four views of the same content, and you can move freely between them:
**Overview** (objective, key ideas, main visual), **Walkthrough** (one section at a time or all on one page,
with previous/next and a contents list), **Try it** (activity, interactive example, quick check), and
**Sources** (citations, check dates, provenance, visual attribution). Your view, section, completion and
lesson notes are saved in the database and restored after a reload or restart.

- Lessons are original educational content written for Learning Desk and stored as typed data in
  `learning_desk/curriculum/`. The collection is validated at import, so a broken link between lessons,
  sources or visuals fails start-up and tests. Lessons never call a model.
- Sources favour official documentation, standards and original papers. Each link was opened and the
  specific claim it supports was compared with the page on 2026-10-23; that date is shown per source.
  Provider-specific details (Anthropic) are marked as such and change over time. Claims about this app were
  checked against its code, and a test re-checks the key ones.
- Quick checks are fixed multiple-choice questions marked by comparison. Every submission is saved with the
  lesson version it was answered against.
- **Optional personalised AI**: *Save this lesson to the Library* stores the exact lesson version as a
  resource (no model call). From there, the existing explicit *Quick read*, *Explain it* and quiz buttons
  can generate AI output, labelled as such and tied to that version.

### Visuals

Diagrams are deterministic SVG drawn by `learning_desk/visuals.py`; interactive examples (sampling with
temperature/top-k/top-p, a context budget, embedding similarity, attention rows, latency and cost, a
parse-only JSON inspector) compute locally and never call a model or run typed input. Every visual has a
"what to notice" note, a full text description (also used as the image's `alt` text), and an explicit label
when its data are illustrative (for example, the 2-D embedding map states that real embeddings have hundreds
to thousands of dimensions). All artwork is original and covered by the MIT licence; no photographs, stock
images, hotlinked assets or AI-generated images are used.

## Library and reader

- Save references, documentation, articles, or pasted text/Markdown. Search titles, URLs, types,
  tags/topics, levels, and status. Edit details, mark Saved/Reading/Finished, or archive without deleting.
- A bookmark is labelled **content not imported** until text is saved. Link resources to notebook sessions
  in the reader's details panel. Open linked sessions from there.
- Public HTTP/HTTPS HTML or plain-text pages can be imported explicitly. Each distinct imported/pasted
  text becomes an immutable version, with its source URL, extraction note, hash, and extracted links.
  Editing a bookmark does not rewrite older versions' source URLs.
- Select an earlier version to read or practise from it. The selected version and reading view persist.
- **Original text** shows the saved source. **Quick read** requests about 150 words.
  **Explain it** requests a fuller explanation and one example. Source-supported paragraphs cite numbered
  passages; added explanations and teaching examples are labelled separately.
- Summaries are generated only on request and cached per version and format. Opening pages, switching
  views, expanding evidence, or rerunning Streamlit does not call a model.
- Further reading contains only saved resource links or links extracted from that source version.
  These linked pages are explicitly labelled as not read for the summary.

Imports check every destination, including redirects, reject private/local/reserved/multicast addresses,
and pin connections to a checked IP while retaining TLS hostname verification. They use bounded DNS
resolution, connection/read timeouts, a total read deadline, a 2 MB response limit, content-type checks,
and a 100,000-character text limit. Scripts, forms, navigation, and unsafe HTML are never executed.
The importer sends no credentials or cookies and makes no attempt to bypass access restrictions.
Compressed responses, PDFs, browser automation, and authenticated pages are outside this version.
Extraction is conservative and may include page furniture or omit content: compare with the original,
and paste the intended text when extraction fails or is incomplete. No automatic retry occurs.

## Practise and resume

Quizzes extend the existing `question_sets` and `questions` tables. Difficulty
(introductory/intermediate/advanced) is independent of practice goal (Understand/Apply/Diagnose)
and question type (multiple choice/short answer).

Three questions are generated in one requested call. Each retains its resource version or original
notebook snapshot, references, key/rubric, optional hint, and generation call/model metadata. One
question is displayed at a time. Keys/rubrics stay hidden until after submission, behind evidence controls.
Every submission creates a separate attempt, even if the wording repeats. Feedback belongs to that
attempt. Multiple-choice comparison is deterministic, but the AI-generated key can be wrong.
Short-answer feedback uses the source, rubric, and exact submitted answer in one requested model call.
Saved feedback is reused. Correctness on one question is not evidence of mastery.

Use **This question or feedback seems wrong** to save a report with question, attempt, and feedback IDs.
Reports are available in Settings & About and in exports; saving a report does not contact a model.
Earlier questions, attempts, and feedback remain available without regeneration.

Home persists the explicitly chosen lesson, resource, unfinished quiz, or notebook session. Continue learning
resumes it after restarting the app and says where you will land (for example, the lesson section). Change activity in the collapsed chooser. Finished/archived resources
and completed quizzes are not presented as unfinished work. Submitted answers, quiz position, and reader
view/version persist; unsaved typing still lives only in the browser tab.

## Notebook compatibility

Notebook retains sessions, notes, queue items, concise reviews, evidence citations, technical call
inspection, comparison of older reviews, and Markdown export. Notes save before requested review
or notebook-based quiz generation. AI output never overwrites your notes or adds tasks automatically.

Reviews keep the concise main takeaway, optional clarification, and one next step, with selective
emphasis and collapsed supporting evidence. Older review formats remain readable.
Notebook groups sessions (filterable cards), lesson notes, and the latest AI reviews in tabs.
The earlier notebook question format remains available in a collapsed compatibility section and now
also shows one question at a time. Feedback defaults to the question's original snapshot, never current notes.

Queue, Search & export, and Settings remain in the Tools navigation group. The session editor is reached
through Notebook or a linked session and is hidden from the main navigation.

## Data and migrations

The default database is `data/learning_desk.db` (`LEARNING_DESK_DB` overrides it).
Before the first learning-environment migration, SQLite's backup API saves a sibling
`*.pre-learning-v1.bak` file, including committed WAL data. The migration is rehearsed on a temporary
copy beside the database, checked for integrity and foreign keys, then applied transactionally.
It preserves existing rows and IDs and records its version in `PRAGMA user_version`.
Schema version 2 adds lesson progress, lesson notes, quick-check attempts and a nullable `activity.target_key`
column; it is purely additive. One backup is taken before each upgrade, named after the first pending
version (`*.pre-learning-v2.bak` for an existing v1 database), and all pending steps are rehearsed together
on a copy first. Backups are retained; failed migrations leave the original unchanged. Keep the app stopped when manually
restoring a backup. Do not remove backups until you have checked your data.

New relationships connect resources → content versions → summaries/quizzes → answer attempts → feedback.
Resources can link to notebook sessions without needing dummy sessions for resource AI calls.
Reader progress, quiz progress, and current activity are stored independently of browser session state.

Historical feedback is associated with an answer only when the recorded request contains an unambiguous
answer block. Such attempts are labelled as recovered. The latest legacy saved answer is retained separately
when needed; earlier submissions that were overwritten cannot be reconstructed. Unrecoverable evaluated
answers are explicitly labelled in exports and the compatibility reader. No association is guessed from
the current answer. Historical AI call contents and old notes/snapshots are preserved.

**Search & export → Download all data (JSON)** includes all old and new tables, source text, immutable
versions, snapshots, summaries, questions, attempts, feedback, reports, links, progress, and call logs.
Notebook Markdown includes the exact evaluated answers and corresponding source snapshot passages.
Resource Markdown includes every content version, source passages, summaries, quizzes, attempts, and reports.
Exports contain answer keys/rubrics and complete call logs; they are intended for personal archival use.

## AI calls and privacy

AI actions use the existing Anthropic provider with no automatic retry or fallback model. Generation
and feedback are labelled as AI output. Each requested generation uses one call; cached output is reused.
Resource actions send only the selected version; notebook actions use the saved snapshot. Ordinary browsing
makes no AI call. Requests/responses, prompt versions, source version/snapshot/attempt IDs, model IDs, usage,
errors, and timing remain inspectable. Invalid structures or unresolved new source references are rejected
and logged. The reference check establishes that a passage exists, not that it supports the model's claim.
Imported/pasted material is untrusted prompt data; this reduces but cannot eliminate prompt injection.
Code is stored as text and never executed. Markdown renders with HTML disabled and remote images suppressed.

Configuration remains: `ANTHROPIC_API_KEY`, `LEARNING_DESK_MODEL`, `LEARNING_DESK_EFFORT`,
`LEARNING_DESK_MAX_TOKENS`, `LEARNING_DESK_TIMEOUT`, and `LEARNING_DESK_DB`.
Defaults remain in `learning_desk/config.py`; this upgrade does not change them.

## Verification

```powershell
.venv\Scripts\python run_tests.py -q
```

`run_tests.py`, `pytest.ini`, and the test fixtures keep temporary directories and caches under
`.test-work/` in this repository. Tests disable loading `.env`, use dummy configuration and mocked
provider responses, and make no paid API calls. The suite covers migration preservation/recovery,
URL safety/failure cases, summary/version grounding and caching, attempt-feedback pairing, exports,
progress persistence, old rendering, save-before-review, safe text, and headless Streamlit interactions.

In the restricted development sandbox the existing virtual environment's base interpreter was inaccessible.
A local embedded interpreter under ignored `.tools/python/` was used for verification with the existing
installed dependencies. No global permissions or settings were changed. The normal launch command remains
unchanged. UI behaviour is checked with `streamlit.testing.v1.AppTest`; `tests/test_curriculum.py` covers content
integrity, visual calculations and alt-text consistency, migration to v2, lesson persistence, quick checks,
and that browsing every lesson view makes no model call. The redesign was also inspected in Chrome at desktop
width and in a 390-pixel-wide frame, running against a copy of an existing database with no API key set. Live model quality and real-provider compatibility were not tested with a
paid call. All new prompts and schemas are bounded and validated locally.

## Main files

| File | Responsibility |
|---|---|
| `app.py` | Home / Explore / Library / Notebook and tools navigation; design system |
| `learning_desk/curriculum/` | Topics, lessons, outlines, sources and the content validator |
| `learning_desk/visuals.py` | Deterministic SVG diagrams and the calculations behind interactive examples |
| `learning_desk/ui/learn.py`, `widgets.py`, `theme.py` | Explore, lesson views, interactive examples, shared styles |
| `learning_desk/db.py` | SQLite storage and relationships |
| `learning_desk/migrations.py` | Versioned backup, rehearsal, migration, legacy answer recovery |
| `learning_desk/importer.py` | Public-page fetching and safe extraction |
| `learning_desk/learning.py` | Source-grounded summaries, progressive quizzes and grading |
| `learning_desk/ai.py`, `prompts.py`, `provider.py` | Shared AI logging/validation and existing notebook actions |
| `learning_desk/ui/library.py`, `practice.py`, `today.py` | Library cards and reader, one-question practice, Home and Notebook |
| `learning_desk/ui/session_page.py` | Existing notebook editor and concise reviews |
| `learning_desk/export.py` | Complete JSON and source-resolving Markdown exports |
| `learning_desk/starter.py` | Optional starter path, with verified official documentation links |

Single-user, local storage only. No accounts, sync, deployment, PDFs, browser automation, automatic
background generation, or automatic correctness verification. See [LICENSE](LICENSE) (MIT).
