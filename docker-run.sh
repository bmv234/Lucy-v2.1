#!/bin/bash

# Stop and remove any existing container
docker stop lucy-app 2>/dev/null
docker rm lucy-app 2>/dev/null

# Build and run the container
docker build -t lucy-app .
docker run -d --name lucy-app \
    --gpus all \
    --ipc=host \
    --ulimit memlock=-1 \
    --ulimit stack=67108864 \
    -p 5000:5000 \
    -p 8443:8443 \
    -p 5050:5050 \
    lucy-app
