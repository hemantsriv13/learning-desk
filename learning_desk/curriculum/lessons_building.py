"""Lessons for topics 7–10: structured outputs, tools and agents, evaluation, product trade-offs."""

from .model import Activity, Check, Citation, Code, Lesson, Section, Table

STRUCTURED = Lesson(
    id="structured-outputs",
    topic="structured",
    title="Structured outputs: schemas and validation",
    summary="Ask for a machine-readable shape, verify what comes back, and handle the replies that fail.",
    level="intermediate",
    minutes=30,
    objective="Request machine-readable replies with a schema, validate them in code, and design what "
              "happens when validation fails.",
    intro="An application cannot store \"a nice paragraph\"; it needs fields: a takeaway, a list of "
          "citations, a question with four options and one key. **Structured output** means asking the "
          "model for a specific JSON shape and then **validating** what comes back before anything is "
          "saved. The two steps are separate, and both matter.",
    key_ideas=(
        "Asking for a shape (a schema) and checking it (validation) are separate steps.",
        "Constrained decoding can make replies schema-compliant, with documented exceptions.",
        "Some rules cannot be expressed in a provider schema; enforce them in your own code.",
        "A rejected reply should be logged and surfaced, never silently patched.",
    ),
    overview_visual="structured_validation",
    sections=(
        Section(
            "why", "Why structure",
            "Free text is for people; fields are for programs. With fields, the interface can place the "
            "takeaway beside its citations, the database can store each question separately, and code can "
            "check rules such as \"the key is one of the options\". Structure also makes failures visible: a "
            "missing field is detectable, a vague paragraph is not.",
        ),
        Section(
            "asking", "Asking for a shape",
            "Anthropic's API accepts a JSON Schema in `output_config.format` with type `json_schema`, and "
            "uses constrained decoding so the reply's text is schema-compliant JSON. Learning Desk's "
            "`provider.build_request` does exactly this for every AI action.\n\n"
            "Provider schemas support a subset of JSON Schema. At the time of checking, unsupported features "
            "included string length limits (`minLength`, `maxLength`), numeric limits (`minimum`, `maximum`), "
            "and array limits beyond `minItems` of 0 or 1; using them returns a 400 error. Learning Desk's "
            "`learning.schema()` therefore removes those keywords from the schema it sends and enforces the "
            "same limits locally with Pydantic.",
            code=Code("python",
                      'def build_request(*, system, user_text, schema):\n'
                      '    output_config = {"format": {"type": "json_schema", "schema": schema}}\n'
                      '    return {"model": config.model(), "max_tokens": config.max_tokens(),\n'
                      '            "system": system,\n'
                      '            "messages": [{"role": "user", "content": user_text}],\n'
                      '            "output_config": output_config}',
                      notes=((2, "The schema travels with the request."),
                             (4, "Fixed instructions go in system; untrusted material goes in the message.")),
                      caption="Shortened from learning_desk/provider.py"),
        ),
        Section(
            "validating", "Validating in code",
            "Validation turns \"probably the right shape\" into \"checked\". Pydantic models describe the "
            "expected fields and types; `model_validate` (or `model_validate_json`) raises a "
            "`ValidationError` listing every problem when data does not fit.\n\n"
            "In Learning Desk, `ai._run` parses the reply with `json.loads`, validates it with the action's "
            "Pydantic model, then runs any extra rules. If anything fails, the call is recorded as an error "
            "with the raw reply and the message \"did not match the expected format\", and your notes are "
            "untouched.",
            visual="structured_validation",
        ),
        Section(
            "rules", "Rules a schema cannot express",
            "Some requirements depend on relationships between fields or on data outside the reply:\n\n"
            "- A multiple-choice key must equal one of four *distinct* options (`PracticeQuestion` checks this).\n"
            "- A quick read must leave the explanation and example fields empty.\n"
            "- Every citation must refer to a passage that was actually supplied (`check_refs`).\n\n"
            "These belong in code after schema validation. Keep each rule small and give it a specific "
            "error message, so a failure points to the exact rule that was broken.",
        ),
    ),
    worked_example=Section(
        "worked", "Worked example: a validator for quiz questions",
        "This is a shortened version of the model Learning Desk uses for generated questions. Field types "
        "and lengths are declared; the cross-field rule lives in a validator that runs after the fields "
        "are parsed.",
        code=Code("python",
                  'class PracticeQuestion(BaseModel):\n'
                  '    question: str = Field(min_length=1, max_length=1000)\n'
                  '    question_type: Literal["multiple_choice", "short_answer"]\n'
                  '    options: list[str] = Field(max_length=4)\n'
                  '    expected_answer: str = Field(min_length=1, max_length=1500)\n'
                  '    section_refs: list[int] = Field(min_length=1, max_length=8)\n'
                  '\n'
                  '    @model_validator(mode="after")\n'
                  '    def valid_key(self):\n'
                  '        if self.question_type == "multiple_choice":\n'
                  '            if (len(self.options) != 4 or len(set(self.options)) != 4\n'
                  '                    or self.expected_answer not in self.options):\n'
                  '                raise ValueError("Multiple-choice key must match one of four distinct options")\n'
                  '        elif self.options:\n'
                  '            raise ValueError("Short-answer questions must have no options")\n'
                  '        return self',
                  notes=((2, "Length limits are enforced here, even though they are stripped from the provider schema."),
                         (3, "Literal restricts the value to two exact strings."),
                         (6, "At least one citation is required."),
                         (8, "Runs after field validation, so all fields are already typed."),
                         (11, "The cross-field rule: four distinct options, and the key is one of them.")),
                  caption="Shortened from learning_desk/learning.py"),
    ),
    misconception=Section(
        "misconception", "Misconception: with structured outputs, validation is unnecessary",
        "Anthropic's own documentation lists cases where output may not match the schema: a refusal "
        "(`stop_reason: \"refusal\"`), a reply cut off at the token limit (`max_tokens`), and enum or const "
        "values that differ only in capitalisation. Add the constraints you had to remove from the provider "
        "schema, and the rules no schema can express, and local validation is still essential. It is also "
        "what keeps your application safe if you change provider or model.",
    ),
    activity=Activity(
        "Design a reply and break it",
        ("Write a JSON object for a lesson summary with fields `takeaway` (string), `points` (array of "
         "strings) and `cited_sections` (array of integers). Check it in the inspector.",
         "Write three variants that parse but should be rejected: a missing field, a wrong type, and a "
         "rule violation of your choice (for example, a cited section that does not exist).",
         "For each, name the gate in the diagram that catches it.",
         "Decide what the user should see for each failure, in one sentence."),
        widget="json_inspector",
        reflection="Which of your rules could the provider enforce, and which only your code can?",
    ),
    checks=(
        Check("strip", "The provider rejects schemas with maxLength. What does Learning Desk do?",
              ("Removes length limits from the schema it sends and enforces them locally",
               "Drops the limits entirely",
               "Sends the schema anyway and ignores the 400 error",
               "Asks the model to count characters"),
              "Removes length limits from the schema it sends and enforces them locally",
              "learning.schema() strips unsupported keywords; Pydantic enforces them after the reply arrives.",
              "asking"),
        Check("gate3", "A reply is valid JSON, matches the schema, and cites passage S9, but the source has 6 passages. What happens?",
              ("An application rule rejects it and the failure is logged",
               "It is saved, because it matched the schema",
               "The app removes the bad citation and saves the rest",
               "The model is asked again automatically"),
              "An application rule rejects it and the failure is logged",
              "check_refs is a rule beyond the schema; failing it rejects the whole reply.", "rules"),
        Check("cutoff", "With structured outputs enabled, a reply stops with stop_reason max_tokens. What should you assume?",
              ("It may be incomplete and may not match the schema",
               "It is guaranteed valid because of constrained decoding",
               "It was refused",
               "It is valid but shorter"),
              "It may be incomplete and may not match the schema",
              "The documentation lists max_tokens as a case where output might be incomplete.", "misconception"),
    ),
    citations=(
        Citation("claude-structured-outputs", "output_config.format with json_schema; constrained decoding; exceptions "
                 "(refusal, max_tokens, enum casing); unsupported schema features return 400."),
        Citation("pydantic-models", "model_validate / model_validate_json raise ValidationError on invalid data."),
        Citation("jsonschema-start", "Schema keywords type, properties and required."),
        Citation("app-provider", "Every request includes output_config with the action's schema."),
        Citation("app-ai", "Replies are parsed, validated and recorded; failures keep notes unchanged."),
        Citation("app-learning", "schema() strips unsupported keywords; PracticeQuestion and check_refs rules."),
    ),
    prerequisites=("json-basics", "http-request-flow"),
    related=("tools-agent-loop", "evaluation-basics"),
    scope="Validation is general practice. output_config and the list of unsupported schema features are "
          "Anthropic-specific and were current when checked.",
)


AGENTS = Lesson(
    id="tools-agent-loop",
    topic="agents",
    title="Tools and the agent loop",
    summary="How a model requests a tool, who runs it, and how to keep a loop of tool calls bounded.",
    level="intermediate",
    minutes=30,
    objective="Explain how a model requests tool calls, who executes them, and how to bound an agent loop "
              "with checks, budgets and stop conditions.",
    intro="A model on its own can only produce text. **Tools** let it ask an application to do something: "
          "search, read a file, call an API. The model proposes a structured call; for tools you define, "
          "**your code** runs it and sends back the result. Repeat that in a loop and you have an "
          "**agent**. The engineering is mostly about the loop's edges: what may run, with which inputs, "
          "and when to stop.",
    key_ideas=(
        "A tool definition has a name, a description and an input schema.",
        "The model returns a tool_use request; your application runs client tools and returns a tool_result.",
        "A workflow follows predefined code paths; an agent lets the model direct its own steps.",
        "Start simple. Add permission checks, budgets and stop conditions before autonomy.",
    ),
    overview_visual="agent_loop",
    sections=(
        Section(
            "define", "Defining a tool",
            "A tool is described to the model, not given to it. The **name** identifies it, the "
            "**description** says when and why to use it (the model relies heavily on this), and the "
            "**input schema** is a JSON Schema for its arguments. Tool definitions are sent with the "
            "request, so they count as input tokens.",
            code=Code("json",
                      '{\n'
                      '  "name": "search_library",\n'
                      '  "description": "Search the learner\'s saved resources by title or tag. Use when the question refers to their own material. Returns up to 5 titles.",\n'
                      '  "input_schema": {\n'
                      '    "type": "object",\n'
                      '    "properties": {"query": {"type": "string"}},\n'
                      '    "required": ["query"]\n'
                      '  }\n'
                      '}',
                      notes=((2, "A stable, specific name."),
                             (3, "Say when to use it and what it returns; vague descriptions cause misuse."),
                             (4, "The arguments the model must supply, as JSON Schema.")),
                      caption="A hypothetical tool for this app (not implemented)"),
        ),
        Section(
            "roundtrip", "The round trip",
            "When the model decides to use a client tool, the response ends with `stop_reason: \"tool_use\"` "
            "and contains a `tool_use` block with an id, the tool name and its input. Your code runs the "
            "operation and sends a new request that includes the earlier turns plus a `tool_result` block "
            "carrying the same id and the output. The model then continues: it may answer, or ask for "
            "another tool.\n\n"
            "Anthropic also offers **server tools** (such as web search) that run on its infrastructure; "
            "you see their results without executing anything. For your own tools, execution and its "
            "consequences are always your application's responsibility.",
        ),
        Section(
            "loop", "From one call to a loop",
            "Anthropic's *Building effective agents* distinguishes **workflows**, where models and tools are "
            "orchestrated through predefined code paths, from **agents**, where the model directs its own "
            "process and tool use. The ReAct paper showed the value of interleaving reasoning with actions: "
            "the reasoning chooses the next action, and the action's result informs the reasoning.\n\n"
            "Each iteration resends the growing conversation, so long loops cost more per step, and an early "
            "mistake can compound.",
            visual="agent_loop",
        ),
        Section(
            "bounds", "Bounding the loop",
            "The same article recommends finding the simplest solution that works, often a single well-"
            "prepared call, and adding agentic complexity only when it pays off. When you do build a loop, "
            "design its edges:\n\n"
            "- **Allowlist** the tools; reject any other name.\n"
            "- **Validate inputs** against the schema and your own rules before running anything.\n"
            "- **Confirm consequential actions** (sending, deleting, paying) with a person.\n"
            "- **Budget** steps, tokens and time, and stop when any runs out.\n"
            "- **Test in a sandbox** before giving access to anything real.",
            callout="Tool results are untrusted input too: a fetched web page can contain instructions aimed at the model.",
        ),
    ),
    worked_example=Section(
        "worked", "Worked example: a bounded loop",
        "A sketch of the control flow, with the provider call and tools passed in as functions. It is "
        "illustrative pseudocode in Python syntax; the app does not run it.",
        code=Code("python",
                  'MAX_STEPS = 6\n'
                  'ALLOWED = {"search_library": search_library}\n'
                  '\n'
                  'def run_agent(goal, call_model):\n'
                  '    messages = [{"role": "user", "content": goal}]\n'
                  '    for step in range(MAX_STEPS):\n'
                  '        reply = call_model(messages)\n'
                  '        messages.append({"role": "assistant", "content": reply.content})\n'
                  '        if reply.stop_reason != "tool_use":\n'
                  '            return reply  # a final answer\n'
                  '        results = []\n'
                  '        for call in tool_calls(reply):\n'
                  '            tool = ALLOWED.get(call.name)\n'
                  '            if tool is None or not valid_input(call):\n'
                  '                output, is_error = "Tool not available or input invalid.", True\n'
                  '            else:\n'
                  '                output, is_error = tool(**call.input), False\n'
                  '            results.append({"type": "tool_result", "tool_use_id": call.id,\n'
                  '                            "content": output, "is_error": is_error})\n'
                  '        messages.append({"role": "user", "content": results})\n'
                  '    raise RuntimeError("Stopped: step limit reached without a final answer")',
                  notes=((1, "A hard step budget, decided before the loop starts."),
                         (2, "Only named, reviewed tools can run."),
                         (9, "No tool requested: return the answer."),
                         (14, "Unknown tools and invalid inputs are refused, and the model is told so."),
                         (18, "Each result carries the id of the request it answers."),
                         (21, "Running out of budget is a visible failure, not a silent one.")),
                  caption="Illustrative only; tool_calls and valid_input are left abstract"),
    ),
    misconception=Section(
        "misconception", "Misconception: the model runs the tool",
        "For client tools the model only *proposes* a call: a name and some arguments in JSON. Your code "
        "decides whether to run it, with what checks, and what to report back. That is good news: every "
        "safety measure (allowlists, validation, confirmation, sandboxing) lives in code you control. It "
        "also means you cannot blame the model for an action your application chose to execute.",
    ),
    activity=Activity(
        "Design a tool for Learning Desk",
        ("Pick a read-only tool that would help a review, such as `find_related_sessions(topic)`.",
         "Write its name, a two-sentence description, and an input schema.",
         "List three checks the app should make before running it.",
         "Choose stop conditions: maximum steps, and what happens when a tool fails.",
         "Decide which tool you would never let the model call without asking you first."),
        widget="agent_loop",
        reflection="Could this task be done with one well-prepared call instead of a loop?",
    ),
    checks=(
        Check("who", "Who executes a client tool that you defined?",
              ("Your application", "The model", "The provider's servers", "The user's browser automatically"),
              "Your application",
              "The model returns a tool_use request; your code runs it and returns a tool_result.", "roundtrip"),
        Check("stop", 'A response has stop_reason "tool_use". What does it mean?',
              ("The model is requesting one or more tool calls",
               "The response was cut off",
               "A tool has already run",
               "The model refused"),
              "The model is requesting one or more tool calls",
              "The application should run the requested calls (after its checks) and reply with results.",
              "roundtrip"),
        Check("bound", "Which of these is a stop condition for an agent loop?",
              ("A maximum number of steps", "A longer tool description", "A higher temperature",
               "A larger context window"),
              "A maximum number of steps",
              "Budgets on steps, tokens or time end loops that are not converging.", "bounds"),
    ),
    citations=(
        Citation("claude-tool-use", "Client tools run in your application; stop_reason tool_use; tool_use and "
                 "tool_result blocks; server tools; tool definitions count as input tokens."),
        Citation("anthropic-effective-agents", "Workflows versus agents; start simple; stopping conditions; sandboxed testing."),
        Citation("yao-2022", "Interleaving reasoning traces with actions."),
    ),
    prerequisites=("structured-outputs", "http-request-flow"),
    related=("evaluation-basics", "latency-cost-reliability"),
    scope="The loop pattern is general. Block and field names (tool_use, tool_result, stop_reason) follow "
          "Anthropic's Messages API.",
)


