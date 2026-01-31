from langchain_google_genai import ChatGoogleGenerativeAI
# We alias 'create_tool_calling_agent' to 'create_agent' for your code preference
from langchain.agents import create_tool_calling_agent as create_agent
from langchain.agents import AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from app.agents.tools import check_gate_availability, suggest_runway
import os
from dotenv import load_dotenv

load_dotenv()

def build_flight_agent():
    # 1. Define the tools the agent can use
    tools = [check_gate_availability, suggest_runway]

    # 2. Initialize Gemini (using stable 1.5-flash)
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        temperature=0,
        max_retries=1,
        max_tokens=150,
    )

    # 3. Create a Prompt Template (Required for 0.1.x agents)
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are a Flight Agent responsible for handling arriving flights. "
            "Use the `check_gate_availability` and `suggest_runway` tools to assign an available gate and runway. "
            "Respond ONLY with valid JSON: {{\"assigned_gate\": \"G2\", \"assigned_runway\": \"R1\"}}"
        )),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"), # Internal monologue space for tools
    ])
    
    # 4. Construct the agent using your aliased 'create_agent'
    agent = create_agent(llm, tools, prompt=prompt)

    # 5. Wrap in an Executor (this is what you actually invoke)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)