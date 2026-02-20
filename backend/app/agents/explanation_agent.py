from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from dotenv import load_dotenv
from app.agents.tools import flight_delay, gate_utilization, runway_utilization

load_dotenv()

def build_explanation_agent():

    tools = [
        runway_utilization,
        gate_utilization,
        flight_delay,
    ]

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-lite",
        temperature=0,
        max_retries=1,
        max_tokens=150,
    )

    system_prompt = (
        "You are an AI Airport Operations Explanation Assistant.\n\n"
        "You MUST use available tools to retrieve operational data.\n"
        "You are NOT allowed to invent runway IDs, gate IDs, or delay values.\n\n"
        "After calling tools, explain clearly and professionally.\n"
        "Respond in plain English."
    )

    agent = create_agent(
        llm,
        tools,
        system_prompt=system_prompt,
    )

    return agent