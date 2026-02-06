import os

import yt_dlp
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


class DownloadError(Exception):
    """Raised when video download fails."""
    pass


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((yt_dlp.utils.DownloadError, ConnectionError, TimeoutError)),
    reraise=True,
)
def download_audio(url: str, output_dir: str = "downloads") -> str:
    os.makedirs(output_dir, exist_ok=True)

    options = {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "outtmpl": f"{output_dir}/%(id)s.%(ext)s",
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(options) as ytdlp:
            data = ytdlp.extract_info(url, download=True)
            pre_filename = ytdlp.prepare_filename(data)
            filename = pre_filename.rsplit(".", 1)[0] + ".mp3"
            return os.path.abspath(filename)
    except yt_dlp.utils.DownloadError as e:
        print(f"Download failed, retrying... Error: {e}")
        raise
