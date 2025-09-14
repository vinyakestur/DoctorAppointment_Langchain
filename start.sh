#!/bin/bash

# Doctor Appointment Multiagent System Startup Script
# This script starts both the backend and frontend services

echo "🩺 Starting Doctor Appointment Multiagent System..."
echo "=================================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "Please create a .env file with your API keys:"
    echo "ANTHROPIC_API_KEY=your_anthropic_api_key_here"
    echo "LANGSMITH_API_KEY=your_langsmith_api_key_here (optional)"
    echo ""
fi

# Check if requirements are installed
echo "📦 Checking dependencies..."
if ! python -c "import fastapi, streamlit, langchain" 2>/dev/null; then
    echo "📥 Installing dependencies..."
    pip install -r requirements.txt
fi

# Start backend in background
echo "🚀 Starting backend server (FastAPI)..."
uvicorn main:app --host 0.0.0.0 --port 8003 --reload &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 3

# Check if backend is running
if curl -s http://127.0.0.1:8003/health > /dev/null; then
    echo "✅ Backend server started successfully!"
else
    echo "❌ Backend server failed to start"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

# Start frontend
echo "🎨 Starting frontend (Streamlit)..."
echo "🌐 Frontend will be available at: http://localhost:8501"
echo "🔧 Backend API available at: http://localhost:8003"
echo "📚 API Documentation: http://localhost:8003/docs"
echo ""
echo "Press Ctrl+C to stop both services"

# Start streamlit (this will block)
streamlit run streamlit_ui.py --server.port 8501

# Cleanup function
cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    kill $BACKEND_PID 2>/dev/null
    echo "✅ Services stopped"
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM
