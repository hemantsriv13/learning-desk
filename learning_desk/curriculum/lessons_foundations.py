"""Lessons for topics 1–2: Python data shapes, JSON, HTTP request flow, and API keys."""

from .model import Activity, Check, Citation, Code, Lesson, Section, Table

PYTHON_DATA_SHAPES = Lesson(
    id="python-data-shapes",
    topic="python",
    title="Python data shapes for AI apps: dictionaries, lists and functions",
    summary="Read and reshape the nested dictionaries and lists that model APIs send and receive.",
    level="introductory",
    minutes=25,
    objective="Read and build the nested dictionaries and lists that AI APIs exchange, and wrap each "
              "reshaping step in a small function that fails clearly when data is missing.",
    intro="Most code around a language model is not about the model. It moves data: building a request "
          "from saved notes, pulling text out of a response, recording what happened. In Python that data "
          "arrives as **dictionaries** and **lists**, usually nested inside each other. Getting fluent with "
          "these two shapes, and with small functions that name each step, removes a large share of the "
          "friction in AI projects.",
    key_ideas=(
        "A dictionary maps keys to values; a list keeps items in order by position.",
        "API responses nest them. Walk a nested value one bracket at a time.",
        "A function gives one reshaping step a name, inputs and a single return value.",
        "A missing key raises KeyError. Decide on purpose whether to fail loudly or use a default.",
    ),
    overview_visual="python_shapes",
    sections=(
        Section(
            "dicts", "Dictionaries: values found by name",
            "A dictionary stores **key: value** pairs. You look a value up by its key rather than by "
            "position, which makes dictionaries the natural shape for records: a request, a response, a "
            "configuration. Keys must be immutable, so strings and numbers are typical keys; values can be "
            "anything, including other dictionaries and lists.\n\n"
            "Three operations cover most needs: `d[key]` reads a value and raises `KeyError` if the key is "
            "absent; `d.get(key, default)` returns the default instead; and `key in d` checks without "
            "reading. Looping over `d.items()` gives you each key with its value.",
            code=Code("python",
                      'request = {"model": "example-model", "max_tokens": 1024}\n'
                      'request["max_tokens"]            # 1024\n'
                      'request.get("system", "")        # "" because the key is absent\n'
                      '"messages" in request             # False\n'
                      'for key, value in request.items():\n'
                      '    print(key, "=", value)',
                      notes=((2, "Square brackets: the key must exist, or Python raises KeyError."),
                             (3, ".get() supplies a fallback for genuinely optional fields."),
                             (5, ".items() yields (key, value) pairs in insertion order.")),
                      caption="Reading a request dictionary"),
        ),
        Section(
            "lists", "Lists: values found by position",
            "A list keeps items in order. Positions start at **0**, and negative positions count from the "
            "end, so `items[-1]` is the last item. Lists grow with `append`, and a `for` loop visits each "
            "item in order.\n\n"
            "Model APIs use lists wherever order matters: the turns of a conversation, the content blocks of "
            "a reply, a set of retrieved passages. When you see a list in a response, ask two questions: "
            "*could it be empty?* and *does the position mean anything, or should I look for the item by a "
            "field such as its type?*",
            code=Code("python",
                      'messages = []\n'
                      'messages.append({"role": "user", "content": "Hello"})\n'
                      'messages.append({"role": "assistant", "content": "Hi!"})\n'
                      'messages[0]["role"]   # "user"\n'
                      'messages[-1]["content"]  # "Hi!"\n'
                      'len(messages)          # 2',
                      notes=((2, "append() adds to the end, preserving order."),
                             (4, "Position 0 is the first item."),
                             (5, "Position -1 is the last item, whatever the length.")),
                      caption="A conversation is a list of dictionaries"),
        ),
        Section(
            "nesting", "Nesting: following a path",
            "Real responses combine the two shapes. To reach a value, read the path from the outside in: "
            "each pair of brackets is one step, a **string key** into a dictionary or an **integer "
            "position** into a list. Writing the path out loud (\"the content list, its first block, that "
            "block's text\") catches most mistakes before you run anything.",
            visual="python_shapes",
            callout="If a step fails, print the value one level up: `type(x)` and `x.keys()` or `len(x)` "
                    "usually show what you have instead.",
        ),
        Section(
            "functions", "Functions: naming one step",
            "A function packages a step so it can be named, tested and reused. Parameters are its inputs; "
            "`return` hands back one value. A function that reaches its end without a `return` statement "
            "returns `None`, which is a common source of confusing errors further along.\n\n"
            "Small functions with clear names (`build_request`, `reply_text`, `count_output_tokens`) make "
            "AI code easier to follow than one long block, and each can be checked separately with a known "
            "input. Type hints such as `-> str` document intent; Python does not enforce them at run time.",
            code=Code("python",
                      'def output_tokens(response: dict) -> int:\n'
                      '    """How many tokens the model produced, as reported in usage."""\n'
                      '    return response["usage"]["output_tokens"]\n'
                      '\n'
                      'def describe(response: dict):\n'
                      '    print(output_tokens(response), "tokens")\n'
                      '\n'
                      'result = describe({"usage": {"output_tokens": 31}})  # prints, then result is None',
                      notes=((1, "Parameters and the return type are documented in the signature."),
                             (3, "One path, one value returned."),
                             (5, "No return statement here…"),
                             (8, "…so the call evaluates to None.")),
                      caption="A function that returns, and one that only prints"),
        ),
    ),
    worked_example=Section(
        "worked", "Worked example: joining the text of a reply",
        "A Messages-style reply holds a list of content blocks. Some are text; others (for example tool "
        "requests) are not. The task is to join the text blocks into one string.\n\n"
        "1. **Start from the outside**: the reply is a dictionary; its `\"content\"` key holds a list.\n"
        "2. **Loop over the list**, because the number of blocks varies.\n"
        "3. **Choose by field, not by position**: keep blocks whose `\"type\"` is `\"text\"`.\n"
        "4. **Return one value**, so the caller decides what to do with it.\n\n"
        "Learning Desk does the same thing with the provider SDK's objects in `provider.py`: it joins "
        "`block.text` for every block whose `block.type` is `\"text\"`.",
        code=Code("python",
                  'def reply_text(response: dict) -> str:\n'
                  '    """Join the text blocks of a Messages-style response."""\n'
                  '    parts = []\n'
                  '    for block in response["content"]:\n'
                  '        if block.get("type") == "text":\n'
                  '            parts.append(block["text"])\n'
                  '    return "".join(parts)\n'
                  '\n'
                  'reply = {"content": [{"type": "text", "text": "Hello"},\n'
                  '                     {"type": "tool_use", "name": "search"},\n'
                  '                     {"type": "text", "text": " again"}]}\n'
                  'reply_text(reply)  # "Hello again"',
                  notes=((4, "\"content\" is required, so square brackets: a missing list should fail loudly."),
                         (5, "Blocks differ, so .get() reads the type without assuming every field exists."),
                         (7, "Joining once at the end is clearer than adding strings in the loop."),
                         (10, "The non-text block is skipped rather than causing an error.")),
                  caption="Choose blocks by type; never assume the first block is the text"),
    ),
    misconception=Section(
        "misconception", "Misconception: .get() is always the safer choice",
        "`d.get(key)` never raises, which can feel safer. But for a value your code *needs*, it only "
        "postpones the failure: `None` flows onward and breaks later, far from the cause, often with a less "
        "helpful message.\n\n"
        "Use square brackets for **required** fields, so a malformed record fails immediately where the "
        "problem is. Use `.get()` with an explicit default for **optional** fields, where absence is "
        "normal. When data comes from outside your program (a model, a file, a web page), validate it once "
        "at the boundary rather than sprinkling defaults throughout.",
        table=Table(("Field", "Required?", "Read it with"),
                    (("response[\"content\"]", "Yes", "response[\"content\"]"),
                     ("block[\"type\"]", "Varies by block", "block.get(\"type\")"),
                     ("settings[\"system\"]", "No (optional prompt)", "settings.get(\"system\", \"\")")),
                    caption="Choose by meaning, not by habit"),
    ),
    activity=Activity(
        "Trace and break a path",
        ("Open a Python prompt in your own terminal (the app does not run code).",
         "Paste the `reply` dictionary from the worked example and evaluate `reply[\"content\"][2][\"text\"]`.",
         "Predict, then check, what `reply[\"content\"][1][\"text\"]` does. Which line of the worked "
         "example protects against it?",
         "Write `first_text(response)` that returns the first text block, or raises `ValueError` with a "
         "clear message when there is none.",
         "Call it on `{\"content\": []}` and read the error message as a stranger would."),
        widget=None,
        reflection="Which fields in the replies you handle are truly optional? Write them down; everything "
                   "else should be read with square brackets.",
    ),
    checks=(
        Check("path", 'Given response = {"content": [{"type": "text", "text": "Hi"}]}, which expression '
                      'evaluates to "Hi"?',
              ('response["content"]["text"]', 'response["content"][0]["text"]',
               'response[0]["content"]["text"]', 'response.content[0].text'),
              'response["content"][0]["text"]',
              "\"content\" holds a list, so the next step is a position ([0]); that item is a dictionary, so "
              "the last step is a key ([\"text\"]). Attribute access (.content) works on SDK objects, not "
              "on plain dictionaries.", "nesting"),
        Check("none", "What does a Python function return when it has no return statement?",
              ("0", "None", "An empty string", "It raises an error"), "None",
              "Falling off the end of a function returns None. Printing inside a function is not the same "
              "as returning a value.", "functions"),
        Check("required", 'Your code cannot work without config["model"]. Which way of reading it is best?',
              ('config["model"], so a missing key fails immediately',
               'config.get("model"), so it never fails',
               'config.get("model", "") and continue',
               "Wrap every access in try/except and ignore errors"),
              'config["model"], so a missing key fails immediately',
              "For a required value, an immediate KeyError at the boundary is easier to diagnose than a None "
              "that breaks something later.", "misconception"),
    ),
    citations=(
        Citation("py-datastructures", "Dictionaries map keys (immutable) to values; list methods; looping "
                 "over items()."),
        Citation("py-functions", "Defining functions; a function without return returns None; default and "
                 "keyword arguments."),
        Citation("py-json", "JSON objects decode to Python dicts and arrays to lists."),
        Citation("app-provider", "Learning Desk joins the text of every text-type content block."),
    ),
    further_reading=(Citation("py-errors", "Handling and raising exceptions such as KeyError and ValueError."),),
    related=("json-basics",),
    scope="General Python. The response shape is simplified from a Messages-style API for teaching.",
)


