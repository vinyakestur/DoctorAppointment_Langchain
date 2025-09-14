"""
Observability configuration for LangSmith and Monte Carlo debugging
"""
import os
from typing import Optional
from langsmith import Client
from langchain_core.tracers import LangChainTracer
from langchain_core.callbacks import BaseCallbackHandler
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ObservabilityConfig:
    def __init__(self):
        self.langsmith_api_key = os.getenv("LANGSMITH_API_KEY")
        self.langsmith_project = os.getenv("LANGSMITH_PROJECT", "doctor-appointment-agent")
        self.langsmith_endpoint = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
        
        # Initialize LangSmith client
        self.client = None
        if self.langsmith_api_key:
            self.client = Client(
                api_key=self.langsmith_api_key,
                api_url=self.langsmith_endpoint
            )
            logger.info(f"LangSmith client initialized for project: {self.langsmith_project}")
        else:
            logger.warning("LANGSMITH_API_KEY not found. Observability features will be disabled.")
    
    def get_tracer(self) -> Optional[LangChainTracer]:
        """Get LangChain tracer for observability"""
        if self.client:
            return LangChainTracer(
                project_name=self.langsmith_project,
                client=self.client
            )
        return None
    
    def get_callbacks(self) -> list:
        """Get callbacks for tracing"""
        callbacks = []
        tracer = self.get_tracer()
        if tracer:
            callbacks.append(tracer)
        return callbacks

# Global observability config
observability_config = ObservabilityConfig()


def setup_observability():
    """Setup observability for the application"""
    # Set environment variables for LangSmith
    if observability_config.langsmith_api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_ENDPOINT"] = observability_config.langsmith_endpoint
        os.environ["LANGCHAIN_API_KEY"] = observability_config.langsmith_api_key
        os.environ["LANGCHAIN_PROJECT"] = observability_config.langsmith_project
        logger.info("Observability setup complete")
    else:
        logger.warning("LangSmith not configured. Set LANGSMITH_API_KEY to enable observability")

def get_observability_callbacks():
    """Get all observability callbacks"""
    return observability_config.get_callbacks()
