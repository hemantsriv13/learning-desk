"""Lessons for topics 3, 4 and 6: tokens and context, context versus storage, sampling, attention."""

from .. import visuals
from .model import Activity, Check, Citation, Code, Lesson, Section, Table

TOKENS_CONTEXT = Lesson(
    id="tokens-context-window",
    topic="tokens",
    title="Tokens and the context window",
    summary="What a model actually reads, what counts toward its limit, and what happens when a request is too long.",
    level="introductory",
    minutes=25,
    objective="Explain how text becomes tokens, list everything that counts toward a context window, and "
              "predict what happens when a request does not fit.",
    intro="Language models do not read characters or words. They read **tokens**: pieces of text from a "
          "fixed vocabulary that the model's tokenizer produces. Limits, prices and speed are all measured "
          "in tokens, and every request has a **context window**: the maximum number of tokens the model "
          "can take into account at once, including what it writes back.",
    key_ideas=(
        "A token is a piece of text from the model's vocabulary, often part of a word, often with a leading space.",
        "Counts depend on the tokenizer, so the same text can count differently on different models.",
        "The context window covers instructions, messages, tool definitions and the reply being generated.",
        "More context is not automatically better: it costs time and money and can reduce recall.",
    ),
    overview_visual="tokens_context",
    sections=(
        Section(
            "what", "What a token is",
            "Tokenizers split text into units that balance two needs: a vocabulary small enough to learn "
            "and pieces meaningful enough to be useful. Sub-word methods such as byte pair encoding keep "
            "common words whole and split rare words into smaller, reusable pieces, so the model can handle "
            "words it never saw whole.\n\n"
            "Two consequences are easy to miss. Spaces usually belong to the following token, so `\" notes\"` "
            "and `\"notes\"` can be different tokens. And code, numbers, unusual names and many non-English "
            "languages tend to use more tokens per word than everyday English prose.",
            visual="tokens_context",
        ),
        Section(
            "counting", "Counting depends on the model",
            "Each model family has its own tokenizer, so token counts are not portable. Anthropic's "
            "documentation notes that its newer models use a tokenizer that produces roughly 30% more tokens "
            "for the same text than earlier models, and advises recounting prompts for the model you plan "
            "to use rather than reusing old counts.\n\n"
            "To measure rather than guess, use the provider's token-counting tool (Anthropic offers a free "
            "endpoint that returns an estimate), or read the `usage` field every response reports. Learning "
            "Desk saves that usage in each call record.",
            callout="Word counts are a poor proxy for tokens. When you need a length limit in a prompt, "
                    "sentences or paragraphs work better than an exact word count.",
        ),
        Section(
            "window", "What fills the window",
            "Everything in a request counts: the system instructions, every message (including earlier "
            "turns, tool results, images and documents), the tool definitions, and the output the model "
            "generates for this turn. In a chat, earlier turns are sent again with every new message, so "
            "history grows until it dominates.\n\n"
            "Window sizes vary by model. At the time of checking, Anthropic listed a 1M-token window for its "
            "current models and 200k for some older ones, with up to 128k output tokens per request on the "
            "1M-token models. The same documentation warns that accuracy and recall can degrade as context "
            "grows, so curating what goes in matters as much as the limit.",
            table=Table(("Part of the request", "Counts toward the window?"),
                        (("System instructions", "Yes"), ("Earlier conversation turns", "Yes, every time they are resent"),
                         ("Tool definitions", "Yes"), ("Images and documents", "Yes"),
                         ("The reply being generated", "Yes"), ("Your stored notes that you did not send", "No")),
                        caption="If it is not in the request, it is not in the context"),
        ),
        Section(
            "overflow", "When it does not fit",
            "What happens depends on the provider and model. On Anthropic's API, input that alone exceeds the "
            "window is rejected with a 400 error (\"prompt is too long\"). On newer models, a request whose "
            "input plus `max_tokens` exceeds the window is accepted, and generation stops with the stop "
            "reason `model_context_window_exceeded` if it reaches the limit. Separately, any reply stops "
            "with `max_tokens` when it reaches the requested output limit.\n\n"
            "Learning Desk guards earlier and more crudely: before any call, a source over 100,000 "
            "characters or 500 passages is refused with a message asking for a shorter passage. That is a "
            "character limit, not a token count, chosen to keep requests bounded and predictable.",
        ),
    ),
    worked_example=Section(
        "worked", "Worked example: budgeting a conversation",
        "Suppose a chat uses 1,200 tokens of system instructions, each exchange (question plus answer) "
        "averages 800 tokens, and you reserve 1,500 tokens for the next reply. Because earlier turns are "
        "resent, the request grows with every exchange:",
        table=Table(("After exchange", "History tokens", "Request + reply budget"),
                    tuple((str(n), f"{n * 800:,}", f"{1200 + n * 800 + 400 + 1500:,}") for n in (1, 5, 10, 20, 40)),
                    caption="Illustrative numbers: system 1,200 + history + new message 400 + reply budget 1,500"),
        callout="By exchange 40, history is over 90% of the request. Summarising or selecting earlier turns "
                "is the usual remedy.",
    ),
    misconception=Section(
        "misconception", "Misconception: a token is a word",
        "Some words are one token, others several, and punctuation and spaces are part of tokens too. "
        "Rules of thumb about characters or words per token are rough averages for one kind of text and "
        "one tokenizer. For anything that matters (cost estimates, fitting a document, setting limits) count "
        "with the tool for your model or read the reported usage.",
    ),
    activity=Activity(
        "Fit a request into a window",
        ("Use the context budget calculator below. Start with the default values.",
         "Increase history until the bar turns red. How many exchanges of 800 tokens is that?",
         "Halve the window size. Which single change gets the request to fit again with the least loss?",
         "Write down one way your own project could send less history without losing what matters."),
        widget="context_budget",
        reflection="Notice that the output budget competes for the same space as everything you send.",
    ),
    checks=(
        Check("counts", "Which of these counts toward a request's context window?",
              ("System instructions, messages, tool definitions and the generated reply",
               "Only the latest user message",
               "Only what the model generates",
               "Everything stored in the app's database"),
              "System instructions, messages, tool definitions and the generated reply",
              "Everything sent, plus the output for the turn, counts. Stored but unsent data does not.", "window"),
        Check("portable", "The same paragraph counts as 400 tokens on one model and 520 on another. Why?",
              ("The models use different tokenizers",
               "Token counting is random",
               "One model added a hidden summary",
               "Spaces are free on one model"),
              "The models use different tokenizers",
              "Tokenizers differ between model families, so counts are not portable.", "counting"),
        Check("toolong", "On Anthropic's API, what happens if the input alone exceeds the context window?",
              ("The request is rejected with a 400 error",
               "The oldest messages are silently dropped",
               "The model reads only the first half",
               "The reply is shortened automatically"),
              "The request is rejected with a 400 error",
              "The documentation describes a 400 invalid_request_error (\"prompt is too long\"). Other "
              "providers may behave differently.", "overflow"),
    ),
    citations=(
        Citation("sennrich-2015", "Sub-word units (byte pair encoding) for rare and unknown words."),
        Citation("claude-token-counting", "Token counts are estimates; newer tokenizer gives roughly 30% more "
                 "tokens; recount per model; the endpoint is free."),
        Citation("claude-context-windows", "What counts toward the window; window sizes; context rot; overflow "
                 "behaviour and model_context_window_exceeded."),
        Citation("claude-latency", "Prefer sentence or paragraph limits to word counts."),
        Citation("app-learning", "Sources over 100,000 characters or 500 passages are refused before any call."),
    ),
    related=("context-vs-storage", "sampling-temperature", "latency-cost-reliability"),
    scope="Tokenization and context windows are general concepts. Sizes, the 30% figure and overflow "
          "behaviour are Anthropic-specific and change between models; re-check before relying on them.",
)


