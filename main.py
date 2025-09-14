from fastapi import FastAPI
from pydantic import BaseModel
from mcp_agent import MCPDoctorAppointmentAgent
from langchain_core.messages import HumanMessage, AIMessage
from config.observability import setup_observability
from debugging.monte_carlo import setup_monte_carlo_debugging, run_debug_simulation, get_debug_report
from dotenv import load_dotenv
import os
import logging
from typing import Dict, List, Optional
import uuid

# Load environment variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

os.environ.pop("SSL_CERT_FILE", None)

# Setup observability
setup_observability()


app = FastAPI()

# In-memory conversation storage (in production, use Redis or database)
conversation_sessions: Dict[str, List] = {}

# Define Pydantic model to accept request body
class UserQuery(BaseModel):
    id_number: int
    messages: str
    session_id: Optional[str] = None  # Optional session ID for conversation continuity

class SessionResponse(BaseModel):
    session_id: str
    messages: List[dict]

# Use MCP Agent for better tool separation
agent = MCPDoctorAppointmentAgent()

@app.post("/execute")
def execute_agent(user_input: UserQuery):
    try:
        # Generate or use existing session ID
        session_id = user_input.session_id or str(uuid.uuid4())
        
        # Get conversation history for this session
        session_data = conversation_sessions.get(session_id, {})
        conversation_history = session_data.get("messages", []) if isinstance(session_data, dict) else session_data
        
        # Create input messages with conversation history
        input_messages = [msg for msg in conversation_history if hasattr(msg, 'content') and not msg.content.startswith('User ID:')]
        
        # Create context message for MCP agent
        context_message = f"User ID: {user_input.id_number}\nQuery: {user_input.messages}"
        final_message = HumanMessage(content=context_message)
        
        # Execute the MCP agent
        app_graph = agent.workflow()
        agent_input = {
            "messages": input_messages + [final_message],
            "id_number": user_input.id_number,
            "session_id": session_id
        }
        
        response = app_graph.invoke(agent_input, config={"recursion_limit": 20})
        
    except Exception as e:
        logger.error(f"Unexpected error in execute_agent: {e}")
        return SessionResponse(
            session_id=session_id if 'session_id' in locals() else str(uuid.uuid4()),
            messages=[{
                "content": f"I encountered an error processing your request: {str(e)}. Please try again.",
                "type": "ai", 
                "name": "assistant",
                "id": None
            }]
        )
    
    # Update conversation history
    try:
        # Get the AI response content
        if response["messages"] and len(response["messages"]) > 0:
            last_message = response["messages"][-1]
            if hasattr(last_message, 'content'):
                ai_response_content = last_message.content
            else:
                ai_response_content = last_message.get("content", "")
        else:
            ai_response_content = ""
        
        ai_message = AIMessage(content=ai_response_content)
        user_message = HumanMessage(content=user_input.messages)
        full_conversation = input_messages + [user_message] + [ai_message]
        
        # Filter out context messages from the response for display
        filtered_messages = []
        for msg in response.get("messages", []):
            if hasattr(msg, 'content'):
                if not msg.content.startswith('User ID:'):
                    filtered_messages.append(msg)
            else:
                if not msg.get("content", "").startswith('User ID:'):
                    filtered_messages.append(msg)
        
        response["messages"] = filtered_messages
        
    except (KeyError, IndexError, TypeError, AttributeError):
        full_conversation = response["messages"]
    
    # Store conversation history
    conversation_sessions[session_id] = {
        "messages": full_conversation,
        "agent_state": {
            "id_number": response.get("id_number", user_input.id_number),
            "session_id": session_id
        }
    }
    
    # Convert LangChain messages to dictionaries for JSON serialization
    messages_dict = []
    for msg in response.get("messages", []):
        if hasattr(msg, 'content'):
            messages_dict.append({
                "content": msg.content,
                "type": msg.__class__.__name__.lower().replace("message", ""),
                "name": getattr(msg, 'name', None),
                "id": getattr(msg, 'id', None)
            })
        else:
            messages_dict.append(msg)
    
    return SessionResponse(
        session_id=session_id,
        messages=messages_dict
    )

@app.post("/debug/simulation")
async def run_debug_simulation_endpoint():
    """Run Monte Carlo debug simulation"""
    try:
        # Test cases for debugging
        test_cases = [
            {
                "id_number": 1234567,
                "messages": "Can you check if a dentist is available tomorrow at 10 AM?",
                "expected_output": "dentist availability information"
            },
            {
                "id_number": 1234568,
                "messages": "I want to book an appointment with Dr. Smith",
                "expected_output": "appointment booking process"
            },
            {
                "id_number": 1234569,
                "messages": "Cancel my appointment for tomorrow",
                "expected_output": "appointment cancellation"
            }
        ]
        
        # Run simulation
        results = await run_debug_simulation(agent.workflow().invoke, test_cases, num_simulations=5)
        
        return {
            "status": "success",
            "simulation_results": results,
            "debug_report": get_debug_report()
        }
    except Exception as e:
        logger.error(f"Debug simulation failed: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/debug/report")
def get_debug_report_endpoint():
    """Get current debug report"""
    try:
        report = get_debug_report()
        return {"status": "success", "report": report}
    except Exception as e:
        logger.error(f"Failed to get debug report: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "doctor-appointment-agent"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
