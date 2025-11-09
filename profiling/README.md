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

```bash
snakeviz server_profile.prof
snakeviz client_profile.prof
```