CONTEXT_STORAGE = Lesson(
    id="context-vs-storage",
    topic="tokens",
    title="Context versus storage: what a model actually sees",
    summary="Why a stateless API forgets, how apps create memory, and how Learning Desk chooses context.",
    level="introductory",
    minutes=25,
    objective="Distinguish the context sent with one request from the data an application stores, and "
              "decide deliberately what each request should include.",
    intro="People often say a model \"remembers\" a conversation. With an API such as Anthropic's Messages "
          "API, it does not: each request is processed on its own, and the application sends the "
          "conversation again every time. **Storage** is what your application keeps between requests. "
          "**Context** is what one request contains. Keeping the two apart explains most \"why did it "
          "forget?\" surprises, and most privacy questions too.",
    key_ideas=(
        "The Messages API is stateless: the client sends the full history it wants the model to use.",
        "A chat app's \"memory\" is the application deciding what to resend.",
        "Storage persists between requests; context exists only inside one request.",
        "Choosing context is a design decision with effects on quality, cost and privacy.",
    ),
    overview_visual="context_storage",
    sections=(
        Section(
            "stateless", "Stateless requests",
            "Anthropic's documentation states it directly: the Messages API is stateless, so you always send "
            "the full conversational history. A multi-turn conversation is just a `messages` list that grows "
            "on the client and is sent in full each time. Earlier turns do not even need to have come from "
            "the model; an application can supply them.\n\n"
            "This is the same property as HTTP's statelessness, one level up: each request stands alone, "
            "and continuity is built by what the client chooses to send.",
            code=Code("python",
                      'turn_1 = [{"role": "user", "content": "My name is Sam."}]\n'
                      '# … reply: "Nice to meet you, Sam." …\n'
                      '\n'
                      'turn_2_alone = [{"role": "user", "content": "What is my name?"}]\n'
                      '\n'
                      'turn_2_with_history = [\n'
                      '    {"role": "user", "content": "My name is Sam."},\n'
                      '    {"role": "assistant", "content": "Nice to meet you, Sam."},\n'
                      '    {"role": "user", "content": "What is my name?"},\n'
                      ']',
                      notes=((4, "Sent on its own, this request contains no name at all."),
                             (6, "The application resends the earlier turns; now the name is in context.")),
                      caption="Two possible second requests"),
        ),
        Section(
            "storage", "Storage is the application's job",
            "Anything that should persist (notes, past reviews, settings, logs) has to be stored by the "
            "application, for example in a database. Learning Desk uses one SQLite file on your computer for "
            "sessions, resources, summaries, quiz attempts and every AI call record.\n\n"
            "Storing something does not send it anywhere. A record only reaches a model if code reads it and "
            "places it in a request. That is the boundary to look for when you ask \"what does the model "
            "know?\" or \"what left my computer?\"",
        ),
        Section(
            "this-app", "How Learning Desk builds context",
            "For a notebook review, `ai.prepare_snapshot` reads the **saved** session (title, topic, goal, "
            "explanation, notes, sources) and its open queue items, splits the text into numbered sections "
            "[S1], [S2], … and stores that snapshot. Identical content reuses the same snapshot row. The "
            "request contains the fixed instructions plus that numbered snapshot, nothing else: no other "
            "sessions, no earlier reviews, no call logs.\n\n"
            "Reader actions follow the same rule with a different source: a summary or quiz sends only the "
            "selected content version of one resource. Because snapshots and versions are kept, every saved "
            "review, summary and question can be traced back to exactly what the model was shown.",
            visual="context_storage",
        ),
        Section(
            "choosing", "Choosing what to include",
            "Every request is a selection problem. Include too little and the model lacks what it needs; "
            "include too much and you pay in tokens and time, may reduce recall, and send data that did not "
            "need to leave. Common strategies:\n\n"
            "- **Scope**: send one session or one document, not everything (Learning Desk's choice).\n"
            "- **Select**: retrieve the most relevant passages (see the retrieval lesson).\n"
            "- **Summarise**: replace old turns with a summary; providers increasingly offer server-side "
            "compaction for long conversations.\n"
            "- **Cache**: prompt caching makes a repeated prefix cheaper and faster to process, but the "
            "cached tokens are still part of the request and still occupy the window.",
        ),
    ),
    worked_example=Section(
        "worked", "Worked example: why the review did not mention last week",
        "You review today's session and the feedback ignores a misconception you corrected in last week's "
        "session. Walk the boundary:\n\n"
        "1. **Is last week in storage?** Yes, as a separate session row.\n"
        "2. **Is it in context?** No. The snapshot contains only the current session's saved fields and open "
        "queue items.\n"
        "3. **Could the model know anyway?** Not from your data; it only sees the request.\n"
        "4. **Fix, if you want it considered**: add a short note or source line to *this* session, save, "
        "and review again. You then control exactly what is shared.",
        table=Table(("Material", "In storage", "In this review's context"),
                    (("Today's saved notes", "Yes", "Yes (numbered)"),
                     ("Today's unsaved typing", "Only in the browser", "Saved first, then included"),
                     ("Last week's session", "Yes", "No"),
                     ("Earlier AI reviews", "Yes", "No"),
                     ("Call logs", "Yes", "No")),
                    caption="Storage versus context for one notebook review"),
    ),
    misconception=Section(
        "misconception", "Misconception: the provider remembers my earlier requests",
        "Whatever a provider retains under its data policies, the model's reply to a request is produced "
        "from that request's context (and what the model learned in training), not from your earlier API "
        "calls. If an application seems to remember, it is resending or retrieving earlier material. "
        "Prompt caching does not change this: it reuses processing of a prefix you send again, and the "
        "cached tokens still count as part of the request's context.",
    ),
    activity=Activity(
        "Find the boundary in a real request",
        ("Open a notebook session that has an AI review (or create one and review it if you have a key).",
         "Open *Technical details* or *Inspect AI call* and read *Request sent*.",
         "Find the `<session>` block. List what is inside, and check that no other session appears.",
         "Compare it with the session editor: which fields are numbered, and in what order?"),
        reflection="For a project of your own, write one sentence defining what each request is allowed to include.",
    ),
    checks=(
        Check("memory", "In a chat app built on a stateless API, how is turn 3 available during turn 10?",
              ("The application resends it as part of the messages",
               "The model stores it between requests",
               "The provider keeps a per-user memory automatically",
               "It is not available"),
              "The application resends it as part of the messages",
              "Continuity comes from what the client sends with each request.", "stateless"),
        Check("review", "What does a Learning Desk notebook review request contain?",
              ("Fixed instructions and a numbered snapshot of the current saved session and its open queue items",
               "All sessions and earlier reviews",
               "The current session's unsaved typing only",
               "The full SQLite database"),
              "Fixed instructions and a numbered snapshot of the current saved session and its open queue items",
              "prepare_snapshot reads only the saved current session and its queue.", "this-app"),
        Check("cache", "Does prompt caching let you stop sending conversation history?",
              ("No. You still send it; caching changes the cost and speed of processing it",
               "Yes. The provider remembers it",
               "Yes, after the first request",
               "Only for system instructions"),
              "No. You still send it; caching changes the cost and speed of processing it",
              "Cached prefixes are still part of the request and still occupy the context window.", "choosing"),
    ),
    citations=(
        Citation("claude-messages", "The Messages API is stateless; send the full conversational history."),
        Citation("claude-context-windows", "Context rot; server-side compaction; cached prefixes still occupy the window."),
        Citation("claude-prompt-caching", "Caching resumes from a cached prefix to reduce processing time and cost."),
        Citation("py-sqlite3", "SQLite as local persistent storage from Python."),
        Citation("app-ai", "prepare_snapshot reads the saved session and queue items and numbers its sections."),
    ),
    prerequisites=("tokens-context-window",),
    related=("retrieval-basics", "http-request-flow"),
    scope="Statelessness is described for Anthropic's Messages API. Other products may add server-side "
          "memory features, which still work by putting material into context.",
)


