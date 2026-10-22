"""Lessons for topic 5: embeddings, similarity and retrieval."""

from .model import Activity, Check, Citation, Code, Lesson, Section, Table

EMBEDDINGS = Lesson(
    id="embeddings-similarity",
    topic="embeddings",
    title="Embeddings and similarity",
    summary="What an embedding vector represents, how cosine similarity compares two of them, and what a score can't tell you.",
    level="intermediate",
    minutes=30,
    objective="Explain what an embedding represents, compute cosine similarity for small vectors, and "
              "recognise what a similarity score can and cannot tell you.",
    intro="An **embedding** is a list of numbers that an embedding model produces for a piece of text. The "
          "model is trained so that texts with related meaning get vectors pointing in similar directions. "
          "That turns a fuzzy question (\"which of my notes is about this?\") into arithmetic you can do "
          "quickly over thousands of passages, which is the basis of semantic search and retrieval.",
    key_ideas=(
        "An embedding model maps text to a fixed-length vector of numbers.",
        "Related meanings tend to produce vectors that point in similar directions.",
        "Cosine similarity compares direction; for unit-length vectors it equals the dot product.",
        "Similar is not the same as relevant, and neither is the same as true.",
    ),
    overview_visual="embedding_map",
    sections=(
        Section(
            "vectors", "Text as vectors",
            "Mikolov and colleagues (2013) showed that continuous vector representations of words, learned "
            "from large text collections, capture syntactic and semantic relationships well enough to score "
            "on word-similarity tests. Modern embedding models apply the same idea to whole sentences and "
            "passages, producing one vector per input.\n\n"
            "The vectors are long. Anthropic, for example, does not offer its own embedding model and points "
            "to Voyage AI, whose current general-purpose models return 1,024 numbers by default (with "
            "256, 512 or 2,048 as options). Each number has no meaning on its own; meaning lives in the "
            "relationships between whole vectors.",
        ),
        Section(
            "cosine", "Measuring similarity",
            "**Cosine similarity** measures the angle between two vectors: 1 means the same direction, 0 "
            "means perpendicular (unrelated in this sense), and −1 means opposite. It is the dot product "
            "divided by the product of the lengths, so it ignores how long the vectors are.\n\n"
            "Many embedding models return unit-length (normalised) vectors. Then the lengths are 1, cosine "
            "similarity equals the dot product, and ranking by Euclidean distance gives the same order. "
            "Check your model's documentation before relying on that.",
            code=Code("python",
                      'import math\n'
                      '\n'
                      'def cosine(a, b):\n'
                      '    dot = sum(x * y for x, y in zip(a, b))\n'
                      '    length = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))\n'
                      '    return dot / length\n'
                      '\n'
                      'cosine([1, 2, 0], [2, 4, 1])   # 0.976: nearly the same direction\n'
                      'cosine([1, 2, 0], [-2, 1, 0])  # 0.0: perpendicular',
                      notes=((4, "Dot product: multiply matching positions and add."),
                             (5, "Product of the two lengths; a zero vector would make this undefined."),
                             (8, "Values close to 1 mean the vectors point the same way.")),
                      caption="Cosine similarity in plain Python (the same function Learning Desk uses for its toy map)"),
        ),
        Section(
            "picture", "A picture you should not over-read",
            "The map places nine phrases by hand in two dimensions so that angles from the origin mirror "
            "meaning: animals one way, payments another, code a third. It is useful for building intuition "
            "about direction and nearest neighbours, and misleading if taken literally. Real embeddings have "
            "hundreds or thousands of dimensions, and any flattening of them to two dimensions distorts "
            "distances.",
            visual="embedding_map",
            callout="Toy data. Use it to see the idea of 'nearest by angle', not to judge how a real model "
                    "would place these phrases.",
        ),
        Section(
            "queries", "Queries and documents",
            "In search, a short question and a long passage are different kinds of text. Some embedding "
            "providers therefore distinguish them: Voyage's documentation recommends setting `input_type` to "
            "`query` or `document`, which prepends a different instruction before embedding and can improve "
            "retrieval quality. Whatever the provider, embed your documents once, store the vectors, and "
            "embed each new query at search time with the same model. Vectors from different models are "
            "not comparable.",
        ),
    ),
    worked_example=Section(
        "worked", "Worked example: cosine similarity by hand",
        "Compare a = (1, 2, 0) with b = (2, 4, 1) and c = (−2, 1, 0).\n\n"
        "1. **a·b** = 1×2 + 2×4 + 0×1 = 10. Lengths: |a| = √5 ≈ 2.236, |b| = √21 ≈ 4.583. "
        "Cosine = 10 / (2.236 × 4.583) ≈ **0.976**.\n"
        "2. **a·c** = 1×(−2) + 2×1 + 0×0 = 0, so the cosine is **0**: the vectors are perpendicular.\n\n"
        "b is almost a scaled copy of a (twice as long, with a small extra component), so its direction "
        "barely differs. Length did not matter, only direction.",
        table=Table(("Pair", "Dot product", "Lengths", "Cosine"),
                    (("a, b", "10", "2.236 × 4.583", "0.976"), ("a, c", "0", "2.236 × 2.236", "0.000")),
                    caption="Values rounded to three decimals"),
    ),
    misconception=Section(
        "misconception", "Misconception: a high score means the passage answers the question",
        "Embeddings capture overall relatedness. A passage can be strongly about the same topic as a "
        "question without answering it, and two sentences that differ by a single *not* are about the same "
        "subject, so they may score as similar while meaning opposite things. Treat similarity as a way to "
        "*shortlist* candidates. Whether a passage actually answers the question, and whether it is correct, "
        "needs reading, a reranker, or evaluation.",
    ),
    activity=Activity(
        "Choose a query and predict its neighbours",
        ("Use the map below. Before choosing a query, predict its three nearest neighbours.",
         "Choose *invoice*. Were you right? Note the similarity values.",
         "Choose *syntax error*. Why is *python function* first, and why do the animal words score below zero?",
         "Recompute one value from the table with the cosine function in the walkthrough."),
        widget="embedding_map",
        reflection="If two of your own notes had a similarity of 0.9, what would you still need to check?",
    ),
    checks=(
        Check("perpendicular", "What is the cosine similarity of two perpendicular vectors?",
              ("0", "1", "−1", "It depends on their lengths"), "0",
              "Perpendicular vectors have a dot product of 0, so the cosine is 0 regardless of length.", "cosine"),
        Check("toy", "Why is the 2-D map labelled illustrative?",
              ("Real embeddings have many more dimensions and the points were placed by hand",
               "Embeddings are always two-dimensional but the colours are invented",
               "Cosine similarity only works in two dimensions",
               "The map is a screenshot from a provider"),
              "Real embeddings have many more dimensions and the points were placed by hand",
              "The picture shows the idea of direction; it is not a real model's output.", "picture"),
        Check("unit", "For unit-length vectors, cosine similarity equals…",
              ("the dot product", "the Euclidean distance", "the number of dimensions", "always 1"),
              "the dot product",
              "With both lengths equal to 1, the denominator is 1.", "cosine"),
    ),
    citations=(
        Citation("mikolov-2013", "Continuous vector representations of words evaluated on similarity tasks."),
        Citation("claude-embeddings", "Anthropic offers no embedding model; Voyage dimensions; normalised vectors "
                 "make cosine equal to dot product; input_type for queries and documents."),
    ),
    prerequisites=("python-data-shapes",),
    related=("retrieval-basics", "attention-basics"),
    scope="Vector similarity is general. Dimensions, normalisation and input_type are properties of specific "
          "embedding models (Voyage, as documented by Anthropic). The map uses hand-placed toy vectors.",
)


