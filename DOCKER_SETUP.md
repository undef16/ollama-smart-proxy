# Docker Setup for Ollama Smart Proxy

This document provides instructions for setting up and running the Ollama Smart Proxy with Docker and Docker Compose.

## Prerequisites

Before running the Docker setup, ensure you have the following installed:

- Docker Engine (version 20.10 or higher)
- Docker Compose (version 2.0 or higher)

### Installing Docker

For Windows:
1. Download Docker Desktop from [Docker's official website](https://www.docker.com/products/docker-desktop)
2. Follow the installation instructions
3. Restart your computer if required

## Services Configuration

The Docker Compose setup includes the following services:

- **ollama-smart-proxy**: Main application service (port 11555)
- **Redis**: In-memory data store (port 6379)
- **Neo4j**: Graph database (ports 7474, 7687)
- **PostgreSQL**: Relational database with vector extensions (port 5432)
- **SearXNG**: Privacy-respecting search engine (port 8080)

## Running the Application

### 1. Build and Start Services

To build and start all services:

```bash
cd ollama-smart-proxy
docker compose up --build
```

### 2. Start Services in Background

To run services in the background:

```bash
docker compose up --build -d
```

### 3. View Logs

To view logs from all services:

```bash
docker compose logs -f
```

### 4. Stop Services

To stop all services:

```bash
docker compose down
```

To stop services and remove volumes (data will be lost):

```bash
docker compose down -v
```

## Configuration

### Environment Variables

The application uses the following environment variables:

- `OLLAMA_PROXY_SERVER_HOST`: Server host (default: 0.0.0.0)
- `OLLAMA_PROXY_SERVER_PORT`: Server port (default: 11555)
- `OLLAMA_PROXY_REDIS_URL`: Redis connection URL
- `OLLAMA_PROXY_NEO4J_URI`: Neo4j connection URI
- `OLLAMA_PROXY_NEO4J_USER`: Neo4j username
- `OLLAMA_PROXY_NEO4J_PASSWORD`: Neo4j password
- `OLLAMA_PROXY_POSTGRES_URI`: PostgreSQL connection URI
- `OLLAMA_PROXY_SEARXNG_URL`: SearXNG service URL

### Volumes

The setup includes persistent volumes for data storage:

- `redis_data`: Redis data persistence
- `neo4j_data`: Neo4j database files
- `neo4j_logs`: Neo4j log files
- `neo4j_import`: Neo4j import directory
- `postgres_data`: PostgreSQL data files
- `searxng_data`: SearXNG configuration

### Network

All services communicate through an internal network named `app-network`.

## Accessing Services

After starting the services, you can access them at:

- **Ollama Smart Proxy**: http://localhost:11555
- **Neo4j Browser**: http://localhost:7474
- **PostgreSQL**: localhost:5432 (use a PostgreSQL client)
- **SearXNG**: http://localhost:8080

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   - Ensure no other services are running on the same ports
   - Check with `netstat -an | findstr :<port_number>`

2. **Docker Build Failures**
   - Ensure you have a stable internet connection
   - Check if your system meets the minimum requirements

3. **Service Health Checks Failing**
   - Wait for services to fully start (especially databases)
   - Check logs with `docker compose logs <service_name>`

### Useful Commands

```bash
# Check running containers
docker compose ps

# Execute commands in a specific container
docker compose exec <service_name> <command>

# Example: Connect to PostgreSQL
docker compose exec postgres psql -U postgres

# Check resource usage
docker stats

# Remove unused Docker objects
docker system prune
```

## Development

For development purposes, you can mount your local code directory to the container by modifying the `volumes` section in the `docker compose.yml` file:

```yaml
ollama-smart-proxy:
  # ... other configuration
  volumes:
    - .:/app  # Mounts the current directory to /app in the container
    - ./config.json:/app/config.json
    - ./src/plugins:/app/src/plugins
```

**Note**: This enables live reloading but may impact performance.

## Production Considerations

For production deployments, consider the following:

1. **Security**:
   - Change default passwords
   - Use environment files for sensitive data
   - Implement SSL/TLS certificates

2. **Performance**:
   - Configure resource limits
   - Set up monitoring and logging
   - Optimize database configurations

3. **Backup**:
   - Regularly backup volumes
   - Implement disaster recovery procedures

## GPU Acceleration with CUDA

The Ollama service in this setup can be configured to use NVIDIA GPU acceleration for faster inference.
The docker compose.yml file has been configured with CUDA support for the Ollama service:

- Runtime set to `nvidia` for GPU access
- Environment variable `NVIDIA_VISIBLE_DEVICES=all` to expose all GPUs
- Proper health checks and networking configuration maintained

### Prerequisites

Before running the Docker Compose setup with GPU support, ensure you have:

1. **NVIDIA GPU** with CUDA support
2. **NVIDIA Drivers** installed on your host system
3. **NVIDIA Container Toolkit** installed and configured for Docker

### Installing NVIDIA Container Toolkit

For detailed installation instructions, see the official documentation: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html

#### Ubuntu/Debian:
```bash
# Add the repository
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Update and install
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
```

#### Configure Docker
After installing the NVIDIA Container Toolkit, configure Docker to use the NVIDIA runtime:

```bash
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### Verification

Verify that your Docker installation can access the GPU:

```bash
docker run --rm --gpus all nvidia/cuda:1.0.3-base-ubuntu20.04 nvidia-smi
```

### Running with GPU Support

Start the services with GPU support:

```bash
docker compose up -d
```

For more detailed information about CUDA setup and troubleshooting, see [DOCKER_CUDA_SETUP.md](./DOCKER_CUDA_SETUP.md).