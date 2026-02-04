# SecureCam

A modern, premium security camera monitoring dashboard with a sleek web interface and powerful backend for managing multiple camera feeds.

## Features

### 🎨 Modern Web Dashboard

- **Premium glassmorphic UI** with smooth animations and gradient accents
- **Real-time camera monitoring** with photo and video support
- **Multi-level drill-down navigation**:
  - Dashboard → Dates → Times → Media viewer
  - Cross-day and cross-hour navigation
  - Intelligent grouping (by hour when >50 items)
- **Advanced media viewer**:
  - Keyboard navigation (arrow keys, ESC)
  - Camera switching without leaving viewer
  - Media type toggle (photos ↔ videos)
  - Download support
- **Responsive design** optimized for desktop and mobile
- **Smart caching** with 30-minute expiration

### ⚡ High-Performance Backend

- **FastAPI** Python backend with async support
- **Automatic video transcoding** (MKV → MP4) via FFmpeg streaming
- **Intelligent caching** using directory mtime for change detection
- **GZip compression** for API responses
- **Timezone handling** (CET/CEST) for accurate timestamps
- **Health checks** for Kubernetes integration

### 🔒 Security & Deployment

- **Hardened container** with read-only root filesystem
- **Non-root execution** (UID 10000)
- **Kubernetes-ready** with NetworkPolicy and security contexts
- **GitHub Actions CI/CD** with automated linting and releases
- **Super-Linter** integration with Biome for code quality

## Tech Stack

### Frontend

- Vanilla JavaScript (ES6+)
- Modern CSS with custom properties
- Google Fonts (Inter)
- No external dependencies

### Backend

- Python 3.14
- FastAPI + Uvicorn
- FFmpeg (video transcoding)
- PyTZ (timezone handling)

### DevOps

- Docker (multi-stage builds)
- Kubernetes manifests
- GitHub Actions (PR checks, releases)
- Biome linter

## Quick Start

### Local Development

1. **Clone the repository**:

   ```bash
   git clone https://github.com/jeromba6/securecam.git
   cd securecam
   ```

2. **Set up Python environment**:

   ```bash
   cd source
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure camera directory**:

   ```bash
   export SECURECAM_DIR=/path/to/your/cameras
   export SECURECAM_PREFIX=cam  # Optional, default is "cam"
   ```

4. **Run the server**:

   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Open browser**: Navigate to `http://localhost:8000`

### Docker Deployment

1. **Build the image**:

   ```bash
   docker build -t securecam:latest .
   ```

2. **Run the container**:
   ```bash
   docker run -d \
     -p 8000:8000 \
     -v /path/to/cameras:/cameras:ro \
     -e SECURECAM_DIR=/cameras \
     ghcr.io/jeromba6/securecam:latest
   ```

### Kubernetes Deployment

1. **Apply the manifests**:

   ```bash
   kubectl apply -f k8s-manifests/k8s-securecam.yaml
   ```

2. **Access the dashboard**:
   - NodePort: `http://<node-ip>:30000`
   - Or configure an Ingress for your domain

## Configuration

### Environment Variables

| Variable           | Default     | Description                                     |
| ------------------ | ----------- | ----------------------------------------------- |
| `SECURECAM_DIR`    | `/cameras/` | Root directory containing camera subdirectories |
| `SECURECAM_PREFIX` | `cam`       | Prefix for camera directory names               |

### Camera Directory Structure

```
/cameras/
├── cam1/
│   ├── 2024-01-01/
│   │   ├── photo1.jpg
│   │   └── video1.mkv
│   └── 2024-01-02/
├── cam2/
│   └── ...
```

Each camera's subdirectory must start with the configured prefix (default: `cam`). The backend automatically discovers all cameras and indexes their media files.

## API Endpoints

| Endpoint              | Method | Description                        |
| --------------------- | ------ | ---------------------------------- |
| `/`                   | GET    | Redirects to dashboard             |
| `/health`             | GET    | Health check (Kubernetes probes)   |
| `/api/cameras`        | GET    | List all cameras (summary)         |
| `/api/cameras/{cam}`  | GET    | Get full data for specific camera  |
| `/video/{cam}/{path}` | GET    | Stream video (auto-transcodes MKV) |
| `/data/{cam}/{path}`  | GET    | Serve static media files           |

## Development

### Linting

The project uses [Biome](https://biomejs.dev/) for linting and formatting:

```bash
# Install Biome
npm install -g @biomejs/biome

# Lint files
biome check source/html/

# Auto-fix issues
biome check --write source/html/
```

### GitHub Actions

- **PR Checks**: Runs Super-Linter on every pull request
- **Release Workflow**: Builds and publishes Docker images on semantic version tags

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run linters: `biome check --write .`
5. Submit a pull request

## License

This project is private and proprietary.

## Acknowledgments

- Built with ❤️ using modern web technologies
- Inspired by the need for elegant security camera monitoring
