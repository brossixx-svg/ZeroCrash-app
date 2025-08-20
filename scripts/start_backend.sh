#!/bin/bash

# ZeroCrash Backend Startup Script

echo "🚀 Starting ZeroCrash Backend..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ to continue."
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ main.py not found. Please run this script from the backend directory."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "📄 Creating .env file from template..."
    cp ../.env.example .env
    echo "⚠️  Please edit .env file with your API keys before running in production mode"
fi

# Initialize database
echo "🗃️  Initializing database..."
python3 -c "from main import init_db; init_db(); print('✅ Database initialized')"

# Run database migrations if needed
echo "🔄 Running database setup..."

# Start the application
echo "🌟 Starting FastAPI server..."
echo "📡 Server will be available at: http://localhost:8000"
echo "📋 API Documentation: http://localhost:8000/docs"
echo "🔍 Health Check: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start with uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload --log-level info