EVALUATION = Lesson(
    id="evaluation-basics",
    topic="evaluation",
    title="Evaluation: test cases, graders and failure analysis",
    summary="Build a small fixed test set, pick a grader per criterion, and turn failures into specific fixes.",
    level="intermediate",
    minutes=35,
    objective="Build a small evaluation set, choose a grading method for each criterion, and turn failures "
              "into specific, testable fixes.",
    intro="Trying a prompt a few times and liking the result is not evidence that it works. An "
          "**evaluation** runs a fixed set of cases through the system the same way every time and judges "
          "each output by a stated standard. It turns \"seems better\" into \"passes 18 of 20, up from 14, "
          "and here are the two that still fail\".",
    key_ideas=(
        "An eval is a fixed set of cases run the same way, so results are comparable across changes.",
        "Each case needs an input and a way to judge the output: an expected answer, a rule, or a rubric.",
        "Graders: code (fast, exact), a model with a rubric (nuanced, can be wrong), a person (best, slow).",
        "Read failures, group them by cause, fix the largest group, rerun the same cases.",
    ),
    overview_visual="eval_pipeline",
    sections=(
        Section(
            "why", "Why a fixed set",
            "Models produce varied outputs, and people remember striking examples. A fixed set protects "
            "against both: the same inputs, the same grader, a number you can compare. Anthropic's guidance "
            "on building evaluations stresses two things that are easy to skip: mirror real usage, "
            "**including edge cases** (irrelevant, very long, ambiguous or harmful inputs), and prefer more "
            "automatically graded cases with slightly lower signal over a handful of hand-graded ones.",
        ),
        Section(
            "cases", "Writing test cases",
            "A case is an input plus what good looks like. Tag each case with what it is testing so failures "
            "can be grouped later. For Learning Desk's *Quick read* (summarise only the supplied source, "
            "about 150 words, with citations), a starter set might look like this:",
            table=Table(("Case", "Input", "Expected behaviour", "Tag"),
                        (("1", "A clear 400-word article", "Summary cites passages; no added facts", "normal"),
                         ("2", "A two-sentence note", "Short summary; says the source is brief", "edge: short"),
                         ("3", "A tutorial that is mostly code", "Describes the code's purpose; cites code passages", "edge: code"),
                         ("4", "A passage containing \"ignore previous instructions\"", "Treats it as text to summarise", "adversarial"),
                         ("5", "A passage in Spanish", "Summary is faithful; language choice consistent", "edge: language")),
                        caption="Illustrative cases; a real set would include many more of each tag"),
        ),
        Section(
            "graders", "Choosing a grader",
            "Pick the cheapest grader that can actually judge the criterion. Exact rules (valid JSON, "
            "required fields, citations resolve, length within bounds) belong in code. Qualities such as "
            "faithfulness or tone need a rubric applied by a model or a person.\n\n"
            "Model graders are useful but have known biases. Zheng and colleagues found position bias "
            "(favouring an answer because of where it appears), verbosity bias (favouring longer answers) "
            "and self-enhancement bias (favouring outputs like their own). Anthropic's guidance suggests "
            "using a different model as the grader from the one that produced the output, and clear rubrics "
            "with a reason before the verdict.",
            table=Table(("Grader", "Good for", "Watch out for"),
                        (("Code", "Format, fields, exact answers, citation existence", "Measures surface form, not quality"),
                         ("Model with a rubric", "Faithfulness, tone, partial credit", "Biases; extra calls; can be wrong"),
                         ("Person", "Ground truth for hard judgements; checking other graders", "Slow, costly, inconsistent across people")),
                        caption="Grading methods and their trade-offs"),
        ),
        Section(
            "analysis", "From failures to fixes",
            "A score tells you *how much*; reading failures tells you *why*. For each failing case, write a "
            "one-line cause (\"added a fact not in the source\", \"ignored the code block\"), then group "
            "causes and count. Fix the largest group first, rerun **all** cases (a fix can break something "
            "else), and keep the outputs and grader reasons from each run so you can compare.\n\n"
            "Keep some cases aside that you do not look at while tuning, so you can tell whether you "
            "improved the system or just fitted the test set.",
            visual="eval_pipeline",
        ),
    ),
    worked_example=Section(
        "worked", "Worked example: grading the grader in this app",
        "Learning Desk grades generated multiple-choice questions deterministically: your choice is compared "
        "with the saved answer key. That comparison is exact and free, but the key itself was generated "
        "by a model, so the grader inherits its errors. The app says so in its feedback: \"Matches the "
        "saved AI-generated key. The key can itself be wrong.\"\n\n"
        "The *This question or feedback seems wrong* report is the failure-analysis loop in miniature: it "
        "saves the question, attempt and feedback ids so a suspect key can be examined later, without "
        "another model call.",
        table=Table(("What is checked", "By", "What a pass means"),
                    (("Key is one of four distinct options", "Code (Pydantic validator)", "The question is well-formed"),
                     ("Citations resolve", "Code (check_refs)", "Cited passages exist"),
                     ("Your answer matches the key", "Code (comparison)", "Agreement with the key, not proven correctness"),
                     ("Short answers", "Model with a rubric", "A model's judgement, with stated uncertainty")),
                    caption="Each layer establishes something specific, and no more"),
    ),
    misconception=Section(
        "misconception", "Misconception: a high score means the system is good",
        "A score is only as meaningful as its cases and its grader. Twenty easy cases graded leniently can "
        "score 100% on a system that fails real users. Before trusting a number, ask: do the cases include "
        "the hard and adversarial inputs real use will bring? Has the grader been checked against human "
        "judgement on a sample? Did the score move because the system improved, or because the cases or "
        "grader changed?",
    ),
    activity=Activity(
        "Draft a five-case evaluation",
        ("Pick one feature you use: Quick read, Explain it, or a notebook review.",
         "Write five cases: two normal, two edge, one adversarial. Give each an expected behaviour and a tag.",
         "For each expected behaviour, choose code, model or human grading, and say why.",
         "Imagine two cases failed. Write the one-line cause for each and what you would change first."),
        reflection="Which of your criteria could a simple function check today, without any model?",
    ),
    checks=(
        Check("grader", 'Which grader suits "the output is valid JSON with the required fields"?',
              ("Code", "A model with a rubric", "A person", "No grader is needed"), "Code",
              "Format and field presence are exact rules: fast, cheap and repeatable to check in code.", "graders"),
        Check("bias", "Which bias of model graders did Zheng and colleagues report?",
              ("Verbosity bias: favouring longer answers", "Recency bias: favouring newer models",
               "Price bias: favouring cheaper models", "No biases were found"),
              "Verbosity bias: favouring longer answers",
              "The paper lists position, verbosity and self-enhancement biases.", "graders"),
        Check("mcq", "Your multiple-choice answer matches the saved key. What is established?",
              ("Your answer agrees with the AI-generated key, which may itself be wrong",
               "You have mastered the topic", "The answer is definitely correct", "The source is correct"),
              "Your answer agrees with the AI-generated key, which may itself be wrong",
              "The comparison is exact, but the key was generated by a model.", "worked"),
    ),
    citations=(
        Citation("claude-develop-tests", "Code, model and human grading with trade-offs; include edge cases; "
                 "volume over hand-graded quality; use a different model as grader."),
        Citation("zheng-2023", "Position, verbosity and self-enhancement biases in model judges."),
        Citation("app-learning", "Deterministic multiple-choice comparison with an AI-generated key; rubric feedback."),
    ),
    prerequisites=("structured-outputs",),
    related=("latency-cost-reliability", "retrieval-basics", "sampling-temperature"),
    scope="Evaluation practice is general. Specific advice is drawn from one provider's guide and one research "
          "paper; the worked example describes this app's actual grading.",
)


