import yt_dlp
import os

def download_and_convert(url, is_playlist=False, output_folder='MP3_converted_files'):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'MP3_converted_files/%(title)s.%(ext)s',
        'noplaylist': False,
        'external_downloader': 'aria2c',
        'external_downloader_args': ['-x', '16', '-k', '1M'],
        'concurrent_fragment_downloads': 4,
        'download_archive': 'downloaded.txt',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '128',
        }],
        'quiet': False,
        'ignoreerrors': True,
    }


    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def handle_input():
    print("Input a YouTube video or playlist link to convert to MP3")
    print("Press Ctrl + C to quit")
    inp = input("Input here: ").strip()

    is_playlist = 'playlist' in inp or 'list=' in inp
    download_and_convert(inp, is_playlist=is_playlist)
    print("Finished downloading.")

handle_input()
