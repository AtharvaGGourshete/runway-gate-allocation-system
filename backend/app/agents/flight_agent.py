from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from app.agents.tools import check_gate_availability, suggest_runway
import os
from dotenv import load_dotenv

load_dotenv()

def build_flight_agent():
    tools = [check_gate_availability, suggest_runway]

    llm = ChatOpenAI(
        model="gpt-4.1-mini",
        temperature=0,
        max_retries=2,
        max_tokens=200,  # keep enough room for tool calls + final JSON
    )

    llm_with_tools = llm.bind_tools(tools)

    system_prompt = (
        "You are a Flight Agent responsible for handling arriving flights. "
        "Use the `check_gate_availability` and `suggest_runway` tools to assign an available gate and runway. "
        "Respond only with JSON: {\"assigned_gate\": \"G2\", \"assigned_runway\": \"R1\"}"
    )

    agent = create_agent(
        llm_with_tools,
        tools,
        system_prompt=system_prompt,
    )

    return agent