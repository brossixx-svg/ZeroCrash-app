#!/bin/bash

# ZeroCrash Backend Test Runner

echo "🧪 Running ZeroCrash Backend Tests..."

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ main.py not found. Please run this script from the backend directory."
    exit 1
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "🔧 Activating virtual environment..."
    source venv/bin/activate
fi

# Set test environment
export MOCK_MODE=true
export DATABASE_URL=sqlite:///:memory:
export CACHE_TTL=60

echo "🏃 Running all tests..."
echo ""

# Run tests with coverage
python -m pytest tests/ -v --tb=short --color=yes

# Check test results
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All tests passed!"
    echo ""
    
    # Run specific test categories
    echo "🔍 Running integration tests..."
    python -m pytest tests/test_main.py::TestIntegration -v
    
    echo ""
    echo "⚡ Running performance tests..."
    python -m pytest tests/test_main.py::TestPerformance -v
    
    echo ""
    echo "🎯 Test Summary:"
    python -m pytest tests/ --tb=no -q
    
else
    echo ""
    echo "❌ Some tests failed. Please check the output above."
    exit 1
fi

echo ""
echo "🏁 Test run completed!"