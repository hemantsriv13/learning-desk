"""Interactive lesson examples. All computation is local and deterministic; none calls a model, and
none executes anything the learner types (the JSON inspector only parses)."""

import json
import random

import altair as alt
import streamlit as st

from .. import visuals
from .theme import figure

JSON_LIMIT = 20_000


def render(visual_id: str, key: str) -> None:
    """Show a lesson visual. Interactive ones get controls; static ones render as a figure."""
    handler = {
        "sampling": sampling, "context_budget": context_budget, "embedding_map": embedding_map,
        "attention_heatmap": attention, "latency_timeline": latency, "json_inspector": json_inspector,
        "cost_calculator": cost_calculator,
    }.get(visual_id)
    if handler:
        handler(key)
    else:
        figure(visual_id, key=key)


def sampling(key: str) -> None:
    visual = visuals.VISUALS["sampling"]
    st.markdown(f"**{visual.title}**")
    st.caption(f"Prompt: “{visuals.NEXT_TOKEN_PROMPT} …”. :material/info: {visual.illustrative}")
    c1, c2, c3 = st.columns(3)
    temperature = c1.slider("Temperature", 0.0, 2.5, 1.0, 0.1, key=f"{key}_t",
                            help="0 means always take the most likely token (greedy).")
    top_k = c2.slider("Top-k (0 = off)", 0, len(visuals.NEXT_TOKEN_LOGITS), 0, 1, key=f"{key}_k")
    top_p = c3.slider("Top-p (1.0 = off)", 0.05, 1.0, 1.0, 0.05, key=f"{key}_p")
    labels = [t for t, _ in visuals.NEXT_TOKEN_LOGITS]
    probs = visuals.sampling_distribution([s for _, s in visuals.NEXT_TOKEN_LOGITS], temperature, top_k, top_p)
    rows = [{"Candidate": t, "Probability": p, "Shown": visuals.pct(p) if p else "removed", "Order": i}
            for i, (t, p) in enumerate(zip(labels, probs))]
    chart = (alt.Chart(alt.Data(values=rows))
             .mark_bar(cornerRadiusEnd=4)
             .encode(y=alt.Y("Candidate:N", sort=alt.SortField("Order"), title=None),
                     x=alt.X("Probability:Q", axis=alt.Axis(format="%"), scale=alt.Scale(domain=[0, 1]), title="Probability"),
                     color=alt.condition("datum.Probability > 0", alt.value("#3ddc97"), alt.value("#4a4a4a")),
                     tooltip=["Candidate:N", "Shown:N"])
             .properties(height=280))
    text = " ".join(f"{r['Candidate']} {r['Shown']}." for r in rows)
    st.altair_chart(chart, use_container_width=True,
                    alt=f"Bar chart of next-word probabilities at temperature {temperature}, top-k {top_k or 'off'}, "
                        f"top-p {top_p}: {text}")
    kept = sum(1 for p in probs if p > 0)
    st.caption(f":material/visibility: **What to notice:** {kept} of {len(labels)} candidates can be chosen. "
               f"{visual.notice}")
    draws = st.session_state.get(f"{key}_draws", 0)
    if st.button("Draw 20 samples", key=f"{key}_draw", icon=":material/casino:"):
        st.session_state[f"{key}_draws"] = draws = draws + 1
    if draws:
        rng = random.Random(draws)  # reproducible for the same click count and settings
        picks = rng.choices(labels, weights=probs, k=20)
        counts = {t: picks.count(t) for t in labels if picks.count(t)}
        st.write("Sampled: " + ", ".join(f"**{t}** ×{n}" for t, n in sorted(counts.items(), key=lambda x: -x[1])))
        st.caption("Each draw picks one word using the probabilities above. Draw again to see variation.")
    with st.expander("Probabilities as a table"):
        st.table({"Candidate": labels, "Probability": [r["Shown"] for r in rows]})


def context_budget(key: str) -> None:
    c1, c2 = st.columns(2)
    window = c1.select_slider("Context window (tokens)", [8_000, 16_000, 32_000, 64_000, 128_000],
                              value=16_000, key=f"{key}_w")
    system = c2.slider("System instructions", 0, 8_000, 1_200, 100, key=f"{key}_s")
    exchanges = c1.slider("Earlier exchanges (≈800 tokens each)", 0, 80, 8, 1, key=f"{key}_h")
    message = c2.slider("New message", 0, 8_000, 400, 100, key=f"{key}_m")
    output = c1.slider("Output budget (max_tokens)", 0, 16_000, 1_500, 100, key=f"{key}_o")
    figure("context_budget", visuals.tokens_context(system, exchanges * 800, message, output, window), key=key)


def embedding_map(key: str) -> None:
    query = st.selectbox("Query phrase", list(visuals.EMBEDDING_POINTS), index=2, key=f"{key}_q")
    figure("embedding_map", visuals.embedding_map(query), key=key)
    ranked = visuals.rank_by_similarity(visuals.EMBEDDING_POINTS[query],
                                        {k: v for k, v in visuals.EMBEDDING_POINTS.items() if k != query})
    st.table({"Phrase": [label for label, _ in ranked],
              "Cosine similarity to the query": [f"{sim:.3f}" for _, sim in ranked]})


