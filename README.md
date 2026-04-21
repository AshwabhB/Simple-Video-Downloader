# Video Downloader

I built this because I wanted a simple, no-fuss way to download videos from the internet - YouTube, Instagram, TikTok, and more - without dealing with sketchy websites or complicated tools. Feel free to use it.

## What it does

Paste a video link, pick a quality, and download it. That's it.

- Supports YouTube, Instagram Reels, TikTok, Twitter/X, Vimeo, and 1000+ other sites
- Downloads in the highest quality available, or lets you choose a specific resolution
- Merges video and audio into a clean `.mp4` file
- Supports downloading multiple videos at once
- Keeps a log of everything you've downloaded (`downloaded_videos.txt`)

## Requirements

- Python 3.x
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — `pip install yt-dlp`
- [FFmpeg](https://ffmpeg.org/) — required for merging video and audio

## How to run

```
python app.py
```

Videos are saved to the `Downloads` folder next to the app.

## Disclaimer

This tool is intended for personal use only. Only download content you have the right to download. Respect the copyright and terms of service of each platform. The author is not responsible for how this tool is used.
