# Accumulator RPC Example (Stateful)

This directory contains a minimal example of using the shm-rpc-bridge library
to implement a simple stateful "accumulator" service over shared memory.

Each client keeps its own running total identified by a `client_id`.

## Files

- `accumulator_server.py` - The server that maintains per-client totals
- `accumulator_client.py` - The client that calls the server methods

## Running the Example

### 1. Start the Server

In one terminal:

```bash
python examples/stateful/accumulator_server.py
```

You should see something like:

```
Starting Accumulator RPC Server...
Channel: accumulator_rpc
Server ready! Waiting for requests...
Press Ctrl+C to stop.
```

### 2. Run the Client

In another terminal:

#### Demo Mode (default)

Run a short demonstration that shows state per `client_id` and clearing:

```bash
python examples/stateful/accumulator_client.py
```

It will:
- Accumulate twice for `alice`
- Accumulate twice for `bob` (independent state)
- Accumulate again for `alice` to show `bob` was unaffected
- Clear `alice`
- Do a final accumulate for `alice` (shows it restarted) and for `bob` (continues from previous)

#### Interactive Mode

Use the service interactively:

```bash
python examples/stateful/accumulator_client.py --interactive
```

Example session:

```
Enter operation (accumulate|clear or 'quit'): accumulate
Enter client_id: alice
Enter value to add (float): 10
Total for 'alice' is now: 10.0

Enter operation (accumulate|clear or 'quit'): clear
Enter client_id to clear: alice
Cleared total for 'alice'.

Enter operation (accumulate|clear or 'quit'): quit
Goodbye!
```

## Available Operations

- `accumulate(client_id, val)`
  - Adds `val` (float) to the running total for `client_id`
  - Returns the new total
- `clear(client_id)`
  - Clears (removes) the running total for `client_id`

## Notes & Errors

- Each `client_id` has its own total; updates are independent across different IDs.
- Clearing a non-existent `client_id` return a KeyError from the server.