def _sampling_rows():
    logits = [s for _, s in visuals.NEXT_TOKEN_LOGITS]
    settings = (("T = 0.5", 0.5, 0, 1.0), ("T = 1.0", 1.0, 0, 1.0), ("T = 1.5", 1.5, 0, 1.0),
                ("T = 1, top-k 3", 1.0, 3, 1.0), ("T = 1, top-p 0.9", 1.0, 0, 0.9))
    columns = [visuals.sampling_distribution(logits, t, k, p) for _, t, k, p in settings]
    rows = tuple((token, *[visuals.pct(col[i]) if col[i] else "removed" for col in columns])
                 for i, (token, _) in enumerate(visuals.NEXT_TOKEN_LOGITS))
    return ("Candidate", *[name for name, *_ in settings]), rows


_SAMPLING_COLUMNS, _SAMPLING_ROWS = _sampling_rows()

SAMPLING = Lesson(
    id="sampling-temperature",
    topic="sampling",
    title="Next-token probabilities and sampling",
    summary="How a model turns scores into probabilities, and how temperature, top-k and top-p change the choice.",
    level="intermediate",
    minutes=30,
    objective="Explain how a language model turns scores into a probability distribution over next tokens, "
              "and predict how temperature, top-k and top-p change which token is chosen.",
    intro="A language model generates text one token at a time. At each step it produces a score for every "
          "token in its vocabulary, those scores become probabilities, and a **decoding** rule picks one "
          "token. The chosen token is appended and the process repeats. Sampling settings change only that "
          "last step, but because every choice becomes context for the next, small changes can lead to "
          "very different text.",
    key_ideas=(
        "At each step the model scores every token; softmax turns the scores into probabilities that sum to 1.",
        "Generation is a loop: choose a token, append it, score again.",
        "Temperature reshapes the whole distribution; top-k and top-p remove the unlikely tail.",
        "Which controls you can set is provider- and model-specific. Check before relying on them.",
    ),
    overview_visual="sampling",
    sections=(
        Section(
            "softmax", "From scores to probabilities",
            "The model's raw scores (often called logits) can be any real numbers. **Softmax** converts them "
            "into probabilities: raise *e* to each score, then divide by the total so everything sums to 1. "
            "Higher scores get exponentially more probability. With temperature *T*, each score is divided "
            "by *T* first:\n\n"
            "p(token i) = exp(s_i / T) / Σ exp(s_j / T)\n\n"
            "The interactive chart uses eight invented candidate words for the prompt *\"The experiment "
            "finished, so we wrote the …\"*. A real model would score its entire vocabulary, often tens of "
            "thousands of tokens.",
            visual="sampling",
        ),
        Section(
            "loop", "One token at a time",
            "Generation repeats a simple loop: score, choose, append. The choice at step 1 becomes part of "
            "the context for step 2, so a less likely early token can lead to a different sentence, "
            "paragraph or argument. This is why two runs with the same prompt can diverge widely even when "
            "each individual choice looked similar.\n\n"
            "The loop stops when the model produces an end-of-turn token, a stop sequence appears, or the "
            "output reaches `max_tokens`: the `stop_reason` in a response tells you which.",
        ),
        Section(
            "temperature", "Temperature",
            "Dividing scores by *T* below 1 stretches the differences between them: the top candidate gains "
            "probability and the tail shrinks. *T* above 1 compresses the differences: the distribution "
            "flattens and unlikely tokens are chosen more often. As *T* approaches 0, sampling approaches "
            "**greedy decoding**, always taking the single most likely token.\n\n"
            "Temperature never changes the *ranking* of candidates, only how much the ranking matters.",
        ),
        Section(
            "truncation", "Top-k and top-p",
            "**Top-k** keeps only the *k* most likely tokens and renormalises. **Top-p** (nucleus sampling) "
            "keeps the smallest set of most likely tokens whose probabilities add up to at least *p*, so the "
            "number kept adapts to how confident the model is. Holtzman and colleagues proposed nucleus "
            "sampling because sampling from the full distribution lets the unreliable low-probability tail "
            "produce incoherent text, while always taking the most likely tokens tends to produce bland, "
            "repetitive text.\n\n"
            "Samplers commonly apply temperature first and then truncation; the chart here does the same.",
        ),
        Section(
            "control", "What you can actually control",
            "Exposed settings differ by provider and model, and change over time. At the time of checking, "
            "Anthropic's documentation said `temperature`, `top_p` and `top_k` are **not supported** on its "
            "Claude 4.7 and later models (or on any model from API version 2026-10-21): setting them returns "
            "a 400 error, and the guidance is to steer behaviour with prompting instead. Learning Desk sends "
            "none of these parameters.\n\n"
            "Whatever your provider allows, the robust practices are the same: constrain the *format* with "
            "structured outputs, cache results you want to stay stable, and evaluate across several runs "
            "rather than trusting one.",
            callout="This lesson teaches the general mechanism. Do not assume any particular provider lets "
                    "you set these values.",
        ),
    ),
    worked_example=Section(
        "worked", "Worked example: one distribution, five settings",
        "The table applies five settings to the same invented scores. Read across a row to see one "
        "candidate's fate. Notice that lower temperature concentrates probability on *report*, higher "
        "temperature lifts *poem* and *banana*, and both truncation methods remove the tail entirely while "
        "boosting what remains.",
        table=Table(_SAMPLING_COLUMNS, _SAMPLING_ROWS,
                    caption="Computed by Learning Desk from illustrative scores; not output from a real model"),
    ),
    misconception=Section(
        "misconception", "Misconception: low temperature makes answers correct",
        "Greedy or low-temperature decoding picks the *most likely* continuation, and likely is not the "
        "same as true. A model that assigns high probability to a wrong statement will state it more "
        "consistently, not less. Lower randomness also does not, by itself, promise identical output on "
        "every run; do not assume that unless your provider documents it. Correctness has to be checked "
        "by evaluation, not dialled in.",
    ),
    activity=Activity(
        "Predict, then move the sliders",
        ("Before touching anything, predict: at temperature 0.2, roughly what share will *report* get?",
         "Set temperature to 0.2 and check. Then try 2.0. What happens to *banana*?",
         "Return to 1.0. Set top-k to 2. Which candidates survive, and why do their shares go up?",
         "Set top-k back to 0 (off) and top-p to 0.5. How many candidates are kept?",
         "Draw three samples at two different temperatures and compare how often each word appears."),
        widget="sampling",
        reflection="Which settings change the ranking of candidates? (None of them should.)",
    ),
    checks=(
        Check("flatten", "Raising temperature from 1.0 to 2.0 does what to the distribution?",
              ("Flattens it, so less likely tokens are chosen more often",
               "Sharpens it toward the top token",
               "Removes all but the top two tokens",
               "Reverses the ranking"),
              "Flattens it, so less likely tokens are chosen more often",
              "Dividing scores by a larger T shrinks their differences.", "temperature"),
        Check("topp", "With top-p = 0.9, which tokens are kept?",
              ("The smallest set of most likely tokens whose probabilities reach 90%",
               "Exactly nine tokens",
               "Tokens with at least 90% probability each",
               "The 90% least likely tokens"),
              "The smallest set of most likely tokens whose probabilities reach 90%",
              "Nucleus sampling keeps a variable-size set covering probability mass p.", "truncation"),
        Check("ranking", "Does lowering temperature change which token is most likely?",
              ("No. It changes how strongly the ranking is followed",
               "Yes, it promotes rarer tokens",
               "Yes, it reverses the order",
               "Only when top-k is set"),
              "No. It changes how strongly the ranking is followed",
              "Temperature rescales all scores by the same factor, so order is preserved.", "temperature"),
    ),
    citations=(
        Citation("holtzman-2019", "Nucleus (top-p) sampling; degeneration from full sampling and from likelihood-maximising decoding."),
        Citation("claude-messages", "temperature, top_p and top_k not supported on Claude 4.7+ models or API version 2026-10-21."),
        Citation("app-provider", "Learning Desk's requests contain no sampling parameters."),
    ),
    further_reading=(Citation("vaswani-2017", "The architecture that produces the scores (see the attention lesson)."),),
    prerequisites=("tokens-context-window",),
    related=("evaluation-basics", "structured-outputs"),
    scope="Softmax, temperature, top-k and top-p are general decoding concepts. Parameter availability is "
          "provider- and model-specific; the cited Anthropic restriction was current when checked.",
)


