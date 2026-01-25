from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from app.agents.tools import resolve_conflict
import os
from dotenv import load_dotenv

load_dotenv()

def build_conflict_agent():  # Renamed for clarity
    tools = [resolve_conflict]
    llm = ChatGoogleGenerativeAI(
    model="gemini-3-pro-preview",
    temperature=0,
    google_api_key=os.environ.get("GEMINI_API_KEY")
)
    llm_with_tools = llm.bind_tools(tools)  # Bind tools to LLM

    system_prompt = (
        "You are a Scheduler Agent. A conflict between flight schedules has been detected. "
        "Use your tools to resolve it. Respond with JSON: {\"status\": \"conflict resolved\"}"
    )
    
    agent = create_agent(
        llm_with_tools,
        tools,
        system_prompt=system_prompt
    )
    
    return agent