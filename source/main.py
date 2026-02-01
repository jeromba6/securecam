#!/usr/bin/env python3
# Collect all camera's data in one place
# Camera's store their data on a remote server located at cams_directory
# Each camera has its own subdirectory with a prefix 'cam'

import datetime  # For date and time handling
import json
import os  # For filesystem operations
import subprocess

import fastapi  # FastAPI web framework
import pytz  # For timezone handling
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

# Define CET timezone
CET = pytz.timezone("CET")


def init():
    """Initialize configuration from command-line arguments or environment variables."""
    cams_directory = os.environ.get("SECURECAM_DIR", "/cameras/")
    cams_prefix = os.environ.get("SECURECAM_PREFIX", "cam")
    cams_images_extentions = [".jpg", ".jpeg", ".png"]
    cams_videos_extentions = [".mp4", ".mkv"]

    return {
        "cams_directory": cams_directory,
        "cams_prefix": cams_prefix,
        "cams_images_extentions": cams_images_extentions,
        "cams_videos_extentions": cams_videos_extentions,
    }


config = init()

app = fastapi.FastAPI()
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Serve static files from the 'html' directory
app.mount("/html", StaticFiles(directory="html"), name="html")

# Serve camera data files
app.mount("/data", StaticFiles(directory=config["cams_directory"]), name="data")


def main(config: dict) -> None:
    camera_data = get_all_camera_data(config)
    print(json.dumps(camera_data, indent=4))


# Sophisticated per-camera cache
# Structure: { cam_name: { 'mtime': float, 'data': dict } }
camera_data_cache: dict[str, dict] = {}


def get_all_camera_data(config: dict, summary_only: bool = False) -> dict:
    """
    Collects data for all cameras. If summary_only is True, returns only
    camera names and file counts.
    """
    cameras = [
        d
        for d in os.listdir(config["cams_directory"])
        if d.startswith(config["cams_prefix"])
    ]
    results = {}

    for cam in cameras:
        cam_data = get_camera_data(cam, config)
        if summary_only:
            results[cam] = {
                "photos_count": len(cam_data["photos"]),
                "videos_count": len(cam_data["videos"]),
            }
        else:
            results[cam] = cam_data

    return results


def get_camera_data(cam: str, config: dict) -> dict:
    """
    Gathers and organizes data for a specific camera with smart caching.
    The cache is only invalidated if the camera directory's mtime changes.
    """
    cam_path = os.path.join(config["cams_directory"], cam)
    if not os.path.isdir(cam_path):
        return {"videos": {}, "photos": {}}

    # Check directory mtime for change detection
    current_mtime = os.path.getmtime(cam_path)
    cached = camera_data_cache.get(cam)

    if cached and cached["mtime"] == current_mtime:
        return cached["data"]

    video_files = {}
    photo_files = {}

    # Walk the camera directory tree
    for root, _, files in os.walk(cam_path):
        for file in files:
            full_path = os.path.join(root, file)
            # Use relative path from the camera root for internal mapping
            rel_path = os.path.relpath(full_path, cam_path).replace(os.sep, "/")

            # Get mtime as UTC, then convert to CET
            mtime_ts = os.path.getmtime(full_path)
            # Optimization: only compute timezone if needed for indexing,
            # but we need it for all to sort correctly later
            mtime_utc = datetime.datetime.fromtimestamp(mtime_ts, datetime.timezone.utc)
            mtime_cet = mtime_utc.astimezone(CET)
            timestamp = int(mtime_cet.timestamp())

            if is_extension_in_list(file, config["cams_images_extentions"]):
                photo_files[timestamp] = rel_path
            elif is_extension_in_list(file, config["cams_videos_extentions"]):
                video_files[timestamp] = rel_path

    data = {
        "videos": video_files,
        "photos": photo_files,
    }

    # Store in cache
    camera_data_cache[cam] = {"mtime": current_mtime, "data": data}

    return data


def is_extension_in_list(filename, extensions):
    """Check if the file has one of the specified extensions."""
    return any(filename.lower().endswith(ext.lower()) for ext in extensions)


def get_sorted_files_by_date(data, key):
    files = [
        (datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d"), ts, data[key][ts])
        for ts in data[key]
    ]
    return sorted(files)


# Helper function to format timestamps in CET/CEST


def format_cet(ts):
    """Format a timestamp (seconds since epoch) as CET/CEST local time string."""
    dt_cet = datetime.datetime.fromtimestamp(ts, CET)
    return dt_cet.strftime("%Y-%m-%d"), dt_cet.strftime("%H:%M:%S")


@app.get("/health")
async def health_check() -> dict:
    """
    Health check endpoint for Kubernetes liveness and readiness probes.
    Includes diagnostic info about the cameras directory.
    """
    cams_dir = config.get("cams_directory", "")
    exists = os.path.exists(cams_dir)
    readable = os.access(cams_dir, os.R_OK) if exists else False

    return {
        "status": "ok" if readable else "degraded",
        "details": {
            "cams_directory": cams_dir,
            "exists": exists,
            "readable": readable,
            "files_found": len(os.listdir(cams_dir)) if readable else 0,
        },
    }


@app.get("/")
async def root() -> fastapi.responses.RedirectResponse:
    """
    Function to redirect to the main HTML dashboard page.
    """

    return fastapi.responses.RedirectResponse(url="/html/index.html")


@app.get("/html/")
async def html_root() -> fastapi.responses.RedirectResponse:
    """
    Function to redirect to the main HTML dashboard page.
    """

    return fastapi.responses.RedirectResponse(url="/html/index.html")


@app.get("/api/cameras")
async def get_cameras() -> dict:
    """
    Returns a summary of all cameras (names and counts).
    """
    return get_all_camera_data(config, summary_only=True)


@app.get("/api/cameras/{cam}")
async def get_camera_details(cam: str) -> dict:
    """
    Returns full recording data for a specific camera.
    """
    if not cam.startswith(config["cams_prefix"]):
        raise fastapi.HTTPException(status_code=400, detail="Invalid camera name")

    cam_path = os.path.join(config["cams_directory"], cam)
    if not os.path.exists(cam_path):
        raise fastapi.HTTPException(status_code=404, detail="Camera not found")

    return get_camera_data(cam, config)


@app.get("/video/{cam}/{file_path:path}")
async def stream_video(cam: str, file_path: str):
    """
    Stream video files. If it's an MKV, transcode it on the fly to MP4.
    """
    full_path = os.path.join(config["cams_directory"], cam, file_path)

    if not os.path.exists(full_path):
        raise fastapi.HTTPException(status_code=404, detail="Video not found")

    if full_path.lower().endswith(".mkv"):
        # Transcode MKV to MP4 on the fly
        command = [
            "ffmpeg",
            "-i",
            full_path,
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-tune",
            "zerolatency",
            "-c:a",
            "aac",
            "-f",
            "mp4",
            "-movflags",
            "frag_keyframe+empty_moov",
            "pipe:1",
        ]

        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )

        def iterfile():
            try:
                while True:
                    data = process.stdout.read(4096)
                    if not data:
                        break
                    yield data
            finally:
                process.terminate()

        return StreamingResponse(iterfile(), media_type="video/mp4")

    # For other formats (like MP4), just serve the file
    return fastapi.responses.FileResponse(full_path)


if __name__ == "__main__":
    main(config)
