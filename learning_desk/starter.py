"""Optional suggestions, never automatically inserted into personal learning history."""

PATH = [
    {
        "title": "1. Python functions and dictionaries",
        "note": "Try writing a function that accepts a dictionary and returns one value.",
        "links": [
            (
                "Defining functions",
                "https://docs.python.org/3/tutorial/controlflow.html#defining-functions",
            ),
            (
                "Dictionaries",
                "https://docs.python.org/3/tutorial/datastructures.html#dictionaries",
            ),
        ],
    },
    {
        "title": "2. JSON and schemas",
        "note": "Encode a dictionary as JSON, then describe which keys and types you expect.",
        "links": [
            (
                "Python JSON documentation",
                "https://docs.python.org/3/library/json.html",
            ),
            (
                "Creating your first JSON Schema",
                "https://json-schema.org/learn/getting-started-step-by-step",
            ),
        ],
    },
    {
        "title": "3. APIs and request flow",
        "note": "Trace a request from client to server and the response back to the client.",
        "links": [
            (
                "MDN: Overview of HTTP",
                "https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Overview",
            )
        ],
    },
    {
        "title": "4. Context versus storage",
        "note": "Context is material supplied to a model call. Persistent storage keeps records between calls. Compare a request snapshot with a SQLite record in this app.",
        "links": [
            (
                "Python SQLite documentation",
                "https://docs.python.org/3/library/sqlite3.html",
            )
        ],
    },
    {
        "title": "5. Model feedback versus verified correctness",
        "note": "A model answer is a claim to check. Try a small deterministic example, inspect its actual result, and compare it with model feedback. Matching a model key does not verify the key.",
        "links": [
            (
                "Python assertions",
                "https://docs.python.org/3/reference/simple_stmts.html#the-assert-statement",
            )
        ],
    },
    {
        "title": "6. Basic evaluation",
        "note": "Choose a few cases with known expected results. Include an edge case. Compare actual results with expectations and record failures; do not turn one success into a broad claim.",
        "links": [
            (
                "Python unittest documentation",
                "https://docs.python.org/3/library/unittest.html",
            )
        ],
    },
]
