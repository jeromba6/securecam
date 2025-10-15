# Collect all camera's data in one place
# Camera's store their data on a remote server located at cams_directory
# Each camera has its own subdirectory with a prefix 'cam'

import os  # For filesystem operations
import flask  # Flask web framework
import datetime  # For date and time handling
import sys  # For sys.argv (ensure this is only imported once)
import pytz  # For timezone handling
import argparse  # For command-line argument parsing

# Path to the directory containing all camera subdirectories
cams_directory: str               = ""
cams_prefix: str                  = ""
cams_images_extentions: list[str] = []
cams_videos_extentions: list[str] = []
debug: bool                       = False
port: int                         = 5000

app = flask.Flask(__name__)

# Simple cache for camera data to avoid frequent disk reads
camera_data_cache: dict[str, dict] = None
camera_data_cache_time: float = 0
CACHE_TTL: int = 300  # Cache time-to-live in seconds

# Define CET timezone
CET = pytz.timezone('CET')


def init():
    """Initialize configuration from command-line arguments or environment variables."""
    global cams_directory, cams_prefix, cams_images_extentions, cams_videos_extentions, debug, port
    parser = argparse.ArgumentParser(description="SecureCam Web Interface")
    parser.add_argument(
        '-d', '--dir', 
        type=str, 
        default=os.environ.get("SECURECAM_DIR", "/cameras/"), 
        help='Directory containing camera subdirectories')
    parser.add_argument(
        '-p','--prefix',
        type=str,
        default=os.environ.get("SECURECAM_PREFIX", "cam"),
        help='Prefix for camera directories')
    parser.add_argument(
        '-i', '--images-extensions',
        type=str,
        nargs='+',
        default=['.jpg', '.jpeg', '.png'],
        help='List of image file extensions')
    parser.add_argument(
        '-v', '--videos-extensions',
        type=str,
        nargs='+',
        default=['.mp4', '.mkv'],
        help='List of video file extensions')
    parser.add_argument(
        '-D', '--debug',
        action='store_true',
        default=False,
        help='Enable debug mode')
    parser.add_argument(
        '-P', '--port',
        type=int,
        default=5000,
        help='Port to run the web server on')
    args = parser.parse_args()

    cams_directory         = args.dir
    cams_prefix            = args.prefix
    cams_images_extentions = args.images_extensions
    cams_videos_extentions = args.videos_extensions
    debug                  = args.debug
    port                   = args.port


def get_all_camera_data():
    """
    Collects and caches data for all cameras.
    Returns a dictionary mapping camera names to their data.
    """
    global cams_directory, cams_prefix, camera_data_cache, camera_data_cache_time
    now = datetime.datetime.now().timestamp()
    # Use cached data if still valid
    if camera_data_cache is not None and now - camera_data_cache_time < CACHE_TTL:
        return camera_data_cache
    camera_data = {}
    # Scan all camera directories
    for cam in os.listdir(cams_directory):
        if not cam.startswith(cams_prefix):
            continue
        camera_data[cam] = get_camera_data(cam)
    camera_data_cache = camera_data
    camera_data_cache_time = now
    return camera_data


# Home page: lists all available cameras
@app.route('/')
def index():
        cameras = sorted([cam for cam in get_all_camera_data().keys()])
        camera_list_html = "<ul>" + "".join(f'<li><a href="/camera/{cam}">{cam}</a></li>' for cam in cameras) + "</ul>"
        return f"""
<!DOCTYPE html>
<html lang='en'>
    <head>
        <meta charset='utf-8'>
        <meta name='viewport' content='width=device-width, initial-scale=1'>
        <title>Available Cameras</title>
        <style>
            body {{ font-family: system-ui, sans-serif; margin: 0; padding: 1em; background: #f8f9fa; }}
            h1 {{ font-size: 1.7em; margin-bottom: 0.7em; }}
            ul {{ padding: 0; list-style: none; }}
            li {{ margin: 0.7em 0; }}
            a {{ color: #1565c0; text-decoration: none; font-size: 1.2em; }}
            a:hover {{ text-decoration: underline; }}
            @media (max-width: 600px) {{
                h1 {{ font-size: 1.2em; }}
                a {{ font-size: 1em; }}
            }}
        </style>
    </head>
    <body>
        <h1>Available Cameras</h1>
        {camera_list_html}
    </body>
</html>
        """

