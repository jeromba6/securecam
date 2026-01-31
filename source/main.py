#!/usr/bin/env python3
# Collect all camera's data in one place
# Camera's store their data on a remote server located at cams_directory
# Each camera has its own subdirectory with a prefix 'cam'

import os  # For filesystem operations
import fastapi  # FastAPI web framework
import datetime  # For date and time handling
import pytz  # For timezone handling
import json
import subprocess
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse

# Define CET timezone
CET = pytz.timezone('CET')


def init():
    """Initialize configuration from command-line arguments or environment variables."""
    cams_directory = os.environ.get("SECURECAM_DIR", "/cameras/")
    cams_prefix = os.environ.get("SECURECAM_PREFIX", "cam")
    cams_images_extentions = ['.jpg', '.jpeg', '.png']
    cams_videos_extentions = ['.mp4', '.mkv']

    return {
        'cams_directory': cams_directory,
        'cams_prefix': cams_prefix,
        'cams_images_extentions': cams_images_extentions,
        'cams_videos_extentions': cams_videos_extentions,
    }


config = init()

app = fastapi.FastAPI()
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Serve static files from the 'html' directory
app.mount("/html", StaticFiles(directory="html"), name="html")

# Serve camera data files
app.mount("/data", StaticFiles(directory=config['cams_directory']), name="data")



# Simple cache for camera data to avoid frequent disk reads
camera_data_cache: dict[str, dict] = None
camera_data_cache_time: float = 0
CACHE_TTL: int = 300  # Cache time-to-live in seconds


def main(config: dict) -> None:
    camera_data = get_all_camera_data(config)
    print(json.dumps(camera_data, indent=4))
    

def get_all_camera_data(config: dict) -> dict:
    """
    Collects and caches data for all cameras.
    Returns a dictionary mapping camera names to their data.
    """
    global camera_data_cache, camera_data_cache_time    
    now = datetime.datetime.now().timestamp()
    # Use cached data if still valid
    if camera_data_cache is not None and now - camera_data_cache_time < CACHE_TTL:
        return camera_data_cache
    camera_data = {}
    # Scan all camera directories
    for cam in os.listdir(config['cams_directory']):
        if not cam.startswith(config['cams_prefix']):
            continue
        camera_data[cam] = get_camera_data(cam, config)
    camera_data_cache = camera_data
    camera_data_cache_time = now
    return camera_data


def get_camera_data(cam: str, config: dict) -> dict:
    """
    Gathers and organizes all data for a specific camera.
    Returns a dictionary containing video and photo file mappings,
    grouped and sorted by date.
    """
    cam_path = os.path.join(config['cams_directory'], cam)
    video_files = {}
    photo_files = {}
    # Walk the camera directory tree
    for root, dirs, files in os.walk(cam_path):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, os.path.join(config['cams_directory'], cam)).replace(os.sep, '/')
            # Get mtime as UTC, then convert to CET
            mtime_utc = datetime.datetime.fromtimestamp(os.path.getmtime(full_path), datetime.timezone.utc)
            mtime_cet = mtime_utc.astimezone(CET)
            timestamp = int(mtime_cet.timestamp())
            if is_extension_in_list(file, config['cams_images_extentions']):
                photo_files[timestamp] = rel_path
                continue
            elif is_extension_in_list(file, config['cams_videos_extentions']):
                video_files[timestamp] = rel_path
                continue

    # # only return the first 10 files
    # video_files = {k: v for k, v in video_files.items() if k in sorted(video_files.keys())[:10]}
    # photo_files = {k: v for k, v in photo_files.items() if k in sorted(photo_files.keys())[:10]}    
    return {
        "videos": video_files,
        "photos": photo_files,
    }
    

def is_extension_in_list(filename, extensions):
    """Check if the file has one of the specified extensions."""
    return any(filename.lower().endswith(ext.lower()) for ext in extensions)


def get_sorted_files_by_date(data, key):
    files = [(datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d'), ts, data[key][ts]) for ts in data[key]]
    return sorted(files)

# Helper function to format timestamps in CET/CEST

def format_cet(ts):
    """Format a timestamp (seconds since epoch) as CET/CEST local time string."""
    dt_cet = datetime.datetime.fromtimestamp(ts, CET)
    return dt_cet.strftime('%Y-%m-%d'), dt_cet.strftime('%H:%M:%S')


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
    Function to serve HTML pages from the html/ directory.

    :param page_name: Description
    :type page_name: str
    """
    return get_all_camera_data(config)


@app.get("/video/{cam}/{file_path:path}")
async def stream_video(cam: str, file_path: str):
    """
    Stream video files. If it's an MKV, transcode it on the fly to MP4.
    """
    full_path = os.path.join(config['cams_directory'], cam, file_path)
    
    if not os.path.exists(full_path):
        raise fastapi.HTTPException(status_code=404, detail="Video not found")

    if full_path.lower().endswith(".mkv"):
        # Transcode MKV to MP4 on the fly
        command = [
            "ffmpeg",
            "-i", full_path,
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-tune", "zerolatency",
            "-c:a", "aac",
            "-f", "mp4",
            "-movflags", "frag_keyframe+empty_moov",
            "pipe:1"
        ]
        
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        
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
