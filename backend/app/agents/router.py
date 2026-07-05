from app.state.state import AgentState
from app.services.llm import get_openai_client, get_model, parse_json_response

async def query_router_node(state: AgentState):
    """
    Analyzes the user query to determine if it's relevant to the e-commerce database.
    Uses a provider-agnostic prompt-based JSON output.
    """
    client = get_openai_client()

    system_prompt = """You are an expert at routing user queries.
    Your task is to determine if the user's query is relevant to a global e-commerce and supply chain analytics database.
    The database contains information about: customers, products, transactions (sales orders), returns, inventory levels, price history, supplier costs, and marketing spend.
    If the query is greeting, chitchat, or completely unrelated to e-commerce, retail, supply chain, or business analytics, mark it as 'irrelevant'.
    Otherwise, mark it as 'relevant'.

    Respond with ONLY a JSON object in this exact form:
    {"relevance": "relevant"} or {"relevance": "irrelevant"}
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
