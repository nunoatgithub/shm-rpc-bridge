# Calculator RPC Example

This directory contains a complete example of using the shm-rpc-bridge library
to implement a calculator service with RPC over shared memory.

## Files

- `calculator_server.py` - The calculator server that provides arithmetic operations
- `calculator_client.py` - The client that calls the calculator operations

## Running the Example

### 1. Start the Server

In one terminal:

```bash
python examples/calculator_server.py
```

The server will start and wait for requests. You should see:

```
Starting Calculator RPC Server...
Channel: calculator_rpc
Registered methods: add, subtract, multiply, divide, power, sqrt
Server ready! Waiting for requests...
Press Ctrl+C to stop.
```

### 2. Run the Client

In another terminal:

#### Demo Mode (default)

Run a pre-programmed demonstration of all calculator features:

```bash
python examples/calculator_client.py
```

#### Interactive Mode

Use the calculator interactively:

```bash
python examples/calculator_client.py --interactive
```

Then you can perform calculations like:

```
Enter operation (or 'quit'): add
Enter first number: 10
Enter second number: 5
Result: 15.0

Enter operation (or 'quit'): sqrt
Enter number: 16
Result: 4.0

Enter operation (or 'quit'): quit
Goodbye!
```

## Available Operations

The calculator supports the following operations:

- `add(a, b)` - Add two numbers
- `subtract(a, b)` - Subtract b from a
- `multiply(a, b)` - Multiply two numbers
- `divide(a, b)` - Divide a by b (raises error if b is zero)
- `power(base, exponent)` - Raise base to the power of exponent
- `sqrt(x)` - Calculate square root (raises error if x is negative)

## Error Handling

The example demonstrates proper error handling:

- Division by zero returns an error
- Square root of negative numbers returns an error
- Connection timeouts are handled gracefully

