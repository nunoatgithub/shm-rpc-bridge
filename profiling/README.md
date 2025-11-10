# Profiling

Profile client and server performance with cProfile and snakeviz.

## Usage

```bash
./run_profile.sh
```

This will:
1. Start the echo server with profiling enabled
2. Run the client making 50,000 calls with 2MB messages
3. Send SIGTERM to the server 2 seconds after client exits
4. Generate profile files and print statistics

## View Results

Both server (on SIGTERM) and client automatically print top 20 functions by cumulative time.

Profile files are saved for later analysis:

```bash
python -m pstats server_profile.prof
python -m pstats client_profile.prof
```

For visual analysis:

```bash
snakeviz server_profile.prof
snakeviz client_profile.prof
```



