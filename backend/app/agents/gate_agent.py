from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from app.agents.tools import check_gate_availability
import os
from dotenv import load_dotenv

load_dotenv()

def build_gate_agent():  # Renamed for clarity
    tools = [check_gate_availability]
    llm = ChatGoogleGenerativeAI(
    model="gemini-3-pro-preview",
    temperature=0,
    google_api_key=os.environ.get("GEMINI_API_KEY")
)
    llm_with_tools = llm.bind_tools(tools)  # Bind tools to LLM

    system_prompt = (
        "You are a Gate Agent. Assign an available gate to the incoming flight. "
        "Respond with JSON: {\"assigned_gate\": \"G2\"}"
    )
    
    agent = create_agent(
        llm_with_tools,
        tools,
        system_prompt=system_prompt  # ✅ system_prompt (not system_message)
    )
    
    return agent