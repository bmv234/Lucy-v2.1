# Use the latest NVIDIA CUDA image as the base image
FROM nvidia/cuda:12.6.1-cudnn-devel-ubuntu24.04

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    zlib1g-dev \
    libncurses5-dev \
    libgdbm-dev \
    libnss3-dev \
    libssl-dev \
    libreadline-dev \
    libffi-dev \
    libsqlite3-dev \
    libbz2-dev \
    wget \
    openssl \
    mecab \
    libmecab-dev \
    mecab-ipadic-utf8 \
    && rm -rf /var/lib/apt/lists/*

# Download and build Python 3.10.12 from source
WORKDIR /tmp
RUN wget https://www.python.org/ftp/python/3.10.12/Python-3.10.12.tgz \
    && tar xzf Python-3.10.12.tgz \
    && cd Python-3.10.12 \
    && ./configure --enable-optimizations \
    && make -j $(nproc) \
    && make install \
    && cd .. \
    && rm -rf Python-3.10.12 Python-3.10.12.tgz

# Ensure pip is installed and updated
RUN python3 -m ensurepip
RUN python3 -m pip install --no-cache-dir --upgrade pip

# Set Python 3.10 as default
RUN update-alternatives --install /usr/bin/python python /usr/local/bin/python3 1
RUN update-alternatives --install /usr/bin/python3 python3 /usr/local/bin/python3 1

# Verify Python version
RUN python3 --version | grep -q "Python 3.10.12" || (echo "Wrong Python version installed" && exit 1)
RUN python --version | grep -q "Python 3.10.12" || (echo "Wrong Python version installed" && exit 1)

WORKDIR /app

# Copy main app requirements and install dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy Melo-TTS-API-Server requirements and install dependencies
COPY Melo-TTS-API-Server/requirements.txt ./melo_requirements.txt
RUN pip3 install --no-cache-dir -r melo_requirements.txt

# Copy all application files
COPY . .

# Generate SSL certificates
RUN openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/CN=localhost"

# Create startup script
RUN echo '#!/bin/bash\n\
# Start Melo-TTS-API-Server\n\
cd /app/Melo-TTS-API-Server\n\
MECAB_SKIP=1 python server.py &\n\
\n\
# Start main application\n\
cd /app\n\
python run.py\n\
\n\
# Wait for any process to exit\n\
wait -n\n\
\n\
# Exit with status of process that exited first\n\
exit $?' > /app/start.sh && chmod +x /app/start.sh

# Expose ports
EXPOSE 6000 9765 6050

# Run the startup script
CMD ["/app/start.sh"]
