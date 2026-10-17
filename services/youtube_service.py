from yt_dlp import YoutubeDL
from config.settings import Setting
from concurrent.futures import ThreadPoolExecutor
from models.cache import getCache, setCache
import youtube_transcript_api
from groq import Groq
import logging
import os
import re
import sys

setting = Setting()
logger = logging.getLogger("proofpick.youtube")


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
            search_url = f"ytsearch{setting.max_youtube_results}:{string}"
            cached_data = getCache(search_url)
            if cached_data is not None:
                logger.info(f"Loaded {len(cached_data)} cached YouTube results for query: '{string}'")
                links.extend(cached_data)
                continue

            query_links = []
            logger.info(f"Searching YouTube for query: '{string}' (max {setting.max_youtube_results} results)")
            try:
                with YoutubeDL(ydl_opts) as ydl:
                    result = ydl.extract_info(search_url, download=False)
                    for entry in result.get("entries", []):
                        duration = entry.get("duration")
                        views = entry.get("view_count")

                        if (
                            duration is None or 
                            duration < setting.min_duration or 
                            duration > setting.max_duration or
                            views is None or 
                            views < setting.min_youtube_views
                        ):
                            continue

                        query_links.append({
                            "search_query": string,
                            "link": f"https://www.youtube.com/watch?v={entry['id']}",
                            "title": entry.get("title") or "",
                            "description": entry.get("description") or "",
                            "duration": duration,
                            "views": views,
                            "channel_name": entry.get("channel") or "",
                            "channel_link": entry.get("channel_url") or "",
                        })
                logger.info(f"Found {len(query_links)} eligible videos for query: '{string}'")
                setCache(search_url, query_links)
                links.extend(query_links)
            except Exception as e:
                logger.error(f"YouTube search error for '{string}': {e}")
                continue

        return links

    def extract_transcript_by_youtube_api(self,url:str):
        video_id_match = re.search(r"v=([^&]+)", url)
        if not video_id_match:
            return (None, "")
        video_id = video_id_match.group(1)

        cache_key = f"yt_transcript:{video_id}"
        cached = getCache(cache_key)
        if cached is not None:
            logger.info(f"Loaded cached transcript for video {video_id} ({cached.get('transcript_source', 'cached')})")
            return (cached.get("transcript"), cached.get("transcript_source", ""))

        text = None
        source = ""

        try:
            logger.info(f"Attempting official captions fetch for video: {video_id}")
            ytt_api = youtube_transcript_api.YouTubeTranscriptApi()
            fetched_transcript = ytt_api.fetch(video_id, languages=setting.transcript_languages)
            transcript_in_dict = fetched_transcript.to_raw_data()
            text = " ".join(item["text"] for item in transcript_in_dict if "text" in item).strip()
            if text and len(text) >= 20:
                source = "youtube_captions"
                logger.info(f"Successfully extracted captions for video {video_id} ({len(text)} characters)")
            else:
                text = None
        except Exception as e:
            logger.info(f"Official captions unavailable for {video_id} ({e}). Checking Whisper fallback...")
            text = None

        if not text and setting.use_whisper_fallback and setting.groq_api_key:
            logger.info(f"Starting Whisper audio fallback for video {video_id}...")
            text = self.extract_transcript_by_api_call(url)
            if text:
                source = "whisper"
                logger.info(f"Whisper transcribed {len(text)} characters for video {video_id}")

        if text:
            setCache(cache_key, {"transcript": text, "transcript_source": source})
        return (text, source)

    def extract_transcript_by_api_call(self,url:str):
        mp3_file = None
        try:
            mp3_file = self.download_and_convert_to_mp3(url)
            if not mp3_file or not os.path.exists(mp3_file):
                logger.warning(f"Audio file missing for {url}")
                return None

            file_size_mb = os.path.getsize(mp3_file) / (1024 * 1024)
            logger.info(f"Audio downloaded: {mp3_file} ({file_size_mb:.2f} MB). Sending to Groq Whisper...")
            if file_size_mb > setting.whisper_max_file_mb:
                logger.warning(f"Audio file {mp3_file} ({file_size_mb:.1f}MB) exceeds {setting.whisper_max_file_mb}MB limit")
                return None

            client = Groq(api_key=setting.groq_api_key)

            with open(mp3_file, "rb") as file:
                if setting.whisper_translate:
                    transcription = client.audio.translations.create(
                        file=file,
                        model=setting.whisper_model,
                        response_format="verbose_json"
                    )
                else:
                    transcription = client.audio.transcriptions.create(
                        file=file,
                        model=setting.whisper_model,
                        response_format="verbose_json"
                    )

            logger.info(f"Groq Whisper transcription finished for {url}")
            return transcription.text
        except Exception as e:
            logger.error(f"Whisper transcription failed for {url}: {e}")
            return None
        finally:
            if mp3_file and os.path.exists(mp3_file):
                try:
                    os.remove(mp3_file)
                    logger.info(f"Cleaned up temporary audio file: {mp3_file}")
                except Exception as e:
                    logger.warning(f"Failed to remove audio file {mp3_file}: {e}")

    def download_and_convert_to_mp3(self,url:str):
        video_id_match = re.search(r"v=([^&]+)", url)
        video_id = video_id_match.group(1) if video_id_match else "audio"

        audio_dir = setting.audio_dir
        os.makedirs(audio_dir, exist_ok=True)

        output_template = os.path.join(audio_dir, f"{video_id}.%(ext)s")
        logger.info(f"Downloading audio track from YouTube: {url}")

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": output_template,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "nocheckcertificate": True,
            "quiet": True,
        }

        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(url, download=True)
                mp3_path = os.path.join(audio_dir, f"{video_id}.mp3")
                if os.path.exists(mp3_path):
                    logger.info(f"Audio converted to MP3: {mp3_path}")
                    return mp3_path
                return None
        except Exception as e:
            logger.error(f"Audio download failed for {url}: {e}")
            return None

    def get_transcript(self,links:list[dict[str,str]]):
        unique_urls = list({link.get("link") for link in links if link.get("link")})
        url_transcripts = {}

        def fetch_one(url):
            try:
                return (url, self.extract_transcript_by_youtube_api(url))
            except Exception as e:
                print(f"Failed extracting transcript for {url}: {e}", file=sys.stderr)
                return (url, (None, ""))

        with ThreadPoolExecutor(max_workers=setting.youtube_workers) as executor:
            for url, (transcript, transcript_source) in executor.map(fetch_one, unique_urls):
                url_transcripts[url] = (transcript, transcript_source)

        for link in links:
            url = link.get("link")
            transcript, transcript_source = url_transcripts.get(url, (None, ""))
            link["transcript"] = transcript
            link["transcript_source"] = transcript_source

        return links


# for testing only
# if __name__ =='__main__':
#     yt = YoutubeSearch(["iphone 16 review"])
#     print("Extracting the link from youtube")
#     links_extracted = yt.search_youtube()
#     print(f"{len(links_extracted)} links extracted sucessfully ")
#     video_details_with_transcription = yt.get_transcript(links_extracted)
#     print(f"video details :- {video_details_with_transcription}")