ATTENTION = Lesson(
    id="attention-basics",
    topic="attention",
    title="Attention: how tokens use other tokens",
    summary="What an attention weight means, how to read an attention pattern, and where attention fits in a transformer.",
    level="intermediate",
    minutes=35,
    objective="Describe what an attention weight represents, compute one attention step on tiny numbers, "
              "and read an attention pattern without over-interpreting it.",
    intro="Inside a transformer, each token is represented by a vector. On its own, the vector for *it* in "
          "\"the animal didn't cross the street because it was tired\" cannot say what *it* refers to. "
          "**Attention** is the operation that lets each token gather information from other tokens' "
          "vectors, weighting some much more than others. Stacked many times, it is the core of the "
          "transformer architecture.",
    key_ideas=(
        "Attention lets each token build a new vector as a weighted mix of other tokens' information.",
        "For one token, the weights are non-negative and sum to 1: a probability distribution.",
        "Queries and keys decide the weights; values are what gets mixed.",
        "In text generators, a causal mask stops tokens from looking at later tokens.",
        "Models use many heads and layers; one heatmap is a narrow view.",
    ),
    overview_visual="attention_heatmap",
    sections=(
        Section(
            "why", "Why attention",
            "Earlier neural translation systems squeezed a whole source sentence into one fixed-length vector "
            "before producing the translation. Bahdanau, Cho and Bengio (2014) let the model instead "
            "*softly search* the source for the positions relevant to each word it produced, a learned "
            "alignment. Vaswani and colleagues (2017) went further: the Transformer drops recurrence and "
            "convolutions and is built from attention (plus simple feed-forward layers), which also made "
            "training more parallel.",
        ),
        Section(
            "qkv", "Queries, keys and values",
            "Each token's vector is projected three ways. A **query** describes what this token is looking "
            "for; a **key** describes what each token offers; a **value** is the information each token "
            "contributes if chosen. The weight between two tokens comes from how well the query matches the "
            "key (a dot product), scaled by the square root of the key dimension and passed through softmax. "
            "The output is the weighted sum of values:\n\n"
            "Attention(Q, K, V) = softmax(Q·Kᵀ / √d_k) · V\n\n"
            "Softmax is the same function as in the sampling lesson, used here to turn match scores into "
            "weights rather than to choose a word.",
        ),
        Section(
            "reading", "Reading an attention heatmap",
            "In a heatmap, each **row** is a token being updated and each **column** a token it can draw "
            "from; each row sums to 1. Generative language models use a **causal mask**: a token may attend "
            "to itself and earlier tokens only, because later tokens do not exist yet when it is generated. "
            "That leaves the upper-right triangle empty.\n\n"
            "In the illustrative head here, the row for *it* puts most of its weight on *animal*: the kind "
            "of pattern that would help resolve the pronoun. Real heads learn their patterns during "
            "training; some are interpretable like this, many are not.",
            visual="attention_heatmap",
        ),
        Section(
            "heads", "Heads, layers and position",
            "A transformer runs several attention **heads** in parallel, each with its own projections, so "
            "different heads can track different relationships. Their outputs are combined and passed "
            "through a feed-forward layer, and this block is repeated across many **layers**, each refining "
            "every token's vector.\n\n"
            "Attention by itself has no notion of order: it compares vectors regardless of where they sit. "
            "The original Transformer therefore added positional encodings to the token vectors. How "
            "position is represented is an active design choice in later models.",
        ),
    ),
    worked_example=Section(
        "worked", "Worked example: one attention step with tiny numbers",
        "Take three tokens with two-dimensional keys and values, and the query of the third token "
        "q = (1.0, 0.5). The keys are k₁ = (1, 0), k₂ = (0, 1), k₃ = (1, 1); the values are "
        "v₁ = (1, 0), v₂ = (0, 1), v₃ = (0.5, 0.5).\n\n"
        "1. **Scores** = q·k / √2: 0.707, 0.354, 1.061.\n"
        "2. **Softmax** turns them into weights: 0.320, 0.225, 0.456 (they sum to 1).\n"
        "3. **Mix the values**: 0.320·v₁ + 0.225·v₂ + 0.456·v₃ = (0.548, 0.452).\n\n"
        "The third token's new vector leans toward the tokens whose keys best matched its query. "
        "That is all one head does; the model learns the projections that make useful matches.",
        table=Table(("Token", "Key", "Score q·k/√2", "Weight", "Value"),
                    (("1", "(1, 0)", "0.707", "0.320", "(1, 0)"),
                     ("2", "(0, 1)", "0.354", "0.225", "(0, 1)"),
                     ("3", "(1, 1)", "1.061", "0.456", "(0.5, 0.5)")),
                    caption="Computed values, rounded to three decimals"),
    ),
    misconception=Section(
        "misconception", "Misconception: attention weights explain the answer",
        "A heatmap shows how one head in one layer mixed information for one input. The model has many "
        "heads and layers, feed-forward computation between them, and the final output depends on all of "
        "it. Attention patterns can suggest hypotheses about what a model uses, but treating a single map "
        "as *the reason* for an output over-reads it. The heatmap in this lesson is invented to illustrate "
        "the mechanism, not taken from a real model.",
    ),
    activity=Activity(
        "Read rows, not pixels",
        ("Use the explorer below. Choose the row for *it* and read its three largest weights.",
         "Choose *was* and *tired*. Which earlier tokens do they draw on in this invented head?",
         "Choose *The* (the first token). Why can it only attend to itself?",
         "Check the worked example by hand: do the three weights sum to 1?"),
        widget="attention_heatmap",
        reflection="What would you need, beyond one heatmap, before claiming a model 'knows' what *it* refers to?",
    ),
    checks=(
        Check("sum", "In an attention heatmap, what do the weights in one row add up to?",
              ("1", "The number of tokens", "0", "It varies freely"), "1",
              "Softmax makes each row a probability distribution over the tokens that row may attend to.", "reading"),
        Check("mask", "Why are the upper-right cells blank in a generative model's heatmap?",
              ("A causal mask stops tokens attending to later tokens",
               "Those weights are always exactly 1",
               "The heatmap is cropped for space",
               "Later tokens have no keys"),
              "A causal mask stops tokens attending to later tokens",
              "When generating left to right, later tokens do not exist yet, so attention to them is masked.",
              "reading"),
        Check("qk", "In scaled dot-product attention, what determines the weights?",
              ("How well each query matches each key", "The values alone", "Token position only",
               "The sampling temperature"),
              "How well each query matches each key",
              "Weights are softmax(Q·Kᵀ/√d_k); values are then mixed using those weights.", "qkv"),
    ),
    citations=(
        Citation("vaswani-2017", "The Transformer, built on attention without recurrence; scaled dot-product and "
                 "multi-head attention; positional encodings."),
        Citation("bahdanau-2014", "Soft alignment instead of a single fixed-length vector."),
    ),
    prerequisites=("tokens-context-window", "embeddings-similarity"),
    related=("sampling-temperature",),
    scope="Attention as defined in the original Transformer paper. Production models vary in details such as "
          "positional schemes and attention variants. The heatmap uses invented weights.",
)

LESSONS = (TOKENS_CONTEXT, CONTEXT_STORAGE, SAMPLING, ATTENTION)
