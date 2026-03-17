from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from dotenv import load_dotenv
from app.agents.tools import (
    flight_delay,
    gate_utilization,
    runway_utilization,
    operations_snapshot,
    high_risk_flights,
    gse_overview,
    surface_overview,
)

load_dotenv()

def build_explanation_agent():

    tools = [
        runway_utilization,
        gate_utilization,
        flight_delay,
        operations_snapshot,
        high_risk_flights,
        gse_overview,
        surface_overview,
    ]

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-lite",
        temperature=0,
        max_retries=1,
        max_tokens=420,
    )

    system_prompt = (
        "You are an AI Airport Operations Explanation Assistant.\n\n"
        "Available tools:\n"
        "- runway_utilization\n"
        "- gate_utilization\n"
        "- flight_delay (requires a flight_id)\n\n"
        "- operations_snapshot (window summary)\n"
        "- high_risk_flights (delay headroom risk)\n"
        "- gse_overview (resource/task pressure)\n"
        "- surface_overview (taxi flow and holds)\n\n"
        "You MUST use available tools to retrieve operational data whenever needed.\n"
        "You are NOT allowed to invent runway IDs, gate IDs, or delay values.\n\n"
        "Never say you do not have tools; use the listed tools.\n"
        "If asked for bottlenecks, risks, causes, recommendations, or briefing,\n"
        "you should call at least one relevant tool before answering.\n"
        "After calling tools, explain clearly and professionally.\n"
        "Respond in plain English with short sections and bullet points.\n"
        "Keep response concise and operationally useful."
    )

    agent = create_agent(
        llm,
        tools,
        system_prompt=system_prompt,
    )

    return agent
