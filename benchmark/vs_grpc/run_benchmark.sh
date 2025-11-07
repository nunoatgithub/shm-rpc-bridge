#!/bin/bash
set -e

echo "======================================================================="
echo "SHM-RPC vs gRPC Benchmark Runner"
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

echo "Installing grpcio..."
pip install -q grpcio grpcio-tools || {
    echo "Error: Failed to install gRPC"
    exit 1
}
echo "✓ grpcio and grpcio-tools installed"
echo ""

# Generate gRPC code from proto file
echo "Generating gRPC code from proto file..."
cd benchmark/vs_grpc
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. echo.proto
cd ../..
echo "✓ gRPC code generated"
echo ""

# Clean up any leftover resources
echo "Cleaning up any leftover shared memory and socket resources..."
python util/cleanup_ipc.py 2>/dev/null || true
rm -f /tmp/grpc_benchmark.sock 2>/dev/null || true
echo "✓ Cleanup complete"
echo ""

# Run the benchmark
echo "======================================================================="
echo "Running SHM-RPC vs gRPC benchmark..."
echo "This will take several minutes"
echo "======================================================================="
echo ""

python benchmark/vs_grpc/benchmark_vs_grpc.py

echo ""
echo "======================================================================="
echo "Benchmark complete!"
echo "======================================================================="

