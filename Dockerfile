# Use official Python image
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install flask pytz

# Copy project files
COPY main.py ./

# Expose port
EXPOSE 5000

# Set default cams_directory (can be overridden)
ENV SECURECAM_DIR=/data/securecam

# Run the Flask app
CMD ["python", "main.py"]
