# Profiling

Profile client and server performance with cProfile and snakeviz.

## Usage

```bash
./run_profile.sh
```

This will:
1. Start the echo server with profiling enabled
2. Run the client making 50.000 calls with 2MB messages
3. Stop the server after 50.000 calls
4. Generate profile files

## View Results

The profiling script automatically prints statistics for both server and client, showing:
- Top 20 functions by cumulative time
- Top 20 functions by total time

Profile files are also saved for later analysis:

```bash
python -m pstats server_profile.prof
python -m pstats client_profile.prof
```

For visual analysis:

```bash
snakeviz server_profile.prof
snakeviz client_profile.prof
```



