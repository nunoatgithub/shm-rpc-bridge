#!/bin/bash
set -e

cd "$(dirname "$0")"

rm -f server_profile.prof client_profile.prof

echo "Profiling..."
python echo_server.py &
SERVER_PID=$!
sleep 2
python echo_client.py
sleep 2
kill -TERM $SERVER_PID
wait $SERVER_PID 2>/dev/null || true
echo ""
echo "Profiling complete!"
echo ""
echo "To view results, run:"
echo "  snakeviz server_profile.prof"
echo "  snakeviz client_profile.prof"




