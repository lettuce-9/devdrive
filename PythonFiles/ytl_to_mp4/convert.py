import yt_dlp # type: ignore
import os
import subprocess

# "type: ignore" is used to suppress warnings that are false, don't remove it

subprocess.run('cls', shell=True)

print("Custom YouTube Downloader/Converter")
print("Available formats:")
print("Youtube => .mp4")
print("Youtube => .mp3")

input_opt = input("Convert to which format? : ").strip().lower()

if input_opt in ["mp4", ".mp4"]:
    output_dir = './converted_files_mp4/%(title)s.%(ext)s'
elif input_opt in ["mp3", ".mp3"]:
    output_dir = './converted_files_mp3/%(title)s.%(ext)s'
else:
    print("Invalid format selected. Exiting.")
    exit()

output_folder = os.path.dirname(output_dir)
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

def download_video(url):
    ydl_opts = {
        'format': 'bestaudio/best' if input_opt == "mp3" else 'bv*+ba/b',
        'outtmpl': output_dir,
        'noplaylist': True,
        'merge_output_format': 'mp4' if input_opt == "mp4" else None,
        'forceipv4': True,
    }

    if input_opt == "mp3":
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            print(f"Downloading from {url}...")
            ydl.download([url])
            print("Download complete!")
        except yt_dlp.utils.DownloadError as e:
            print(f"Download error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    url = input("Enter YouTube video URL: ")
    download_video(url)
