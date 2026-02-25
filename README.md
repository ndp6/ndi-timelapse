# NDI Construction Timelapse

A Docker-based timelapse capture system that records frames from NDI video sources at scheduled intervals. Perfect for construction site monitoring, long-term project documentation, or any scenario requiring automated periodic image capture from NDI-enabled cameras.

## Features

- 📷 **Automated frame capture** from NDI video sources at configurable intervals
- 🕐 **Scheduled operation** with configurable active hours (e.g., daylight only)
- 📁 **Organized output** with daily folders (`YYYY-MM-DD/frame_YYYYMMDD_HHMMSS.jpg`)
- 🎯 **Specific frame selection** - extract any frame number from the recording
- 🐳 **Fully containerized** with Docker for easy deployment
- ⚙️ **Highly configurable** via environment variables

## Prerequisites

- Docker and Docker Compose
- NDI-enabled camera or video source on your network
- NDI SDK (automatically downloaded during Docker build)

## Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/ndi-construction-timelapse.git
   cd ndi-construction-timelapse
   ```

2. **Configure your settings** in `docker-compose.yml`:
   ```yaml
   environment:
     - NDI_SOURCE_NAME=Your-Camera-Name (CAM)
     - NDI_SOURCE_URL=192.168.1.100:5961
     - CAPTURE_INTERVAL=15
   ```

3. **Build and run:**
   ```bash
   docker compose up -d
   ```

4. **Check the logs:**
   ```bash
   docker logs -f construction-timelapse
   ```

## Configuration

All settings are configured via environment variables in `docker-compose.yml`:

| Variable | Default | Description |
|----------|---------|-------------|
| `NDI_SOURCE_NAME` | `Your-Camera-Name (CAM)` | Name of the NDI source to capture from |
| `NDI_SOURCE_URL` | `192.168.1.100:5961` | Direct URL to the NDI source |
| `CAPTURE_INTERVAL` | `15` | Minutes between captures |
| `START_HOUR` | `5` | Hour to start capturing (24h format) |
| `END_HOUR` | `21` | Hour to stop capturing (24h format) |
| `RECORD_SECONDS` | `5` | Duration to record for each capture |
| `JPEG_QUALITY` | `95` | JPEG quality (1-100) |
| `FRAME_NUMBER` | `120` | Which frame to extract from recording |
| `OUTPUT_DIR` | `/output` | Output directory inside container |
| `LOG_DIR` | `/logs` | Log directory inside container |
| `TZ` | `America/New_York` | Timezone for scheduling |

## Finding Your NDI Source

To discover NDI sources on your network, you can use NDI Tools or run:

```bash
docker exec -it construction-timelapse /usr/local/bin/ndi-record --help
```

The `NDI_SOURCE_NAME` should match exactly what appears in NDI discovery, and `NDI_SOURCE_URL` is the IP:port of your NDI source.

## Directory Structure

```
ndi-construction-timelapse/
├── Dockerfile
├── docker-compose.yml
├── capture_construction.py
├── install_ndi.sh
├── requirements.txt
├── README.md
└── LICENSE
```

## Output Structure

Captured images are organized by date:

```
/output/
├── 2026-02-24/
│   ├── frame_20260224_080000.jpg
│   ├── frame_20260224_081500.jpg
│   └── ...
├── 2026-02-25/
│   └── ...
```

## Creating a Timelapse Video

Once you have captured enough frames, create a timelapse video using FFmpeg:

```bash
# Basic timelapse at 30fps
ffmpeg -framerate 30 -pattern_type glob -i '/path/to/output/2026-02-*/*.jpg' \
  -c:v libx264 -pix_fmt yuv420p timelapse.mp4

# Higher quality with specific dates
ffmpeg -framerate 24 -pattern_type glob -i '/path/to/output/2026-02-24/*.jpg' \
  -c:v libx264 -crf 18 -pix_fmt yuv420p timelapse_feb24.mp4
```

## Docker Compose Example

```yaml
version: '3.8'

services:
  ndi-timelapse:
    build: .
    container_name: construction-timelapse
    restart: unless-stopped
    network_mode: host
    tty: true
    stdin_open: true
    environment:
      - TZ=America/New_York
      - NDI_SOURCE_NAME=Your-Camera-Name (CAM)
      - NDI_SOURCE_URL=192.168.1.100:5961
      - CAPTURE_INTERVAL=15
      - START_HOUR=6
      - END_HOUR=20
      - RECORD_SECONDS=5
      - JPEG_QUALITY=95
      - FRAME_NUMBER=120
      - OUTPUT_DIR=/output
      - LOG_DIR=/logs
    volumes:
      - /path/to/your/timelapse/storage:/output
      - ./logs:/logs
```

## Technical Notes

### Why PTY is Required

The `ndi-record` binary from the NDI SDK requires a pseudo-terminal (PTY) to function properly. This is why the Docker container uses `tty: true` and the Python script creates a PTY for the subprocess.

### Signal Handling

The script sends `SIGINT` (equivalent to Ctrl+C) to gracefully stop `ndi-record`, which ensures the MOV file is properly finalized with correct headers. Using `SIGTERM` or `SIGKILL` can result in corrupted files.

### Frame Extraction

FFmpeg extracts a specific frame from the recorded MOV file. Frame 120 (at 60fps) is approximately 2 seconds into the recording, which typically provides a cleaner image than the first frame.

## Troubleshooting

### "Recording file not created"
- Verify `NDI_SOURCE_NAME` and `NDI_SOURCE_URL` are correct
- Ensure the NDI source is accessible from the Docker host
- Check that `network_mode: host` is set in docker-compose.yml

### "moov atom not found" / Corrupted MOV files
- Ensure `tty: true` is set in docker-compose.yml
- The script should be using PTY (`pty.openpty()`)
- SIGINT should be sent before SIGTERM

### "FFmpeg failed"
- Verify FFmpeg is installed in the container
- Check that `RECORD_SECONDS` is long enough to capture `FRAME_NUMBER` frames
- At 60fps, frame 120 requires at least 2 seconds of recording

### Container exits immediately
- Check for syntax errors in the Python script
- Ensure `tty: true` and `stdin_open: true` are set

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## NDI SDK Notice

This project uses the NDI® SDK from Vizrt NDI AB. The NDI SDK is subject to its own license agreement. By using this project, you agree to comply with the [NDI SDK License Agreement](https://ndi.video/sdk/).

NDI® is a registered trademark of Vizrt NDI AB.

**Note:** The NDI SDK binaries are not included in this repository. They are downloaded and installed during the Docker build process, and you must accept the NDI SDK license agreement.

## Acknowledgments

- [NDI® by Vizrt](https://ndi.video/) for the NDI SDK
- [FFmpeg](https://ffmpeg.org/) for video processing

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request
