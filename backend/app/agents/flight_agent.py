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

    system_prompt = (
        "You are an airport Flight Agent.\n"
        "You MUST choose ONLY from the available gates and runways returned by tools.\n"
        "You are NOT allowed to invent gate or runway IDs.\n\n"
        "Valid gates: G1, G2, G3\n"
        "Valid runways: R1, R2\n\n"
        "Always call tools first.\n"
        "Respond ONLY in valid JSON:\n"
        '{"assigned_gate": "G1", "assigned_runway": "R1"}'
    )
    
    # 4. Construct and return the agent
    agent = create_agent(
        llm, 
        tools, 
        system_prompt=system_prompt
    )
    
    return agent