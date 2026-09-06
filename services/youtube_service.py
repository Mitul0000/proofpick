from yt_dlp import YoutubeDL
from config import settings
from concurrent.futures import ThreadPoolExecutor
from youtube_transcript_api import YouTubeTranscriptApi
from groq import Groq
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
                        "search_query":string,
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


    def extract_transcript_by_youtube_api(self,url):
        try:
            video_id = url.split("v=")(1)
            ytt_api = YouTubeTranscriptApi()
            fetched_transcript = ytt_api.fetch(video_id)
            transcript_in_dict = fetched_transcript.to_raw_data()
            text = " ".join(item["text"] for item in transcript_in_dict)

            if(text is None or len(text)<20):
                self.extract_transcript_by_api_call(url)

        except Exception as e:
            print(f"An error occurred during conversion: {e}")
            return None

        return text





    def extract_transcript_by_api_call(self,url):
        try:
            mp3_file = self.download_and_convert_to_mp3(url)
            client = Groq()

            with open(mp3_file,"rb") as file:
                transcription = client.audio.transcriptions.create(
                    file=file,
                    model="whisper-large-v3-turbo",
                    response_format="verbose_json"
                )

            return transcription.text
        except Exception as e:
            print(f"An error occurred during conversion: {e}")
            return None



    def download_and_convert_to_mp3(url):

        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        audio_dir = os.path.join(script_dir, "audio")
        os.makedirs(audio_dir, exist_ok=True)

        output_template = os.path.join(audio_dir, "%(title)s.%(ext)s")

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": output_template,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "nocheckcertificate": True,
        }

        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

                filename = ydl.prepare_filename(info)

                mp3_path = os.path.splitext(filename)[0] + ".mp3"

                return mp3_path

        except Exception as e:
            print(f"An error occurred during download or conversion: {e}")
            return None


    

    def get_transcript (self,links:list[dict[str,str]]):
        urls=[link.get('link') for link in links]

        with ThreadPoolExecutor(max_workers=18) as executor:
            result = list(executor.map(self.extract_transcript_by_youtube_api,urls))

        for link, transcript in zip(links, result):
            link["transcript"] = transcript

        return links
