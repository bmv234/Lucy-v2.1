#!/bin/bash

# Check if pyenv is installed
if ! command -v pyenv &> /dev/null
then
    echo "pyenv is not installed. Please install pyenv first."
    exit 1
fi

# Set Python version locally
echo "Setting Python version to 3.10 using pyenv..."
pyenv local 3.10.12

# Activate the virtual environment
if [ -f "venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "Virtual environment not found at 'venv/bin/activate'."
    exit 1
fi

# Set the environment variable and run the server
echo "Starting the server with MECAB_SKIP=1..."
MECAB_SKIP=1 python server.py
