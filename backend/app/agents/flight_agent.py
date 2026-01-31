from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from app.agents.tools import check_gate_availability, suggest_runway
import os
from dotenv import load_dotenv

load_dotenv()

def build_flight_agent():
    # 1. Define the tools the agent can use
    tools = [check_gate_availability, suggest_runway]

    # 2. Initialize Gemini (using stable 1.5-flash)
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-lite",
        temperature=0,
        max_retries=1,
        max_tokens=150,
    )

    # 3. Define system prompt
    system_prompt = (
        "You are a Flight Agent responsible for handling arriving flights. "
        "Use the check_gate_availability and suggest_runway tools to assign an available gate and runway. "
        "Respond ONLY with valid JSON: {\"assigned_gate\": \"G2\", \"assigned_runway\": \"R1\"}"
    )
    
    # 4. Construct and return the agent
    agent = create_agent(
        llm, 
        tools, 
        system_prompt=system_prompt
    )
    
    return agent