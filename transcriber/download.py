import os

import yt_dlp


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

    with yt_dlp.YoutubeDL(options) as ytdlp:
        data = ytdlp.extract_info(url, download=True)
        pre_filename = ytdlp.prepare_filename(data)
        filename = pre_filename.rsplit(".", 1)[0] + ".mp3"
        return os.path.abspath(filename)
