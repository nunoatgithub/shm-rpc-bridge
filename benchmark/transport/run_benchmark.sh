#!/bin/bash
set -e

echo "======================================================================="
echo "Transport Layer Benchmark Runner (POSIX vs ZeroMQ IPC)"
echo "======================================================================="
echo ""

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "Error: Please run this script from the repository root directory"
    exit 1
fi

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"
echo ""

# Install dependencies
echo "Installing dependencies..."
echo "---"

echo "Installing posix-ipc..."
pip install -q posix-ipc || {
    echo "Error: Failed to install posix-ipc"
    echo "You may need to install system dependencies first:"
    echo "  Ubuntu/Debian: sudo apt-get install python3-dev"
    echo "  Fedora/RHEL:   sudo dnf install python3-devel"
    exit 1
}
echo "✓ posix-ipc installed"

echo "Installing pyzmq..."
pip install -q pyzmq || {
    echo "Error: Failed to install pyzmq"
    exit 1
}
echo "✓ pyzmq installed"
echo ""

# Run the benchmark
echo "======================================================================="
echo "Running benchmark (this may take several minutes)..."
echo "======================================================================="
echo ""

python benchmark/transport/transport_benchmark.py

echo ""
echo "======================================================================="
echo "Benchmark complete!"
echo "======================================================================="
