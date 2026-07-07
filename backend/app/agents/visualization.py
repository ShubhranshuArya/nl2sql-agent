import json

from app.state.state import AgentState
from app.services.llm import get_llm_client, get_model, parse_json_response

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
    return {"needs_visualization": bool(data.get("needs_visualization", False))}


async def visualization_generator_node(state: AgentState):
    """
    Generates a Vega-Lite specification for the data.
    """
    client = get_llm_client()
    
    query_to_use = state.get("refined_query", state["user_query"])
    results = state["query_result"]
    
    system_prompt = f"""You are a Vega-Lite expert.
    Generate a valid Vega-Lite JSON specification to visualize the provided data.
    
    User Query: {query_to_use}
    Data: {json.dumps(results)}
    
    Rules:
    1. Return ONLY the JSON object.
    2. Use the 'data' property with 'values' set to the provided data.
    3. Choose appropriate encodings based on the data types.
    4. Add a title and tooltips.
    5. Set "width": "container" to ensure it takes the full available width.
    6. Set "height": 300 for a good aspect ratio.
    7. Enable "autosize": {{ "type": "fit", "contains": "padding" }}.
    8. Use a minimal pastel color theme. Always include a top-level "config" object exactly like this:
       "config": {{
         "background": "white",
         "view": {{ "stroke": null }},
         "range": {{ "category": ["#818CF8", "#C4B5FD", "#F9A8D4", "#A5B4FC", "#DDD6FE", "#FBCFE8"] }},
         "mark": {{ "color": "#818CF8" }},
         "axis": {{ "gridColor": "#EEF2F6", "domainColor": "#E2E8F0", "tickColor": "#E2E8F0", "labelColor": "#64748B", "titleColor": "#334155", "labelFontSize": 11, "grid": true }},
         "legend": {{ "labelColor": "#64748B", "titleColor": "#334155" }},
         "title": {{ "color": "#0F172A" }}
       }}
    9. For any color encoding, rely on the categorical "range" above. For single-series bar/line/area charts, do NOT set an explicit color; let the default mark color apply. Never use bright default Vega colors.
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
    return {"visualization_spec": spec}
