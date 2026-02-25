FROM python:3.11-slim

# Install dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    wget \
    tar \
    xz-utils \
    libavahi-client3 \
    libavahi-common3 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Download and install static FFmpeg binary
# Use || true to ignore tar permission errors on QNAP filesystem
RUN wget -q https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz -O /tmp/ffmpeg.tar.xz && \
    cd /tmp && \
    tar -xf ffmpeg.tar.xz 2>/dev/null || true && \
    find /tmp -name "ffmpeg" -type f -executable -exec cp {} /usr/local/bin/ffmpeg \; && \
    find /tmp -name "ffprobe" -type f -executable -exec cp {} /usr/local/bin/ffprobe \; && \
    chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe && \
    rm -rf /tmp/*

# Verify FFmpeg installed
RUN ffmpeg -version

# Install NDI SDK
WORKDIR /tmp
COPY install_ndi.sh /tmp/
RUN chmod +x /tmp/install_ndi.sh && /tmp/install_ndi.sh

ENV LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

# Install Python dependencies
WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir schedule Pillow numpy

# Copy application
COPY capture_construction.py /app/

# Create directories
RUN mkdir -p /output /logs

CMD python -u capture_construction.py