# Camera details page: shows stats and available dates
@app.route('/camera/<cam_name>')
def camera_detail(cam_name):
    if not cam_name.startswith("cam"):
        return "Invalid camera name", 404
    all_data = get_all_camera_data()
    if cam_name not in all_data:
        return "Camera not found", 404
    data = all_data[cam_name]
    # Count files per date (photos + videos)
    date_counts = {}
    for ts in list(data['videos'].keys()) + list(data['photos'].keys()):
        date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
        date_counts[date] = date_counts.get(date, 0) + 1
        dates = sorted(date_counts.keys())
        dates_html = "<ul>" + "".join(f"<li>{date} ({date_counts[date]})</li>" for date in dates) + "</ul>"
        num_videos = len(data['videos'])
        num_photos = len(data['photos'])
        return f"""
<!DOCTYPE html>
<html lang='en'>
    <head>
        <meta charset='utf-8'>
        <meta name='viewport' content='width=device-width, initial-scale=1'>
        <title>{cam_name} Details</title>
        <style>
            body {{ font-family: system-ui, sans-serif; margin: 0; padding: 1em; background: #f8f9fa; }}
            h1 {{ font-size: 1.5em; margin-bottom: 0.5em; }}
            h2 {{ font-size: 1.1em; margin-top: 1.5em; }}
            ul {{ padding: 0; list-style: none; }}
            li {{ margin: 0.5em 0; }}
            a {{ color: #1565c0; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            p {{ margin: 0.5em 0; }}
            @media (max-width: 600px) {{
                h1 {{ font-size: 1.1em; }}
                h2 {{ font-size: 1em; }}
            }}
        </style>
    </head>
    <body>
        <a href='/'>Back to camera list</a>
        <h1>{cam_name}</h1>
        <p>Videos: <a href='/camera/{cam_name}/videos'>{num_videos}</a></p>
        <p>Photos: <a href='/camera/{cam_name}/photos'>{num_photos}</a></p>
        <h2>Available Dates</h2>
        {dates_html}
    </body>
</html>
        """

# Video date list: shows all dates with videos for a camera
@app.route('/camera/<cam_name>/videos')
def camera_videos_dates(cam_name):
    if not cam_name.startswith("cam"):
        return "Invalid camera name", 404
    data = get_all_camera_data()[cam_name]
    # Count videos per date
    date_counts = {}
    for ts in data['videos']:
        date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
        date_counts[date] = date_counts.get(date, 0) + 1
        video_dates = sorted(date_counts.keys())
        dates_html = "<ul>" + "".join(f"<li><a href='/camera/{cam_name}/videos/{date}'>{date}</a> ({date_counts[date]})</li>" for date in video_dates) + "</ul>"
        return f"""
<!DOCTYPE html>
<html lang='en'>
    <head>
        <meta charset='utf-8'>
        <meta name='viewport' content='width=device-width, initial-scale=1'>
        <title>{cam_name} Video Dates</title>
        <style>
            body {{ font-family: system-ui, sans-serif; margin: 0; padding: 1em; background: #f8f9fa; }}
            h1 {{ font-size: 1.3em; margin-bottom: 0.7em; }}
            ul {{ padding: 0; list-style: none; }}
            li {{ margin: 0.5em 0; }}
            a {{ color: #1565c0; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            @media (max-width: 600px) {{
                h1 {{ font-size: 1em; }}
            }}
        </style>
    </head>
    <body>
        <a href='/camera/{cam_name}'>Back to camera details</a>
        <a href='/'>Back to camera list</a>
        <h1>{cam_name} - Video Dates</h1>
        {dates_html}
    </body>
</html>
        """

