"""
MCP-based Agent for Doctor Appointment System
Uses Model Context Protocol for clear separation of booking and cancellation flows
"""

from typing import Literal, List, Any
from langgraph.types import Command
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from utils.llms import LLMModel
from dotenv import load_dotenv
import logging
from mcp_tools import mcp_agent

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

class MCPAgentState(TypedDict):
    messages: Annotated[list[Any], add_messages]
    id_number: int
    session_id: str

class MCPDoctorAppointmentAgent:
    def __init__(self):
        llm_model = LLMModel()
        self.llm_model = llm_model.get_model_with_retry()
        self.llm_instance = llm_model
        self.mcp_agent = mcp_agent
    
    def main_chat_node(self, state: MCPAgentState) -> Command[Literal['__end__']]:
        """Main chat node using MCP tools"""
        user_query = ""
        if state["messages"]:
            for msg in reversed(state["messages"]):
                if hasattr(msg, '__class__') and 'HumanMessage' in str(type(msg)):
                    user_query = msg.content
                    break
        
        user_id = state.get('id_number', 1234567)
        session_id = state.get('session_id', 'default_session')
        
        # Extract just the query part if it's wrapped in context format
        if "Query: " in user_query:
            user_query = user_query.split("Query: ")[1].strip()
        
        # Process request using MCP agent
        try:
            result = self.mcp_agent.process_request(session_id, user_id, user_query)
            
            # Format response based on action type
            if result["action"] == "cancellation_confirmation":
                response = result["message"]
            elif result["action"] == "cancellation_completed":
                response = result["message"]
            elif result["action"] == "cancellation_cancelled":
                response = result["message"]
            elif result["action"] == "booking_confirmation":
                response = result["message"]
            elif result["action"] == "booking_completed":
                response = result["message"]
            elif result["action"] == "booking_cancelled":
                response = result["message"]
            elif result["action"] == "show_appointments":
                response = result["message"]
            elif result["action"] == "show_availability":
                response = result["message"]
            elif result["action"] == "error":
                response = result["message"]
            elif result["action"] == "general":
                response = result["message"]
            else:
                response = "I'm here to help you with appointment booking and cancellation. What would you like to do?"
            
            return Command(
                update={
                    "messages": state["messages"] + [AIMessage(content=response)],
                    "session_id": session_id
                },
                goto="__end__"
            )
            
        except Exception as e:
            logger.error(f"Error in MCP agent: {e}")
            response = f"I encountered an error processing your request: {str(e)}. Please try again."
            return Command(
                update={
                    "messages": state["messages"] + [AIMessage(content=response)]
                },
                goto="__end__"
            )
    
    def workflow(self):
        """Create MCP-based workflow"""
        workflow = StateGraph(MCPAgentState)
        
        # Add nodes
        workflow.add_node("chat", self.main_chat_node)
        
        # Set entry point
        workflow.set_entry_point("chat")
        
        # Add edges
        workflow.add_edge("chat", END)
        
        # Compile the workflow
        self.app = workflow.compile()
        return self.app
