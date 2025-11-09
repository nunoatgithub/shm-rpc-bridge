#!/bin/bash
set -e

echo "======================================================================="
echo "SHM-RPC Bridge Benchmark Runner"
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
pip install -q posix-ipc || {
    echo "Error: Failed to install posix-ipc"
    echo "You may need to install system dependencies first:"
    echo "  Ubuntu/Debian: sudo apt-get install python3-dev"
    echo "  Fedora/RHEL:   sudo dnf install python3-devel"
    exit 1
}

echo "✓ posix-ipc installed"

pip install -q orjson || {
    echo "Error: Failed to install orjson"
    exit 1
}

echo "✓ orjson installed"
echo ""

# Clean up any leftover resources
echo "Cleaning up any leftover shared memory resources..."
python util/cleanup_ipc.py 2>/dev/null || true
echo "✓ Cleanup complete"
echo ""

# Run the benchmark
echo "======================================================================="
echo "Running benchmark (this may take several minutes)..."
echo "======================================================================="
echo ""

python benchmark/benchmark_ipc.py

echo ""
echo "======================================================================="
echo "Benchmark complete!"
echo "======================================================================="

