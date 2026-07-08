from app.state.state import AgentState
from app.services.llm import get_llm_client, get_model, parse_json_response
from app.services.data_dictionary import get_domain_description

async def query_router_node(state: AgentState):
    """
    Analyzes the user query to determine if it's relevant to the e-commerce database.
    """
    client = get_llm_client()

    system_prompt = f"""You are an expert at routing user queries.
    Your task is to determine if the user's query is relevant to the following database.

    {get_domain_description()}

    If the query is a greeting, chitchat, or completely unrelated to e-commerce, retail, supply chain, or business analytics, mark it as 'irrelevant'.
    Otherwise, mark it as 'relevant'.

    Respond with ONLY a JSON object in this exact form:
    {{"relevance": "relevant"}} or {{"relevance": "irrelevant"}}
    """

    response = await client.chat.completions.create(
        model=get_model(),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": state["user_query"]}
        ],
        temperature=0
    )

    data = parse_json_response(response.choices[0].message.content)
    relevance = data.get("relevance")
    if relevance not in ("relevant", "irrelevant"):
        relevance = "irrelevant"
    return {"relevance": relevance}