# Video file list for a specific date
@app.route('/camera/<cam_name>/videos/<date>')
def camera_videos_files(cam_name, date):
    if not cam_name.startswith("cam"):
        return "Invalid camera name", 404
    data = get_all_camera_data()[cam_name]
    files = sorted([(ts, data['videos'][ts]) for ts in data['videos'] if datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d') == date])
    files_html = "<ul>" + "".join(f"<li><a href='/camera/{cam_name}/videos/{date}/{idx}'>{datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')}</a></li>" for idx, (ts, file) in enumerate(files)) + "</ul>"
    return f"""
<!DOCTYPE html>
<html lang='en'>
    <head>
        <meta charset='utf-8'>
        <meta name='viewport' content='width=device-width, initial-scale=1'>
        <title>{cam_name} Videos on {date}</title>
        <style>
            body {{ font-family: system-ui, sans-serif; margin: 0; padding: 1em; background: #f8f9fa; }}
            h1 {{ font-size: 1.2em; margin-bottom: 0.7em; }}
            ul {{ padding: 0; list-style: none; }}
            li {{ margin: 0.5em 0; }}
            a {{ color: #1565c0; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            @media (max-width: 600px) {{
                h1 {{ font-size: 1em; }}
            }}
        </style>
    </head>
    <body>
        <a href='/camera/{cam_name}/videos'>Back to video dates</a>
        <a href='/camera/{cam_name}'>Back to camera details</a>
        <a href='/'>Back to camera list</a>
        <h1>{cam_name} - Videos on {date}</h1>
        {files_html}
    </body>
</html>
        """

# Photo date list: shows all dates with photos for a camera
@app.route('/camera/<cam_name>/photos')
def camera_photos_dates(cam_name):
    if not cam_name.startswith("cam"):
        return "Invalid camera name", 404
    data = get_all_camera_data()[cam_name]
    # Count photos per date
    date_counts = {}
    for ts in data['photos']:
        date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
        date_counts[date] = date_counts.get(date, 0) + 1
        photo_dates = sorted(date_counts.keys())
        dates_html = "<ul>" + "".join(f"<li><a href='/camera/{cam_name}/photos/{date}'>{date}</a> ({date_counts[date]})</li>" for date in photo_dates) + "</ul>"
        return f"""
<!DOCTYPE html>
<html lang='en'>
    <head>
        <meta charset='utf-8'>
        <meta name='viewport' content='width=device-width, initial-scale=1'>
        <title>{cam_name} Photo Dates</title>
        <style>
            body {{ font-family: system-ui, sans-serif; margin: 0; padding: 1em; background: #f8f9fa; }}
            h1 {{ font-size: 1.3em; margin-bottom: 0.7em; }}
            ul {{ padding: 0; list-style: none; }}
            li {{ margin: 0.5em 0; }}
            a {{ color: #1565c0; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            @media (max-width: 600px) {{
                h1 {{ font-size: 1em; }}
            }}
        </style>
    </head>
    <body>
        <a href='/camera/{cam_name}'>Back to camera details</a>
        <a href='/'>Back to camera list</a>
        <h1>{cam_name} - Photo Dates</h1>
        {dates_html}
    </body>
</html>
        """

# Photo file list for a specific date
@app.route('/camera/<cam_name>/photos/<date>')
def camera_photos_files(cam_name, date):
    if not cam_name.startswith("cam"):
        return "Invalid camera name", 404
    data = get_all_camera_data()[cam_name]
    files = sorted([(ts, data['photos'][ts]) for ts in data['photos'] if datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d') == date])
    files_html = "<ul>" + "".join(f"<li><a href='/camera/{cam_name}/photos/{date}/{idx}'>{datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')}</a></li>" for idx, (ts, file) in enumerate(files)) + "</ul>"
    return f"""
<!DOCTYPE html>
<html lang='en'>
    <head>
        <meta charset='utf-8'>
        <meta name='viewport' content='width=device-width, initial-scale=1'>
        <title>{cam_name} Photos on {date}</title>
        <style>
            body {{ font-family: system-ui, sans-serif; margin: 0; padding: 1em; background: #f8f9fa; }}
            h1 {{ font-size: 1.2em; margin-bottom: 0.7em; }}
            ul {{ padding: 0; list-style: none; }}
            li {{ margin: 0.5em 0; }}
            a {{ color: #1565c0; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            @media (max-width: 600px) {{
                h1 {{ font-size: 1em; }}
            }}
        </style>
    </head>
    <body>
        <a href='/camera/{cam_name}/photos'>Back to photo dates</a>
        <a href='/camera/{cam_name}'>Back to camera details</a>
        <a href='/'>Back to camera list</a>
        <h1>{cam_name} - Photos on {date}</h1>
        {files_html}
    </body>
</html>
        """


@app.route('/camera/<cam_name>/videos/<date>/<int:file_idx>')
def camera_video_viewer(cam_name, date, file_idx):
    if not cam_name.startswith("cam"):
        return "Invalid camera name", 404
    data = get_all_camera_data()[cam_name]
    files = data['videos_by_date'].get(date, [])
    if file_idx < 0 or file_idx >= len(files):
        return "File not found", 404
    ts, file = files[file_idx]
    all_dates = data['video_dates']
    date_idx = all_dates.index(date)
    if file_idx > 0:
        prev_link = f"<a href='/camera/{cam_name}/videos/{date}/{file_idx-1}' style='font-size:2em;text-decoration:none;'>&larr;</a>"
    elif date_idx > 0:
        prev_date = all_dates[date_idx-1]
        prev_files = data['videos_by_date'][prev_date]
        prev_link = f"<a href='/camera/{cam_name}/videos/{prev_date}/{len(prev_files)-1}' style='font-size:2em;text-decoration:none;'>&larr;</a>"
    else:
        prev_link = ""
    if file_idx < len(files)-1:
        next_link = f"<a href='/camera/{cam_name}/videos/{date}/{file_idx+1}' style='font-size:2em;text-decoration:none;'>&rarr;</a>"
    elif date_idx < len(all_dates)-1:
        next_date = all_dates[date_idx+1]
        next_files = data['videos_by_date'][next_date]
        next_link = f"<a href='/camera/{cam_name}/videos/{next_date}/0' style='font-size:2em;text-decoration:none;'>&rarr;</a>"
    else:
        next_link = ""
    video_url = f"/media/{cam_name}/{file}"
    photo_candidates = list(data['photos'].items())
    if photo_candidates:
        nearest_photo_ts, nearest_photo_file = min(photo_candidates, key=lambda x: abs(x[0] - ts))
        nearest_photo_date, _ = format_cet(nearest_photo_ts)
        photo_files = data['photos_by_date'][nearest_photo_date]
        photo_idx = [i for i, (t, f) in enumerate(photo_files) if t == nearest_photo_ts][0]
        photo_link = f"<div style='margin-top:1em;'><a href='/camera/{cam_name}/photos/{nearest_photo_date}/{photo_idx}'>Go to nearest photo</a></div>"
    else:
        photo_link = ""
    date_str, time_str = format_cet(ts)
    return f"""
<!DOCTYPE html>
<html lang='en'>
    <head>
        <meta charset='utf-8'>
        <meta name='viewport' content='width=device-width, initial-scale=1'>
        <title>{cam_name} Video {file}</title>
        <style>
            body {{ font-family: system-ui, sans-serif; margin: 0; padding: 1em; background: #f8f9fa; }}
            h1 {{ font-size: 1.1em; margin-bottom: 0.7em; }}
            video {{ width: 100%; max-width: 640px; height: auto; display: block; margin: 0 auto; background: #000; }}
            div {{ text-align: center; }}
            a {{ color: #1565c0; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            @media (max-width: 600px) {{
                h1 {{ font-size: 1em; }}
                video {{ max-width: 100vw; }}
            }}
        </style>
    </head>
    <body>
        <h1>{cam_name} - {date_str} - {time_str}</h1>
        <video controls src='{video_url}'></video><br>
        <div style='margin:1em 0;'>{prev_link} {next_link}</div>
        {photo_link}
        <a href='/camera/{cam_name}/videos/{date}'>Back to file list</a>
    </body>
</html>
        """


@app.route('/camera/<cam_name>/photos/<date>/<int:file_idx>')
def camera_photo_viewer(cam_name, date, file_idx):
    if not cam_name.startswith("cam"):
        return "Invalid camera name", 404
    data = get_all_camera_data()[cam_name]
    files = data['photos_by_date'].get(date, [])
    if file_idx < 0 or file_idx >= len(files):
        return "File not found", 404
    ts, file = files[file_idx]
    all_dates = data['photo_dates']
    date_idx = all_dates.index(date)
    if file_idx > 0:
        prev_link = f"<a href='/camera/{cam_name}/photos/{date}/{file_idx-1}' style='font-size:2em;text-decoration:none;'>&larr;</a>"
    elif date_idx > 0:
        prev_date = all_dates[date_idx-1]
        prev_files = data['photos_by_date'][prev_date]
        prev_link = f"<a href='/camera/{cam_name}/photos/{prev_date}/{len(prev_files)-1}' style='font-size:2em;text-decoration:none;'>&larr;</a>"
    else:
        prev_link = ""
    if file_idx < len(files)-1:
        next_link = f"<a href='/camera/{cam_name}/photos/{date}/{file_idx+1}' style='font-size:2em;text-decoration:none;'>&rarr;</a>"
    elif date_idx < len(all_dates)-1:
        next_date = all_dates[date_idx+1]
        next_files = data['photos_by_date'][next_date]
        next_link = f"<a href='/camera/{cam_name}/photos/{next_date}/0' style='font-size:2em;text-decoration:none;'>&rarr;</a>"
    else:
        next_link = ""
    photo_url = f"/media/{cam_name}/{file}"
    video_candidates = list(data['videos'].items())
    if video_candidates:
        nearest_video_ts, nearest_video_file = min(video_candidates, key=lambda x: abs(x[0] - ts))
        nearest_video_date, _ = format_cet(nearest_video_ts)
        video_files = data['videos_by_date'][nearest_video_date]
        video_idx = [i for i, (t, f) in enumerate(video_files) if t == nearest_video_ts][0]
        video_link = f"<div style='margin-top:1em;'><a href='/camera/{cam_name}/videos/{nearest_video_date}/{video_idx}'>Go to nearest video</a></div>"
    else:
        video_link = ""
    date_str, time_str = format_cet(ts)
    return f"""
<!DOCTYPE html>
<html lang='en'>
    <head>
        <meta charset='utf-8'>
        <meta name='viewport' content='width=device-width, initial-scale=1'>
        <title>{cam_name} Photo {file}</title>
        <style>
            body {{ font-family: system-ui, sans-serif; margin: 0; padding: 1em; background: #f8f9fa; }}
            h1 {{ font-size: 1.1em; margin-bottom: 0.7em; }}
            img {{ width: 100%; max-width: 640px; height: auto; display: block; margin: 0 auto; background: #000; }}
            div {{ text-align: center; }}
            a {{ color: #1565c0; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            @media (max-width: 600px) {{
                h1 {{ font-size: 1em; }}
                img {{ max-width: 100vw; }}
            }}
        </style>
    </head>
    <body>
        <h1>{cam_name} - {date_str} - {time_str}</h1>
        <img src='{photo_url}' alt='Photo'><br>
        <div style='margin:1em 0;'>{prev_link} {next_link}</div>
        {video_link}
        <a href='/camera/{cam_name}/photos/{date}'>Back to file list</a>
    </body>
</html>
        """


@app.route('/media/<cam_name>/<path:filename>')
def serve_media(cam_name, filename):
    if not cam_name.startswith("cam"):
        return "Invalid camera name", 404
    safe_filename = os.path.normpath(filename).replace('..', '')
    media_path = os.path.join(cams_directory, cam_name, safe_filename)
    # Ensure the file is within the camera directory
    abs_media_path = os.path.abspath(media_path)
    abs_cam_dir = os.path.abspath(os.path.join(cams_directory, cam_name))
    if not abs_media_path.startswith(abs_cam_dir):
        return "Invalid file path", 404
    if not os.path.exists(abs_media_path):
        return "File not found", 404

    # Serve images and .mp4 directly
    ext = os.path.splitext(abs_media_path)[1].lower()
    if ext in ['.jpg', '.jpeg', '.png']:
        mimetype = 'image/jpeg' if ext in ['.jpg', '.jpeg'] else 'image/png'
        return flask.send_file(abs_media_path, mimetype=mimetype)
    elif ext == '.mp4':
        return flask.send_file(abs_media_path, mimetype='video/mp4')
    # Transcode .mkv to .mp4 on the fly
    elif abs_media_path.endswith('.mkv'):
        import subprocess
        from flask import Response
        def generate():
            # ffmpeg command to transcode mkv to mp4 (H.264/AAC)
            cmd = [
                'ffmpeg', '-i', abs_media_path,
                '-f', 'mp4',
                '-vcodec', 'libx264', '-acodec', 'aac',
                '-movflags', 'frag_keyframe+empty_moov',
                '-preset', 'veryfast',
                '-tune', 'fastdecode',
                '-analyzeduration', '0', '-probesize', '32',
                '-y', '-loglevel', 'error', '-'
            ]
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=4096)
            try:
                while True:
                    chunk = p.stdout.read(4096)
                    if not chunk:
                        break
                    yield chunk
            finally:
                p.stdout.close()
                p.stderr.close()
                p.terminate()
        return Response(generate(), mimetype='video/mp4')
    else:
        return "Unsupported file type", 415


def get_camera_data(cam):
    """
    Gathers and organizes all data for a specific camera.
    Returns a dictionary containing video and photo file mappings,
    grouped and sorted by date.
    """
    cam_path = os.path.join(cams_directory, cam)
    video_files = {}
    photo_files = {}
    # Walk the camera directory tree
    for root, dirs, files in os.walk(cam_path):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, os.path.join(cams_directory, cam)).replace(os.sep, '/')
            # Get mtime as UTC, then convert to CET
            mtime_utc = datetime.datetime.fromtimestamp(os.path.getmtime(full_path), datetime.timezone.utc)
            mtime_cet = mtime_utc.astimezone(CET)
            timestamp = int(mtime_cet.timestamp())
            if is_extension_in_list(file, cams_images_extentions):
                photo_files[timestamp] = rel_path
                continue
            elif is_extension_in_list(file, cams_videos_extentions):
                video_files[timestamp] = rel_path
                continue
    # Precompute date groupings and sorted lists
    def group_by_date(files_dict):
        by_date = {}
        for ts, rel_path in files_dict.items():
            # Use CET date directly from mtime_cet
            dt_cet = datetime.datetime.fromtimestamp(ts, CET)
            date = dt_cet.strftime('%Y-%m-%d')
            by_date.setdefault(date, []).append((ts, rel_path))
        # Sort each date's list by timestamp
        for date in by_date:
            by_date[date].sort()
        return by_date
    videos_by_date = group_by_date(video_files)
    photos_by_date = group_by_date(photo_files)
    video_dates = sorted(videos_by_date.keys())
    photo_dates = sorted(photos_by_date.keys())
    return {
        "videos": video_files,
        "photos": photo_files,
        "videos_by_date": videos_by_date,
        "photos_by_date": photos_by_date,
        "video_dates": video_dates,
        "photo_dates": photo_dates,
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


if __name__ == "__main__":
    init()
    app.run(host='0.0.0.0', port=port, debug=debug)