JSON_BASICS = Lesson(
    id="json-basics",
    topic="web",
    title="JSON: the shape of data on the wire",
    summary="Recognise JSON's six value types, convert to and from Python, and describe an expected shape.",
    level="introductory",
    minutes=25,
    objective="Read any JSON document by identifying its value types, convert it to and from Python, and "
              "explain why successful parsing does not mean the data is what you expected.",
    intro="JSON is the format most AI APIs use for both requests and responses, and the format Learning "
          "Desk uses to store model output. It is plain text with a small grammar, which is why nearly "
          "every language can read it. The skill is not memorising the grammar; it is reading a document's "
          "**shape** quickly and knowing what parsing does and does not check.",
    key_ideas=(
        "JSON has four primitive types (string, number, boolean, null) and two structured types (object, array).",
        "json.loads turns JSON text into Python objects; json.dumps turns them back into text.",
        "Parsing checks syntax only. It does not check that the fields you need are present or sensible.",
        "A JSON Schema states the expected shape: types, properties and which are required.",
    ),
    overview_visual="json_anatomy",
    sections=(
        Section(
            "types", "Six kinds of value",
            "An **object** is an unordered set of name–value pairs in braces; names are always strings in "
            "double quotes. An **array** is an ordered list in square brackets. Everything else is a "
            "**string** (double quotes), a **number**, `true`/`false`, or `null`.\n\n"
            "Notice what is missing: there is no date type, no integer-versus-decimal distinction in the "
            "grammar, and no comments. Dates travel as strings by convention, which is why a schema or "
            "documentation must say which format to expect. The standard also says names within an object "
            "*should* be unique; when they are not, different software may behave differently.",
            visual="json_anatomy",
            table=Table(("JSON", "Python after json.loads"),
                        (("object", "dict"), ("array", "list"), ("string", "str"),
                         ("number (integer)", "int"), ("number (real)", "float"),
                         ("true / false", "True / False"), ("null", "None")),
                        caption="The conversion table from Python's json documentation"),
        ),
        Section(
            "convert", "Text in, objects out",
            "`json.loads` (load *string*) parses text into Python objects; `json.dumps` (dump *string*) "
            "serialises them back into text. Use `indent=2` when a person will read the result.\n\n"
            "A parse either succeeds completely or raises an error; there is no partial result. Code that "
            "parses data from outside the program (a model reply, an import) should expect that error and "
            "report it rather than crash or guess.",
            code=Code("python",
                      'import json\n'
                      '\n'
                      'text = \'{"minutes": 20, "complete": true, "tags": ["tokens"]}\'\n'
                      'record = json.loads(text)\n'
                      'record["complete"]        # True (a Python bool)\n'
                      'record["tags"][0]         # "tokens"\n'
                      'json.dumps(record, indent=2)  # back to text\n'
                      '\n'
                      'try:\n'
                      '    json.loads(\'{"minutes": 20,}\')   # trailing comma\n'
                      'except json.JSONDecodeError as error:\n'
                      '    print("Not valid JSON:", error)',
                      notes=((4, "Text becomes a dict because the outermost value is an object."),
                             (5, "JSON true becomes Python True."),
                             (10, "Trailing commas are not allowed in JSON."),
                             (11, "JSONDecodeError says where parsing stopped.")),
                      caption="Parsing and serialising with the standard library"),
        ),
        Section(
            "meaning", "Syntax is not meaning",
            "`json.loads` tells you the text is well-formed JSON. It says nothing about whether the object "
            "has the keys you need, whether a number is in range, or whether a list is empty. All of these "
            "parse successfully:\n\n"
            "- `{}`: a valid, empty object.\n"
            "- `{\"answer\": null}`: the key is present but holds nothing.\n"
            "- `{\"minutes\": \"twenty\"}`: the right key with the wrong type.\n\n"
            "Checking shape and meaning is a separate step, either with explicit code or with a schema "
            "validator. Learning Desk always does that second step before saving model output.",
            callout="Parsed is not the same as valid. Keep the two words distinct in your head and in your error messages.",
        ),
        Section(
            "schema", "Describing shape with JSON Schema",
            "JSON Schema is itself JSON. The core keywords are `type` (what kind of value), `properties` "
            "(the expected keys of an object and a schema for each) and `required` (keys that must be "
            "present). A schema is useful twice: as documentation a person can read, and as input to a "
            "validator or a model provider that can enforce it.\n\n"
            "Learning Desk generates schemas from Pydantic models and sends them with structured-output "
            "requests; the *Structured outputs* lesson follows that path in detail.",
            code=Code("json",
                      '{\n'
                      '  "type": "object",\n'
                      '  "properties": {\n'
                      '    "question": {"type": "string"},\n'
                      '    "options":  {"type": "array", "items": {"type": "string"}},\n'
                      '    "answer":   {"type": "string"}\n'
                      '  },\n'
                      '  "required": ["question", "options", "answer"]\n'
                      '}',
                      notes=((2, "The document must be an object."),
                             (5, "An array whose items are all strings."),
                             (8, "All three keys must be present; extra rules (answer is one of the options) "
                                 "need code.")),
                      caption="A schema for one multiple-choice question"),
        ),
    ),
    worked_example=Section(
        "worked", "Worked example: checking a saved record",
        "Suppose a quiz question arrives as JSON text. Parsing is step one; then check the fields you rely "
        "on and one rule a basic schema cannot express: the answer must be one of the options. Learning "
        "Desk applies that same rule to generated multiple-choice questions before saving them.",
        code=Code("python",
                  'import json\n'
                  '\n'
                  'raw = \'{"question": "What is a token?", "options": ["A word", "A piece of text"], \' \\\n'
                  '      \'"answer": "A piece of text"}\'\n'
                  'record = json.loads(raw)\n'
                  '\n'
                  'missing = [k for k in ("question", "options", "answer") if k not in record]\n'
                  'if missing:\n'
                  '    raise ValueError(f"Missing fields: {missing}")\n'
                  'if not isinstance(record["options"], list):\n'
                  '    raise ValueError("options must be a list")\n'
                  'if record["answer"] not in record["options"]:\n'
                  '    raise ValueError("answer must be one of the options")',
                  notes=((5, "Step 1: syntax. Raises JSONDecodeError on malformed text."),
                         (7, "Step 2: presence of required keys, reported together."),
                         (10, "Step 3: type of a field the next check depends on."),
                         (12, "Step 4: a cross-field rule; schemas alone usually cannot say this.")),
                  caption="Parse, then check presence, type and rules"),
    ),
    misconception=Section(
        "misconception", "Misconception: valid JSON means correct data",
        "A reply that parses is only *readable*. It can still be missing fields, have values of the wrong "
        "type, contain an answer that is not among the options, or be factually wrong. Each of those needs "
        "its own check, and the last one (truth) usually cannot be checked by code at all.\n\n"
        "A useful habit is to name each check explicitly in error messages: \"not JSON\", \"missing field\", "
        "\"wrong type\", \"rule broken\". When something fails later, you will know which layer to look at.",
    ),
    activity=Activity(
        "Inspect JSON safely",
        ("Use the JSON inspector below. Paste the schema from the Walkthrough and check that it parses.",
         "Remove one closing brace. Read where the error says parsing stopped.",
         "Paste `{\"minutes\": \"twenty\"}`. It parses; which check from the worked example would catch it?",
         "Write a JSON object describing one of your current learning goals with a string, a number, a "
         "boolean, a null and an array. Inspect it."),
        widget="json_inspector",
        reflection="The inspector only parses: it shows types and never runs anything you paste.",
    ),
    checks=(
        Check("type", "Which of these is NOT a JSON value type?", ("string", "null", "date", "array"), "date",
              "JSON has strings, numbers, booleans, null, objects and arrays. Dates travel as strings, so "
              "their format must be agreed separately.", "types"),
        Check("loads", 'What does json.loads(\'{"ok": true}\') return in Python?',
              ('The dict {"ok": True}', "The string '{\"ok\": true}'", "True", "A JSONDecodeError"),
              'The dict {"ok": True}',
              "The outermost value is an object, so the result is a dict; JSON true becomes Python True.",
              "convert"),
        Check("parsed", 'A reply parses without error but has no "answer" key. What has been established?',
              ("Only that the text is syntactically valid JSON",
               "That the reply is complete",
               "That the reply matches the schema",
               "That the answer is correct"),
              "Only that the text is syntactically valid JSON",
              "Parsing checks syntax. Presence, types and rules need separate checks.", "meaning"),
    ),
    citations=(
        Citation("rfc8259", "JSON's four primitive and two structured types; object names SHOULD be unique."),
        Citation("py-json", "json.loads/json.dumps and the JSON-to-Python conversion table."),
        Citation("jsonschema-start", "The type, properties and required keywords."),
        Citation("app-learning", "Generated multiple-choice keys must match one of four options before saving."),
    ),
    further_reading=(Citation("pydantic-models", "Validating parsed data against Python models."),),
    prerequisites=("python-data-shapes",),
    related=("structured-outputs", "http-request-flow"),
    scope="General: JSON is a standard and the json module is part of Python. Schema use by providers is "
          "covered in Structured outputs.",
)


