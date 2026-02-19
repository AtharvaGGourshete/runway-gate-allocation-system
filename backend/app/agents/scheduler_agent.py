import os
import time
import json
from ratelimit import limits, sleep_and_retry

# 1. Google & LangChain Imports
from langchain_google_genai import ChatGoogleGenerativeAI
# 'tool' is now in langchain_core
from langchain_core.tools import tool
# The agent helpers remain in langchain.agents
from langchain_classic.agents import AgentExecutor
from langchain_classic.agents import create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from app.optimization.airport_solver import solve_and_simulate  # Import your solver

# ==========================================
# PART 1: The Rate Limiter (Safety Valve)
# ==========================================
# Constraint: Allow max 10 calls every 60 seconds (Conservative safe limit)
CALLS = 10
PERIOD = 60

@sleep_and_retry
@limits(calls=CALLS, period=PERIOD)
def safe_google_call(agent_executor, input_data):
    """
    Wraps the agent execution with a rate limiter.
    If we hit the limit, this function SLEEPS automatically until safe.
    """
    return agent_executor.invoke(input_data)

# ==========================================
# PART 2: The Tool (Math Engine)
# ==========================================
@tool
def run_airport_system(num_runways: int, num_gates: int, flights: str) -> str:
    """
    Calculates schedule using OR-Tools and verifies with SimPy.
    Inputs:
    - num_runways: Int
    - num_gates: Int
    - flights: JSON string of flight data
    """
    try:
        flight_data = json.loads(flights)
        result = solve_and_simulate(
            L=num_runways, 
            G=num_gates, 
            T=num_runways, 
            planes_data=flight_data
        )
        return json.dumps(result)
    except Exception as e:
        return f"System Error: {str(e)}"

# ==========================================
# PART 3: The Agent (Gemini Flash-Lite)
# ==========================================
def build_scheduler_agent():
    # Ensure API Key is set
    if "GEMINI_API_KEY" not in os.environ:
        raise ValueError("Please set GEMINI_API_KEY environment variable")

    # Initialize Gemini 2.5 Flash-Lite
    # temperature=0 ensures the agent is factual and deterministic
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite", # Or specific 'gemini-1.5-flash' if 2.5 isn't public yet
        temperature=0,
        max_retries=2,
    )
    
    tools = [run_airport_system]
    
    # System Prompt: Explicit instructions for the AI
    prompt = ChatPromptTemplate.from_messages([
        ("system", 
         "You are the 'AeroOps' Assistant. Your goal is to schedule flights safely.\n"
         "RULES:\n"
         "1. ALWAYS use the 'run_airport_system' tool for scheduling. Do not guess.\n"
         "2. Input data must be structured carefully for the tool.\n"
         "3. Explain the output clearly: Mention which gate was assigned and if SimPy detected any delays.\n"
         "4. If SimPy reports 'CRITICAL' delays, warn the user immediately."),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    
    # Return the Executor
    return AgentExecutor(agent=agent, tools=tools, verbose=True)

# ==========================================
# PART 4: Execution Helper
# ==========================================
def run_agent_safely(user_input):
    """
    Main function to call from your UI/Main script.
    Handles rate limiting automatically.
    """
    print("⏳ Connecting to Gemini (Rate Limiter Active)...")
    agent = build_scheduler_agent()
    
    # Use the rate-limited wrapper
    response = safe_google_call(agent, {"input": user_input})
    return response['output']