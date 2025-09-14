import os
import logging
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic

# Optional imports for fallback models
try:
    from langchain_openai import ChatOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from langchain_groq import ChatGroq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

load_dotenv()

logger = logging.getLogger(__name__)

class LLMModel:
    def __init__(self, model_name="claude-3-5-sonnet-20241022"):
        if not model_name:
            raise ValueError("Model is not defined.")
        self.model_name = model_name
        self.primary_model = None
        self.fallback_model = None
        self._setup_models()
        
    def _setup_models(self):
        """Setup primary and fallback models with error handling"""
        try:
            # Try to setup Anthropic as primary
            ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
            if ANTHROPIC_API_KEY:
                os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY
                self.primary_model = ChatAnthropic(
                    model=self.model_name,
                    max_tokens=4000,
                    temperature=0.1
                )
                logger.info("Anthropic Claude model initialized successfully")
            else:
                logger.warning("ANTHROPIC_API_KEY not found")
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic model: {e}")
        
        # Setup fallback models
        if OPENAI_AVAILABLE:
            try:
                # Try OpenAI as fallback
                OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
                if OPENAI_API_KEY:
                    self.fallback_model = ChatOpenAI(
                        model="gpt-3.5-turbo",
                        temperature=0.1,
                        max_tokens=4000
                    )
                    logger.info("OpenAI fallback model initialized")
            except Exception as e:
                logger.warning(f"OpenAI fallback not available: {e}")
        
        # Try Groq as another fallback
        if GROQ_AVAILABLE and not self.fallback_model:
            try:
                GROQ_API_KEY = os.getenv("GROQ_API_KEY")
                if GROQ_API_KEY:
                    self.fallback_model = ChatGroq(
                        model="llama3-8b-8192",
                        temperature=0.1,
                        max_tokens=4000
                    )
                    logger.info("Groq fallback model initialized")
            except Exception as e:
                logger.warning(f"Groq fallback not available: {e}")
        
        # If no models available, raise error
        if not self.primary_model and not self.fallback_model:
            raise ValueError("No LLM models available. Please check your API keys.")
    
    def get_model(self):
        """Get the best available model"""
        if self.primary_model:
            return self.primary_model
        elif self.fallback_model:
            logger.warning("Using fallback model due to primary model unavailability")
            return self.fallback_model
        else:
            raise ValueError("No models available")
    
    def get_model_with_retry(self, max_retries=3):
        """Get model with retry logic for overload errors"""
        for attempt in range(max_retries):
            try:
                model = self.get_model()
                # Test the model with a simple call
                test_response = model.invoke("Hello")
                return model
            except Exception as e:
                if "overloaded" in str(e).lower() or "529" in str(e):
                    logger.warning(f"Model overloaded (attempt {attempt + 1}/{max_retries}): {e}")
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                else:
                    logger.error(f"Model error: {e}")
                    break
        
        # If all retries failed, try fallback
        if self.fallback_model and self.primary_model:
            logger.warning("Switching to fallback model after retries failed")
            return self.fallback_model
        
        raise Exception("All models failed after retries")

if __name__ == "__main__":
    llm_instance = LLMModel()  
    llm_model = llm_instance.get_model()
    response=llm_model.invoke("hi")

    print(response)