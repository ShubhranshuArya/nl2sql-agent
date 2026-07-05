from typing import List

from app.state.state import AgentState
from app.services.llm import get_openai_client, get_model, parse_json_response
from app.tools.sql import get_table_names

async def table_selector_node(state: AgentState):
    """
    Selects the relevant tables for the user query from the database schema.
    Uses a provider-agnostic prompt-based JSON output.
    """
    client = get_openai_client()
    
    all_tables = get_table_names()
    formatted_tables = ", ".join(all_tables)
    
    # Use refined query if available, closely matching the user intent
    query_to_use = state.get("refined_query", state["user_query"])
    
    system_prompt = f"""You are an expert database architect.
    Your task is to select the most relevant tables from the database to answer the user's query.
    The available tables are: {formatted_tables}.
    Return a list of ONLY the table names that are strictly necessary.
    Do not halluncinate table names.

    Respond with ONLY a JSON object in this exact form:
    {{"selected_tables": ["TableA", "TableB"]}}
    """
    
    response = await client.chat.completions.create(
        model=get_model(),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query_to_use}
        ],
        temperature=0
    )
    
    data = parse_json_response(response.choices[0].message.content)
    selected = data.get("selected_tables", [])
    if not isinstance(selected, list):
        selected = []
    
    # Filter out any hallucinates tables basically
    valid_tables = [t for t in selected if t in all_tables]
    
    return {"selected_tables": valid_tables}