def attention(key: str) -> None:
    token = st.selectbox("Row to highlight (the token being updated)", visuals.ATTENTION_TOKENS,
                         index=visuals.ATTENTION_TOKENS.index("it"), key=f"{key}_row")
    figure("attention_heatmap", visuals.attention_heatmap(token), key=key)
    row = visuals.attention_weights()[visuals.ATTENTION_TOKENS.index(token)]
    visible = [(t, w) for t, w in zip(visuals.ATTENTION_TOKENS, row) if w > 0]
    st.table({"Looks at": [t for t, _ in visible], "Weight": [f"{w:.2f}" for _, w in visible]})
    st.caption(f"The weights for “{token}” sum to {sum(row):.2f}.")


def latency(key: str) -> None:
    c1, c2, c3 = st.columns([2, 2, 1.4])
    input_tokens = c1.slider("Input tokens", 100, 50_000, 3_000, 100, key=f"{key}_in")
    output_tokens = c2.slider("Output tokens", 10, 4_000, 500, 10, key=f"{key}_out")
    streaming = c3.toggle("Streaming", key=f"{key}_stream")
    figure("latency_timeline", visuals.latency_timeline(input_tokens, output_tokens, streaming), key=key)
    st.divider()
    cost_calculator(f"{key}_cost", input_tokens, output_tokens)


def cost_calculator(key: str, input_tokens: int = 3_000, output_tokens: int = 500) -> None:
    visual = visuals.VISUALS["cost_calculator"]
    st.markdown(f"**{visual.title}**")
    st.caption(f":material/info: {visual.illustrative}")
    c1, c2, c3 = st.columns(3)
    price_in = c1.number_input("Input price per million tokens", 0.0, 1000.0, 1.0, 0.1, key=f"{key}_pin")
    price_out = c2.number_input("Output price per million tokens", 0.0, 1000.0, 5.0, 0.1, key=f"{key}_pout")
    per_day = c3.number_input("Requests per day", 0, 1_000_000, 100, 10, key=f"{key}_n")
    one = visuals.request_cost(input_tokens, output_tokens, price_in, price_out)
    st.write(f"One request ({input_tokens:,} in, {output_tokens:,} out): **{one:.4f}** in your currency. "
             f"30 days at {per_day:,} a day: **{one * per_day * 30:,.2f}**.")
    share = (output_tokens * price_out) / (input_tokens * price_in + output_tokens * price_out) if one else 0
    st.caption(f":material/visibility: Output tokens are {share:.0%} of this cost. {visual.notice}")


def _json_rows(value, path="$", rows=None, limit=200):
    rows = [] if rows is None else rows
    if len(rows) >= limit:
        return rows
    kind = {dict: "object", list: "array", str: "string", bool: "boolean", type(None): "null",
            int: "number", float: "number"}[type(value)]
    preview = "" if isinstance(value, (dict, list)) else json.dumps(value, ensure_ascii=False)[:80]
    size = f"{len(value)} item(s)" if isinstance(value, (dict, list)) else ""
    rows.append({"Path": path, "Type": kind, "Value": preview or size})
    if isinstance(value, dict):
        for k, v in value.items():
            _json_rows(v, f"{path}.{k}", rows, limit)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            _json_rows(v, f"{path}[{i}]", rows, limit)
    return rows


def inspect_json(text: str):
    """(rows, error). Parses only; never evaluates. Bounded in size and in rows shown."""
    if len(text) > JSON_LIMIT:
        return None, f"Paste at most {JSON_LIMIT:,} characters."
    try:
        value = json.loads(text)
    except json.JSONDecodeError as error:
        return None, f"Not valid JSON: {error.msg} at line {error.lineno}, column {error.colno}."
    except RecursionError:
        return None, "Too deeply nested to inspect."
    return _json_rows(value), None


def json_inspector(key: str) -> None:
    visual = visuals.VISUALS["json_inspector"]
    st.markdown(f"**{visual.title}**")
    st.caption(":material/shield: Parse-only: the app reads your text as JSON data and never runs it.")
    with st.form(f"{key}_form", border=False):
        text = st.text_area("JSON to inspect", '{"title": "Tokens", "minutes": 20, "complete": false, '
                            '"reviewed_by": null, "tags": ["tokens", "context"]}', height=140, key=f"{key}_text")
        submitted = st.form_submit_button("Inspect", icon=":material/search:")
    if submitted or f"{key}_result" in st.session_state:
        if submitted:
            st.session_state[f"{key}_result"] = inspect_json(text)
        rows, error = st.session_state[f"{key}_result"]
        if error:
            st.warning(error, icon=":material/error:")
        else:
            st.success(f"Valid JSON: {len(rows)} value(s) found.", icon=":material/check_circle:")
            st.dataframe(rows, hide_index=True, use_container_width=True)
            st.caption(visual.notice)
