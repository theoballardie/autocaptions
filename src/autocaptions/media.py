"""Reading media durations with ffprobe or ffmpeg."""
from __future__ import annotations

import json
import re
import shutil
import subprocess


def _ffmpeg() -> str | None:
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg  # optional, bundles a static ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return None


def duration(path: str) -> float:
    """Length of an audio or video file in seconds."""
    probe = shutil.which("ffprobe")
    if probe:
        out = subprocess.run([probe, "-v", "error", "-show_entries", "format=duration", "-of", "json", path],
                             capture_output=True, text=True, check=True).stdout
        return float(json.loads(out)["format"]["duration"])
    try:  # PyAV ships with the audio extra
        import av
        with av.open(path) as container:
            if container.duration:
                return container.duration / av.time_base
    except ImportError:
        pass
    ffmpeg = _ffmpeg()
    if not ffmpeg:
        raise SystemExit('reading durations needs ffmpeg, ffprobe or the audio extra: pip install "autocaptions[audio]"')
    err = subprocess.run([ffmpeg, "-hide_banner", "-i", path], capture_output=True, text=True).stderr
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", err)
    if not match:
        raise SystemExit(f"could not read a duration from {path}")
    h, m, s = match.groups()
    return int(h) * 3600 + int(m) * 60 + float(s)