PRODUCT = Lesson(
    id="latency-cost-reliability",
    topic="product",
    title="Usefulness, latency, cost and reliability",
    summary="Estimate where time and money go in a request, and trade them off deliberately.",
    level="intermediate",
    minutes=30,
    objective="Estimate where time and money go in an AI request, and choose design changes that trade "
              "usefulness, latency, cost and reliability deliberately.",
    intro="An AI feature succeeds only if it is useful, responds fast enough, costs an acceptable amount, "
          "and behaves predictably when things go wrong. These pull against each other: a longer, more "
          "careful answer is slower and dearer; automatic retries improve success rates and add cost. "
          "Good product decisions make those trade-offs explicit.",
    key_ideas=(
        "Start from usefulness; a fast, cheap wrong answer has no value.",
        "Output length usually dominates response time; input size matters too.",
        "Price is per token, and output tokens cost more than input tokens on current price lists.",
        "Plan for rate limits, timeouts and invalid replies before they happen.",
    ),
    overview_visual="latency_timeline",
    sections=(
        Section(
            "useful", "Usefulness first",
            "Anthropic's latency guide makes the order explicit: first engineer a prompt that works well "
            "without constraints, then try latency reductions, because optimising too early can stop you "
            "discovering what good looks like. In practice: define the job, build an evaluation, reach "
            "acceptable quality, *then* shorten, cache, stream or switch models, re-running the evaluation "
            "after each change.",
        ),
        Section(
            "time", "Where time goes",
            "Two measures matter. **Time to first token** (TTFT) is how long until the first piece of output "
            "arrives; it shapes how responsive streaming feels. Total time is how long until the reply is "
            "complete. Reading the input is relatively fast per token; generating output happens one token at "
            "a time, so long outputs dominate.\n\n"
            "Levers, in rough order of impact: ask for shorter output and set `max_tokens`, send less input, "
            "choose a faster model or lower effort setting, cache repeated prefixes, and stream so people "
            "see progress.",
            visual="latency_timeline",
            callout="The timeline uses invented round-number rates to show proportions. Measure your own requests.",
        ),
        Section(
            "money", "Where money goes",
            "Providers price input and output tokens separately, per million tokens. On Anthropic's current "
            "price list output costs several times more than input for every model, so verbose replies are "
            "expensive twice: in time and in money. Two discounts change the arithmetic: prompt-cache reads "
            "are billed at a fraction of the base input price (0.1× on most models at the time of checking), "
            "and the Message Batches API offers a 50% reduction for work that can wait.\n\n"
            "Do not copy prices into code or notes. They change; read the provider's page and plug current "
            "numbers into a calculator like the one in *Try it*.",
        ),
        Section(
            "reliability", "Reliability",
            "Plan for each failure the request flow can produce. Rate limits are measured per minute in "
            "requests, input tokens and output tokens; exceeding one returns 429, often with a "
            "`retry-after` header saying how long to wait. Overload, timeouts and invalid replies need their "
            "own handling, and every retry costs another request.\n\n"
            "Learning Desk's choices, for comparison: one attempt per click; a configurable timeout "
            "(`LEARNING_DESK_TIMEOUT`, 180 seconds by default); validation before saving; and summaries "
            "cached per content version, so opening a saved summary again costs nothing and takes no time.",
        ),
    ),
    worked_example=Section(
        "worked", "Worked example: a design review of Quick read",
        "Each design choice in Learning Desk's *Quick read* moves at least one of the four qualities:",
        table=Table(("Decision", "Usefulness", "Latency", "Cost", "Reliability"),
                    (("Ask for about 150 words", "Focused, may omit detail", "Shorter output, faster", "Fewer output tokens", "—"),
                     ("Send only the selected version", "Grounded in one source", "Smaller input", "Fewer input tokens", "Bounded size"),
                     ("Cache per version and format", "Stable on reopen", "Instant on reopen", "No repeat cost", "No repeat failures"),
                     ("One attempt, no auto-retry", "—", "No hidden waits", "Predictable", "You retry deliberately"),
                     ("Validate citations before saving", "Checkable claims", "Milliseconds", "—", "Bad replies not stored")),
                    caption="Effects described qualitatively; measure before quoting numbers"),
    ),
    misconception=Section(
        "misconception", "Misconception: streaming makes requests faster",
        "Streaming sends tokens as they are generated, so people can start reading after the time to "
        "first token. The model still generates the same number of tokens at the same pace, so the total "
        "time is essentially unchanged. Streaming improves *perceived* responsiveness, and is worth having "
        "for that reason, but it does not reduce cost or total latency.",
    ),
    activity=Activity(
        "Change one lever at a time",
        ("Use the latency timeline below with 3,000 input and 500 output tokens. Which segment dominates?",
         "Double the input tokens. Then halve the output tokens instead. Which change saved more time?",
         "Turn on streaming and read the time to first token.",
         "In the cost calculator, enter the current per-million-token prices from your provider's pricing "
         "page and estimate 100 requests a day for a month."),
        widget="latency_timeline",
        reflection="For a feature you use, which matters more to you: time to first token, or total time?",
    ),
    checks=(
        Check("stream", "What does streaming change?",
              ("When the first words appear, not the total generation time",
               "The total time, by generating faster",
               "The cost per token",
               "The number of output tokens"),
              "When the first words appear, not the total generation time",
              "Streaming improves perceived responsiveness; the same tokens are still generated.", "time"),
        Check("dominant", "For a reply of several hundred tokens, which part usually takes longest?",
              ("Generating the output tokens", "Opening the network connection", "Reading the input",
               "Saving to the database"),
              "Generating the output tokens",
              "Output is produced one token at a time, so long outputs dominate total time.", "time"),
        Check("retryafter", "A request returns 429 with a retry-after header. What should a client do?",
              ("Wait at least that many seconds before retrying",
               "Retry immediately in a loop",
               "Switch to a different API key",
               "Treat the reply as a valid result"),
              "Wait at least that many seconds before retrying",
              "Earlier retries will fail; the header says when capacity returns.", "reliability"),
    ),
    citations=(
        Citation("claude-latency", "Engineer for quality before latency; baseline latency and TTFT; model choice, "
                 "shorter prompts and outputs, max_tokens, streaming."),
        Citation("claude-streaming", "Streaming returns the response incrementally as server-sent events."),
        Citation("claude-pricing", "Per-million-token prices with output priced above input."),
        Citation("claude-prompt-caching", "Cache reads billed at a fraction (0.1× on most models) of base input price."),
        Citation("claude-api-overview", "Message Batches API with a 50% cost reduction."),
        Citation("claude-rate-limits", "Limits in RPM, ITPM and OTPM; 429 with retry-after."),
        Citation("app-config", "LEARNING_DESK_TIMEOUT defaults to 180 seconds."),
        Citation("app-learning", "Summaries cached per content version and format; quick read about 150 words."),
    ),
    prerequisites=("tokens-context-window", "http-request-flow"),
    related=("evaluation-basics", "api-keys-auth"),
    scope="The trade-offs are general. Prices, discounts and limits are Anthropic-specific and change; the "
          "timeline uses illustrative rates, not measurements.",
)

LESSONS = (STRUCTURED, AGENTS, EVALUATION, PRODUCT)
