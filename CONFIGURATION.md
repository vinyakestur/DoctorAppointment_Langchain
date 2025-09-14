# Configuration Guide

## Environment Variables

### Required
- `ANTHROPIC_API_KEY`: Your Anthropic Claude API key

### Optional (for observability)
- `LANGSMITH_API_KEY`: Your LangSmith API key for observability
- `LANGSMITH_PROJECT`: Project name for LangSmith (default: doctor-appointment-agent)
- `LANGSMITH_ENDPOINT`: LangSmith endpoint (default: https://api.smith.langchain.com)

### LangSmith Tracing
- `LANGCHAIN_TRACING_V2=true`: Enable LangSmith tracing
- `LANGCHAIN_ENDPOINT=https://api.smith.langchain.com`: LangSmith endpoint
- `LANGCHAIN_API_KEY=your_langsmith_api_key_here`: LangSmith API key
- `LANGCHAIN_PROJECT=doctor-appointment-agent`: Project name

## Setup Instructions

1. **Set your Anthropic API key:**
   ```bash
   export ANTHROPIC_API_KEY=your_anthropic_api_key_here
   ```

2. **Set your LangSmith API key (optional):**
   ```bash
   export LANGSMITH_API_KEY=your_langsmith_api_key_here
   export LANGCHAIN_TRACING_V2=true
   export LANGCHAIN_API_KEY=your_langsmith_api_key_here
   export LANGCHAIN_PROJECT=doctor-appointment-agent
   ```

3. **Run the application:**
   ```bash
   python -m uvicorn main:app --host 127.0.0.1 --port 8003 --reload
   ```

## Features

### Observability
- **LangSmith Integration**: Automatic tracing of all agent interactions
- **Monte Carlo Debugging**: Run simulations to test agent performance
- **Performance Metrics**: Track response times, success rates, and error patterns

### Human-in-the-Loop
- **Approval Workflow**: Human approval required for booking actions
- **Interactive Debugging**: Console-based human input for testing
- **Customizable Callbacks**: Override human input handling for different interfaces

### Debug Endpoints
- `POST /debug/simulation`: Run Monte Carlo simulation
- `GET /debug/report`: Get current debug report
- `GET /health`: Health check endpoint

## Usage Examples

### Running a Debug Simulation
```bash
curl -X POST "http://127.0.0.1:8003/debug/simulation"
```

### Getting Debug Report
```bash
curl -X GET "http://127.0.0.1:8003/debug/report"
```

### Testing Human-in-the-Loop
```bash
curl -X POST "http://127.0.0.1:8003/execute" \
  -H "Content-Type: application/json" \
  -d '{"id_number": 1234567, "messages": "I want to book an appointment with Dr. Smith"}'
```