HTTP_REQUEST_FLOW = Lesson(
    id="http-request-flow",
    topic="web",
    title="HTTP and API calls: following one request",
    summary="Trace a model call from click to storage, read requests and responses, and plan for failure.",
    level="introductory",
    minutes=30,
    objective="Trace an API call from the interface to storage, name the parts of an HTTP request and "
              "response, and decide in advance what should happen at each kind of failure.",
    intro="When you press a button that \"asks the AI\", a chain of ordinary software runs: your interface, "
          "a backend, an HTTPS request across the internet, a provider's servers, and code that checks and "
          "stores the result. Each link can fail independently. Seeing the whole chain turns error "
          "messages into locations you can reason about.",
    key_ideas=(
        "HTTP is request and response: method, path, headers and body go out; status, headers and body come back.",
        "Status classes: 2xx success, 4xx a problem with the request, 5xx a problem on the server side.",
        "HTTP is stateless: each request stands alone unless the client sends context again.",
        "Every step can fail. Decide what is recorded and shown before it happens.",
    ),
    overview_visual="request_flow",
    sections=(
        Section(
            "anatomy", "Request and response",
            "A request has a **method** (what to do, such as GET to read or POST to submit), a **path** "
            "(which resource), **headers** (metadata such as content type and credentials) and, for POST, "
            "a **body** with the data. The response mirrors it: a **status code** with a short reason, "
            "headers, and a body.\n\n"
            "Model APIs typically use POST with a JSON body describing the model, limits and messages. The "
            "JSON reply contains the generated content, a stop reason and token usage.",
            visual="http_anatomy",
        ),
        Section(
            "status", "Status codes tell you how to read the body",
            "Read the status before the body. A 2xx body is a result; a 4xx or 5xx body is an error "
            "description. The first digit tells you who should act: 4xx means something about *your* request "
            "needs to change; 5xx means the server had a problem, and the same request might succeed later.",
            table=Table(("Status", "Meaning", "Usual response"),
                        (("200 OK", "Processed successfully", "Read and validate the body"),
                         ("400 Bad Request", "Request format or content rejected", "Fix the request; retrying unchanged will fail again"),
                         ("401 Unauthorized", "Not authenticated: credential missing or invalid", "Check the key"),
                         ("403 Forbidden", "Authenticated but not permitted", "Check access to the model or feature"),
                         ("404 Not Found", "Resource or model name not found", "Check the path or model name"),
                         ("429 Too Many Requests", "Rate limited", "Wait (honour retry-after if present)"),
                         ("500 Internal Server Error", "Unexpected server failure", "Retry later, carefully"),
                         ("529 (provider-specific)", "Anthropic: API temporarily overloaded", "Retry later")),
                        caption="Common statuses for model APIs. 529 is Anthropic-specific, not a standard HTTP status."),
        ),
        Section(
            "this-app", "Following a request through Learning Desk",
            "In this app, `provider.build_request` assembles the request (model, token limit, instructions, "
            "one user message, and an output schema). `provider.send` makes **exactly one attempt**: the SDK "
            "client is created with `max_retries=0`, and each known failure (401, 403, 404, 429, 400, other "
            "statuses, timeouts, connection errors) becomes a readable message.\n\n"
            "`ai._run` times the call, parses and validates the reply, and inserts an `ai_calls` record "
            "**whether the call succeeded or failed**, including the request sent, the raw response, the "
            "model reported back, token usage and elapsed time. That record is what *Inspect AI call* shows.",
            visual="request_flow",
        ),
        Section(
            "retries", "Retries and idempotency",
            "A request is **idempotent** if sending it twice has the same effect as sending it once. GET is "
            "designed to be; POST is not guaranteed to be. A model call is a POST, and every attempt is "
            "processed and billed separately, so a retry is a decision, not a free action.\n\n"
            "Anthropic's SDK retries some transient failures (connection errors, rate limits, 5xx) "
            "automatically, twice by default. Learning Desk turns that off so one click is at most one "
            "billable attempt, and asks you to retry deliberately. Other applications reasonably choose "
            "automatic retries with backoff; what matters is choosing on purpose.",
            callout="Before adding automatic retries to a billed call, decide the maximum number of attempts "
                    "and what the user sees while they happen.",
        ),
    ),
    worked_example=Section(
        "worked", "Worked example: reading one failure",
        "Suppose you click **Generate quick read** during a burst of activity and the provider answers "
        "429. Follow it through the code:\n\n"
        "1. The SDK raises `RateLimitError`; `provider.send` converts it to \"Rate limited (429). Wait and "
        "try again.\" with the provider's details.\n"
        "2. `ai._run` catches the error, records `status='error'`, the message, and the elapsed time.\n"
        "3. Nothing is saved as a summary, so the reader still offers the button.\n"
        "4. You can open the call record to see exactly what was sent and what came back.\n\n"
        "No retry happened, nothing was invented, and the failure is inspectable later.",
        code=Code("python",
                  'client = anthropic.Anthropic(max_retries=0, timeout=config.timeout_seconds())\n'
                  'try:\n'
                  '    response = client.messages.create(**request)\n'
                  'except anthropic.AuthenticationError:\n'
                  '    raise ProviderError("The API key was rejected (401). Check ANTHROPIC_API_KEY.")\n'
                  'except anthropic.RateLimitError as e:\n'
                  '    raise ProviderError(f"Rate limited (429). Wait and try again. Details: {e.message}")\n'
                  'except anthropic.APITimeoutError:\n'
                  '    raise ProviderError("No response within … seconds. Nothing was saved from this attempt.")',
                  notes=((1, "One attempt per click; a timeout bounds the wait."),
                         (4, "Each provider error type maps to a message a person can act on."),
                         (8, "A timeout is a failure too, and is reported the same way.")),
                  caption="Excerpt (shortened) from learning_desk/provider.py"),
    ),
    misconception=Section(
        "misconception", "Misconception: a 200 response means the answer is right",
        "200 means the server processed the request. The content can still be unusable: the reply may have "
        "stopped at the token limit (`stop_reason` of `max_tokens`) and be incomplete, the model may have "
        "declined (`refusal`), or the text may not match the shape your code needs. Learning Desk treats the "
        "first two as errors in `provider.send` and checks the third in validation.\n\n"
        "And even a complete, well-formed reply can be factually wrong. Transport success, format validity "
        "and correctness are three separate questions.",
    ),
    activity=Activity(
        "Inspect a real call record",
        ("If you have used an AI action in this app, open the resource or notebook session and find "
         "*AI call history* or *Inspect AI call*.",
         "Identify the status, elapsed time, requested model and returned model.",
         "In *Request sent*, find the model name, the token limit and the system instructions. Confirm no "
         "API key appears.",
         "If you have no calls yet, use the request-flow diagram: for each failure, say which step it "
         "happens at and what the app records."),
        reflection="Which of the six steps could fail without any error message in a less careful app?",
    ),
    checks=(
        Check("auth", "A request returns 403. Compared with 401, what is different?",
              ("The caller is known but not permitted to do this",
               "The credential is missing or invalid",
               "The server is overloaded",
               "The request body is not valid JSON"),
              "The caller is known but not permitted to do this",
              "401 means not authenticated; 403 means authenticated but lacking permission.", "status"),
        Check("retries", "Why does Learning Desk create its client with max_retries=0?",
              ("So each click makes at most one billable attempt",
               "Because the provider forbids retries",
               "Because POST requests cannot be retried",
               "To make requests faster"),
              "So each click makes at most one billable attempt",
              "Retries are allowed and sometimes sensible, but each attempt is billed. The app leaves that "
              "decision to you.", "retries"),
        Check("truncated", "A reply arrives with status 200 and stop_reason max_tokens. What should the app assume?",
              ("The output may be incomplete and should not be used as finished",
               "The answer is complete and correct",
               "The key was rejected",
               "The request should be retried automatically until it succeeds"),
              "The output may be incomplete and should not be used as finished",
              "The status says the request was processed; the stop reason says generation was cut off.",
              "misconception"),
    ),
    citations=(
        Citation("mdn-http-overview", "HTTP as client–server request/response; message parts; stateless but not sessionless."),
        Citation("mdn-status", "Status code classes and the meanings of 401, 403 and 429."),
        Citation("mdn-idempotent", "GET is idempotent; POST is not guaranteed to be."),
        Citation("claude-errors", "Anthropic error types including 529 overloaded; SDK retries twice by default."),
        Citation("claude-api-overview", "Required request headers and request size limits."),
        Citation("app-provider", "One attempt (max_retries=0), error mapping, refusal and max_tokens handling."),
        Citation("app-ai", "Every call, successful or failed, is recorded with timing and usage."),
    ),
    prerequisites=("json-basics",),
    related=("api-keys-auth", "latency-cost-reliability", "structured-outputs"),
    scope="HTTP methods and status classes are general. 529, header names and SDK retry defaults are "
          "Anthropic-specific; other providers differ.",
)


