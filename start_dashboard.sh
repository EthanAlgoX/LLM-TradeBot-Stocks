#!/bin/bash
# Start development servers

echo "🚀 Starting AI Stock Daily Dashboard..."

# Start backend
echo "📡 Starting FastAPI backend on port 8000..."
cd server && pip install -r requirements.txt > /dev/null 2>&1
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

# Wait for backend
sleep 2

# Start frontend
echo "🌐 Starting React frontend on port 3000..."
cd ../web && npm install > /dev/null 2>&1
npm run dev &
FRONTEND_PID=$!

# Start live trader (optional - only during market hours)
echo "📈 Starting Live Trader service..."
cd .. && python live_trader.py --preset momentum &
TRADER_PID=$!

echo ""
echo "✅ Development servers started!"
echo "   Backend:     http://localhost:8000"
echo "   Frontend:    http://localhost:3000"
echo "   API Docs:    http://localhost:8000/docs"
echo "   Live Trader: Running in background (US market hours)"
echo ""
echo "Press Ctrl+C to stop all servers"

# Wait and cleanup
trap "kill $BACKEND_PID $FRONTEND_PID $TRADER_PID 2>/dev/null; exit" SIGINT SIGTERM
wait
