import json

from app.state.state import AgentState
from app.services.llm import get_llm_client, get_model, parse_json_response
from app.agents.vega_examples import VEGA_LITE_SCHEMA_V6, get_examples

# Rows sent to the LLM purely for column/type inference. The full result set is
# injected into the spec server-side, so a small sample keeps latency/tokens low.
_SAMPLE_ROWS = 20

async def visualization_planner_node(state: AgentState):
    """
    Decides if a visualization is needed.
    Uses a provider-agnostic prompt-based JSON output.
    """
    client = get_llm_client()
    
    query_to_use = state.get("refined_query", state["user_query"])
    results = state.get("query_result", [])
    
    # If no results or error, no viz
    if not results or state.get("query_error"):
        return {"needs_visualization": False}
        
    system_prompt = f"""You are a data visualization expert.
    Analyze the user request and data to decide if a chart is necessary.
    
    User Query: {query_to_use}
    Data Sample (first few rows): {str(results[:5])}
    
    Rules:
    1. If user explicitly asks for "plot", "chart", "graph", "visualize", return true.
    2. If the data is a time series or distribution that benefits from visualization, return true.
    3. If the data is a single number or text, return false.

    Respond with ONLY a JSON object in this exact form:
    {{"needs_visualization": true, "visualization_type": "bar", "reasoning": "..."}}
    where visualization_type is one of "bar", "line", "pie", "scatter" (or null when not needed).
    """
    
    response = await client.chat.completions.create(
        model=get_model(),
        messages=[
            {"role": "system", "content": system_prompt}
        ],
        temperature=0
    )
    
    data = parse_json_response(response.choices[0].message.content)

    needs_viz = bool(data.get("needs_visualization", False))
    chart_type = data.get("visualization_type") if needs_viz else None
    if chart_type not in ("bar", "line", "pie", "scatter"):
        chart_type = None

    return {
        "needs_visualization": needs_viz,
        "visualization_type": chart_type,
    }


async def visualization_generator_node(state: AgentState):
    """
    Generates a Vega-Lite v6 specification for the data.

    Grounds the model in curated v6 few-shot examples (matching the frontend's
    vega-lite v6 renderer) and asks for the spec WITHOUT data. The full result
    set and the v6 `$schema` are injected server-side to avoid round-tripping the
    data through the LLM and to guarantee the correct schema version.
    """
    client = get_llm_client()

    query_to_use = state.get("refined_query", state["user_query"])
    results = state.get("query_result", [])

    # Nothing to plot; guard against direct/empty invocations.
    if not results:
        return {"visualization_spec": None}

    chart_type = state.get("visualization_type")
    examples = get_examples(chart_type)
    sample = results[:_SAMPLE_ROWS]

    chart_hint = (
        f"The chosen chart type is \"{chart_type}\"."
        if chart_type
        else "Choose the most appropriate chart type for the data."
    )

    system_prompt = f"""You generate Vega-Lite v6 specifications.
    Copy the shape of the official v6 example(s) below; do not invent properties.

    User Query: {query_to_use}
    {chart_hint}

    Data columns come from this sample (first {_SAMPLE_ROWS} rows). Infer field
    names and types from it. Do NOT include the data in your output.
    Data Sample: {json.dumps(sample, default=str)}

    Official Vega-Lite v6 example(s) to follow:
    {json.dumps(examples)}

    Rules:
    1. Return ONLY the JSON object (a single Vega-Lite v6 spec).
    2. Do NOT include a "data" property; it is added later.
    3. Map "field" values to the actual column names from the data sample.
    4. Choose encoding "type" (quantitative/nominal/ordinal/temporal) from the data.
    5. Add a descriptive "title" and tooltips.
    6. Keep "width": "container", "height": 300, and the "autosize" config.
    """

    response = await client.chat.completions.create(
        model=get_model(),
        messages=[
            {"role": "system", "content": system_prompt}
        ],
        temperature=0
    )

    spec = parse_json_response(response.choices[0].message.content)
    if not spec:
        print("Error generating viz: could not parse a JSON specification")
        return {"visualization_spec": None}

    # Inject data + pin the v6 schema server-side (source of truth, not the LLM).
    spec["$schema"] = VEGA_LITE_SCHEMA_V6
    spec["data"] = {"values": results}
    return {"visualization_spec": spec}