API_KEYS_AUTH = Lesson(
    id="api-keys-auth",
    topic="web",
    title="API keys and authentication basics",
    summary="How a key proves who is calling, where to keep it, and how to read 401 and 403.",
    level="introductory",
    minutes=20,
    objective="Explain how an API key identifies the caller, keep keys out of code, logs and history, and "
              "interpret authentication and permission failures.",
    intro="An API key is a long random string that tells the provider which account is calling. Anyone who "
          "holds it can make requests, and spend money, as you. Handling keys well is mostly about "
          "*where they live*: in the environment, never in source code, logs, exports or screenshots.",
    key_ideas=(
        "Authentication asks who is calling (401 when it fails); authorisation asks what they may do (403).",
        "An API key is a bearer secret: whoever presents it is treated as you.",
        "Keep keys in the environment and load them at run time; keep them out of git.",
        "HTTPS protects the key in transit. It cannot protect a key you have pasted somewhere else.",
    ),
    overview_visual="auth_flow",
    sections=(
        Section(
            "who", "Who is calling, and what may they do?",
            "Two different questions hide behind \"access denied\". **Authentication** establishes identity: "
            "is this a valid credential? **Authorisation** establishes permission: may this identity use "
            "this model or feature? HTTP gives them different statuses. 401 means the request is not "
            "authenticated; 403 means the server knows who you are but refuses.\n\n"
            "Anthropic's API follows the same split: 401 `authentication_error` for a malformed, revoked or "
            "expired key, and 403 `permission_error` when the key lacks permission for the resource.",
        ),
        Section(
            "headers", "Credentials travel in headers",
            "HTTP's general pattern is an `Authorization: <type> <credentials>` header. Model providers "
            "document their own header names. Anthropic currently accepts `Authorization: Bearer <key>` "
            "or the older `x-api-key` header, alongside a required `anthropic-version` header. Official "
            "SDKs add these for you, which is one reason to use them.",
            visual="auth_flow",
        ),
        Section(
            "storage", "Keeping keys out of code",
            "Put the key in an **environment variable**. Python reads environment variables through "
            "`os.environ`; many projects load a local `.env` file into the environment at start-up with "
            "`python-dotenv`. The `.env` file must be listed in `.gitignore` so it never enters version "
            "control, where it would persist in history even after deletion.\n\n"
            "OWASP's guidance adds operational habits: avoid hard-coding secrets, grant the least privilege "
            "needed, and rotate secrets regularly. A per-project key with a spend limit is easier to revoke "
            "and limits damage if it leaks.",
            callout="Search before you commit: a key pasted into a test file is the most common leak.",
        ),
        Section(
            "transport", "Transport security",
            "HTTPS (HTTP over TLS) encrypts the request, headers included, between your computer and the "
            "provider. MDN notes that some schemes, such as Basic authentication, only *encode* "
            "credentials, so they are insecure without HTTPS. TLS does nothing for a key that appears in a "
            "screenshot, a shared log, a chat message or an exported file.",
        ),
    ),
    worked_example=Section(
        "worked", "Worked example: how Learning Desk handles the key",
        "Learning Desk never reads, stores or displays the key's value. `config.api_key_present()` only "
        "reports whether one is set, which is what Settings shows. The Anthropic SDK reads "
        "`ANTHROPIC_API_KEY` from the environment itself. `provider.build_request` builds the request "
        "without credentials, so the request saved in every call record contains none. A rejected key "
        "becomes a clear 401 message rather than a stack trace.",
        code=Code("python",
                  'def api_key_present() -> bool:\n'
                  '    """Only reports whether a key exists. Never returns or logs the key."""\n'
                  '    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())\n'
                  '\n'
                  '# provider.send\n'
                  'if not config.api_key_present():\n'
                  '    raise ProviderError("No API key found. Set ANTHROPIC_API_KEY in your environment or .env file.")',
                  notes=((3, "A boolean leaves the module; the value itself does not."),
                         (6, "Fail before any network traffic when no key is configured.")),
                  caption="From learning_desk/config.py and provider.py"),
    ),
    misconception=Section(
        "misconception", "Misconception: a private repository is a safe place for a key",
        "Private repositories get cloned to laptops, shared with collaborators, connected to CI services, "
        "and occasionally made public. Git history keeps every committed version, so deleting the line "
        "later does not remove it. Treat any key that has been committed as leaked: revoke it in the "
        "provider console, create a new one, and update your `.env`.",
    ),
    activity=Activity(
        "Check your own setup",
        ("In a terminal in this repository, run `git check-ignore .env`. It should print `.env`.",
         "Open **Settings & About** in this app: the API key row should say *set* or *NOT set*, never the value.",
         "Search your other projects for hard-coded keys before your next commit.",
         "In your provider console, check whether your key has a spend limit and an expiry you are comfortable with."),
        reflection="If this key leaked today, how long would it take you to revoke and replace it?",
    ),
    checks=(
        Check("forbidden", "Your key is valid, but a request for one model returns 403. What is the most likely cause?",
              ("The key lacks permission for that model or feature",
               "The key is malformed",
               "You sent too many requests",
               "The JSON body is invalid"),
              "The key lacks permission for that model or feature",
              "403 means authenticated but not permitted. A malformed key gives 401; too many requests gives 429.",
              "who"),
        Check("where", "Where should an application's API key live?",
              ("In an environment variable, loaded at run time",
               "In a constant at the top of the source file",
               "In the README so collaborators can find it",
               "In the app's exported data"),
              "In an environment variable, loaded at run time",
              "Keep secrets outside code and version control; load them from the environment.", "storage"),
        Check("tls", "Does HTTPS make it safe to paste your key into a support chat?",
              ("No. HTTPS protects requests in transit, not copies of the key elsewhere",
               "Yes, because HTTPS encrypts everything",
               "Yes, if the chat is private",
               "Only for Bearer tokens"),
              "No. HTTPS protects requests in transit, not copies of the key elsewhere",
              "Once copied elsewhere the key is outside TLS's protection. Revoke it.", "transport"),
    ),
    citations=(
        Citation("mdn-status", "401 means unauthenticated; 403 means known identity without access rights."),
        Citation("mdn-auth", "The Authorization header format; Basic credentials are insecure without HTTPS."),
        Citation("claude-api-overview", "Authorization: Bearer or x-api-key; required anthropic-version header."),
        Citation("claude-errors", "401 authentication_error and 403 permission_error."),
        Citation("owasp-secrets", "Avoid hard-coding secrets; least privilege; regular rotation."),
        Citation("py-os-environ", "os.environ and os.getenv read environment variables."),
        Citation("app-config", "api_key_present() reports only whether a key exists."),
        Citation("app-provider", "Requests are built without credentials; 401 becomes a readable message."),
    ),
    prerequisites=("http-request-flow",),
    related=("latency-cost-reliability",),
    scope="Status semantics are general HTTP. Header names, error type names and key management features "
          "are Anthropic-specific.",
)

LESSONS = (PYTHON_DATA_SHAPES, JSON_BASICS, HTTP_REQUEST_FLOW, API_KEYS_AUTH)
