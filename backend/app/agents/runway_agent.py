from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from app.agents.tools import suggest_runway
import os
from dotenv import load_dotenv

load_dotenv()

def build_runway_agent():  # Renamed for clarity
    tools = [suggest_runway]
    llm = ChatGoogleGenerativeAI(
    model="gemini-3-pro-preview",
    temperature=0,
    google_api_key=os.environ.get("GEMINI_API_KEY")
)
    llm_with_tools = llm.bind_tools(tools)  # Bind tools to LLM

    system_prompt = (
        "You are a Runway Agent. Assign the best available runway for landing or takeoff. "
        "Respond with JSON: {\"assigned_runway\": \"R1\"}"
    )
    
    agent = create_agent(
        llm_with_tools,
        tools,
        system_prompt=system_prompt
    )
    
    return agent