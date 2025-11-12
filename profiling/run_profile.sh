#!/bin/bash
set -e

cd "$(dirname "$0")"

rm -f server_profile.prof client_profile.prof

NAME="profile"
BUFFER_SIZE=2500000 #2.5 MB
ITERATIONS=30000

echo "Profiling..."
python echo_server.py $NAME $BUFFER_SIZE $ITERATIONS 2>&1 &
SERVER_PID=$!
sleep 2
python echo_client.py $NAME $BUFFER_SIZE $ITERATIONS 2>&1
wait $SERVER_PID 2>/dev/null || true
echo ""
echo "Profiling complete!"
echo ""
echo "To view results, run:"
echo "  snakeviz server_profile.prof"
echo "  snakeviz client_profile.prof"




