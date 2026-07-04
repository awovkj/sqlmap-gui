#!/bin/bash

echo "========================================"
echo "  SQLmap GUI 2.0 - Starting..."
echo "========================================"
echo ""

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "[ERROR] Node.js not found. Please install Node.js first."
    echo "Download: https://nodejs.org/"
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "[ERROR] Python not found. Please install Python first."
        echo "Download: https://python.org/"
        exit 1
    fi
    PYTHON_CMD="python"
else
    PYTHON_CMD="python3"
fi

# Install dependencies (first run)
if [ ! -d "node_modules" ]; then
    echo "[1/3] Installing frontend dependencies..."
    npm install
    echo ""
fi

# Install Python dependencies
echo "[2/3] Checking Python dependencies..."
$PYTHON_CMD -m pip install -r requirements.txt -q 2>/dev/null

echo "[3/3] Starting application..."
echo ""
echo "----------------------------------------"
echo "  Application will start automatically"
echo "  Press Ctrl+C to stop"
echo "----------------------------------------"
echo ""

npm start
