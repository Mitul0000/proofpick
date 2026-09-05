from yt_dlp import YoutubeDL
from config import settings
from concurrent.futures import ThreadPoolExecutor
import os


class YoutubeSearch:

    def __init__(self,search_list:list[str]):
        self.search_string = search_list

    def search_youtube(self)->list[dict[str,str]]:
        
        ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'skip_download': True
        }

        links = []

        for string in self.search_string:
            search_url = f"ytsearch{settings.max_youtube_results}:{string}"
            with YoutubeDL (ydl_opts) as ydl:
                result = ydl.extract_info(search_url,download=False)
                for entry in result.get("entries",[]):
                    duration = entry.get("duration")
                    views = entry.get("view_count")
                    channal_subscriber = ydl.extract_info(entry["channel_url"], download=False).get("channel_follower_count")

                    if(
                        duration is None or 
                        duration<600 or 
                        channal_subscriber is None or
                        channal_subscriber < 10000 or
                        views is None or views < 10000):
                        continue

                    
                    links.append({
                        "link":f"https://www.youtube.com/watch?v={entry['id']}",
                        "title":entry.get("title"),
                        "description": entry.get("description"),
                        "duration":duration,
                        "views":views,
                        "channal_name":entry.get("channel"),
                        "channel_link":entry.get("channel_url"),
                        "channal_subscriber":channal_subscriber
                    })
                return links
            
    def download_and_convert_to_mp3(url):
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
audio_dir = os.path.join(script_dir, "audio")
os.makedirs(audio_dir, exist_ok=True)
output_template = os.path.join(audio_dir, "%(title)s.%(ext)s")

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_template,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'nocheckcertificate': True,
        }

        try:
            with YoutubeDL(ydl_opts) as ydl:
                print("Downloading and converting to MP3...")
                ydl.download([url])
                print("Download and conversion completed successfully.")
        except Exception as e:
            print(f"An error occurred during download or conversion: {e}")


    def extract_transcript(links:list[dict[str,str]]):
        urls=[link.get('link') for link in links]

        






    