RETRIEVAL = Lesson(
    id="retrieval-basics",
    topic="embeddings",
    title="Retrieval: choose documents before generating",
    summary="Separate selecting material from writing an answer, and diagnose which stage went wrong.",
    level="intermediate",
    minutes=30,
    objective="Separate retrieval (selecting material) from generation (writing an answer), and diagnose "
              "which stage caused a poor answer.",
    intro="You cannot send everything you have with every request, and you should not: it costs tokens, "
          "time and privacy, and can reduce quality. **Retrieval** selects a few relevant passages first; "
          "**generation** then writes an answer using only those. The combination is usually called "
          "retrieval-augmented generation (RAG). Treating the two stages separately is the key to "
          "building and debugging it.",
    key_ideas=(
        "RAG pairs a retriever that selects passages with a generator that writes from them.",
        "The model can only use what retrieval puts into its context.",
        "Chunking decides what can be found; chunks can lose the context that made them findable.",
        "Evaluate retrieval and generation separately; they fail in different ways.",
    ),
    overview_visual="retrieval_pipeline",
    sections=(
        Section(
            "stages", "Two stages",
            "Lewis and colleagues (2020) combined a pre-trained generator (knowledge stored in its weights, "
            "*parametric* memory) with a dense vector index of Wikipedia searched by a neural retriever "
            "(*non-parametric* memory). The pattern generalises: an index you control supplies material at "
            "request time, so answers can draw on documents the model never saw in training, and you can "
            "update the documents without retraining anything.",
            visual="retrieval_pipeline",
        ),
        Section(
            "index", "Indexing: chunks and vectors",
            "Before searching, documents are split into **chunks**, each chunk is embedded, and the vectors "
            "are stored with a pointer back to the text. Chunk size is a trade-off: small chunks match "
            "precisely but may lack context; large chunks keep context but dilute the match and cost more "
            "tokens when included.\n\n"
            "Learning Desk splits text in a related way for a different purpose: `sections.split_blocks` "
            "breaks a source on blank lines, never inside a fenced code block, and numbers the passages so "
            "the model can cite them. The app does not embed or search them; the whole selected version is "
            "sent. That works because sources are short and bounded.",
        ),
        Section(
            "select", "Selecting: similarity and beyond",
            "The simplest retriever embeds the question and takes the *k* chunks with the highest cosine "
            "similarity. Anthropic's write-up on contextual retrieval describes common improvements: combine "
            "embeddings with keyword search (BM25) because exact terms such as names and error codes matter, "
            "merge the two rankings, and rerank the candidates with a model to keep only the most relevant. "
            "The same write-up names a core weakness of chunking: a chunk such as \"revenue grew by 3%\" can "
            "lose the company and period it referred to, so it is never retrieved. Adding brief document "
            "context to each chunk before indexing addresses that.",
        ),
        Section(
            "generate", "Generating with citations",
            "The generator receives instructions, the selected chunks (numbered), and the question, and is "
            "asked to answer from them and cite chunk numbers. Citations make answers checkable, but a "
            "citation check has limits. Learning Desk's `check_refs` rejects replies whose references do "
            "not resolve to a supplied passage; the app's own documentation is explicit that this "
            "establishes that a passage *exists*, not that it *supports* the claim.",
            callout="Existence of a citation is cheap to verify in code. Support needs reading or a separate grader.",
        ),
    ),
    worked_example=Section(
        "worked", "Worked example: diagnosing a wrong answer",
        "A user asks \"How long are summaries cached?\" and gets a wrong answer. Work stage by stage:",
        table=Table(("Check", "If the answer is no…", "Stage at fault", "Typical fix"),
                    (("Is the correct passage in the index at all?", "Nothing can retrieve it", "Indexing",
                      "Import the document; check chunking"),
                     ("Is it among the top k for this question?", "The model never saw it", "Retrieval",
                      "Add keyword search, rerank, add chunk context, raise k"),
                     ("Does the answer follow from the passages it was given?", "The model misread or added claims",
                      "Generation", "Tighten instructions; require quotes; grade support"),
                     ("Do the citations point at the passages actually used?", "Answer is uncheckable",
                      "Generation", "Validate citations; show passages beside claims")),
                    caption="Ask the questions in order: a failure early on makes later checks meaningless"),
    ),
    misconception=Section(
        "misconception", "Misconception: retrieval stops hallucination",
        "Retrieval gives the model better material; it does not force the model to use it faithfully. The "
        "generator can still misread a passage, merge two passages incorrectly, or add plausible claims "
        "that appear in neither. And if retrieval selected the wrong passages, a faithful answer will be "
        "faithfully wrong. RAG reduces some failure modes and introduces others, which is why both stages "
        "need their own evaluation.",
    ),
    activity=Activity(
        "Be the retriever",
        ("Question: \"Why does the app refuse very long sources?\" Read these five chunks:",
         "(1) Summaries are cached per version and format. (2) Imports reject private network addresses. "
         "(3) Sources over 100,000 characters or 500 passages are refused before any call. (4) Each "
         "request uses one call; no automatic retry. (5) Long requests cost more tokens and time.",
         "Choose the two chunks you would send. Which words did you match on, and which did you infer?",
         "Which chunk would a keyword search find most easily? Which needs meaning rather than words?",
         "Write the one-sentence answer, citing your chunks. Would it still be right if you had picked (1) and (4)?"),
        widget="retrieval_pipeline",
        reflection="Retrieval errors are silent: the model answers confidently from whatever it received.",
    ),
    checks=(
        Check("stage", "The correct passage exists in the index but was not in the top 5. Which stage failed?",
              ("Retrieval", "Generation", "Tokenization", "Validation"), "Retrieval",
              "The model never received the passage, so generation could not use it.", "worked"),
        Check("cite", "What does Learning Desk's citation check establish?",
              ("That each cited passage exists in the supplied source",
               "That each claim is supported by its passage",
               "That the answer is correct",
               "That no passage was ignored"),
              "That each cited passage exists in the supplied source",
              "The check resolves references; it does not judge support or truth.", "generate"),
        Check("context", "Why add document context to chunks before indexing?",
              ("A chunk can lose the names or period it referred to, so it is never retrieved",
               "To make chunks longer for the model",
               "Embedding models require a title",
               "To reduce the number of chunks"),
              "A chunk can lose the names or period it referred to, so it is never retrieved",
              "Contextual retrieval restores the missing context so the chunk matches relevant questions.", "select"),
    ),
    citations=(
        Citation("lewis-2020", "RAG combines parametric memory with a dense vector index searched by a neural retriever."),
        Citation("anthropic-contextual-retrieval", "Chunks lose context; embeddings plus BM25 with rank fusion; reranking."),
        Citation("claude-embeddings", "Embedding queries and documents for retrieval."),
        Citation("app-learning", "Numbered passages and check_refs: references must resolve to supplied passages."),
    ),
    prerequisites=("embeddings-similarity", "context-vs-storage"),
    related=("evaluation-basics", "structured-outputs"),
    scope="General RAG pattern. Contextual retrieval and reranking details come from one provider's published "
          "write-up. Learning Desk itself does not embed or search; it sends one bounded source.",
)

LESSONS = (EMBEDDINGS, RETRIEVAL)
