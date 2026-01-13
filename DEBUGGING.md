# Debugging main.py in Docker Container

This guide explains how to debug the `main.py` file in the Docker container named "proxy" using VS Code.

## Prerequisites

1. VS Code with the "Python" extension installed
2. Docker and Docker Compose installed and running

## Steps to Debug

### 1. Build and Start the Container

```bash
docker compose up --build
```

Wait for the container to start. You should see the message "Waiting for debugger to attach on port 5678..." in the logs.

### 2. Attach VS Code Debugger

1. Open this project in VS Code
2. Go to the "Run and Debug" view (Ctrl+Shift+D)
3. Select "Python: Remote Attach to Docker" from the dropdown
4. Click the green play button or press F5
5. The debugger will attach to your running container

### 3. Set Breakpoints and Debug

- Set breakpoints in your VS Code editor by clicking on line numbers
- The code will pause at breakpoints when hit
- You can inspect variables, step through code, etc.

## Alternative: Using Interactive Debugging

If you prefer to use interactive debugging (pdb), you can temporarily modify the main.py to use pdb instead:

```python
if __name__ == "__main__":
    import uvicorn
    
    # For interactive debugging, uncomment the next line
    # import pdb; pdb.set_trace()
    
    server_config = Config()
    uvicorn.run(
        app,
        host=server_config.server_host,
        port=server_config.server_port,
        reload=reload_option  # Only enable hot reloading when not in Docker and in debug mode
    )
```

Then run:
```bash
docker compose up --build
```

This will start an interactive debugging session in the container's terminal.

## Troubleshooting

1. If the debugger doesn't connect, make sure port 5678 is available
2. Check that the container is running: `docker ps`
3. Make sure the Python extension is installed and configured in VS Code
4. If you get import errors, ensure debugpy is installed in the container by checking the Dockerfile

## Stopping Debug Session

1. To stop debugging, press Ctrl+C in the terminal where docker-compose is running
2. Or run `docker compose down` in another terminal