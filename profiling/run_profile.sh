#!/bin/bash
set -e

cd "$(dirname "$0")"

rm -f server_profile.prof client_profile.prof

echo "Profiling..."
python echo_server.py &
sleep 2
python echo_client.py
sleep 2
echo ""
echo "Profiling complete!"
echo ""
echo "To view results, run:"
echo "  snakeviz server_profile.prof"
echo "  snakeviz client_profile.prof"


