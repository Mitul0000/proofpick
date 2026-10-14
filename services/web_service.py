from config.settings import Setting
from ddgs import DDGS
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from models.cache import getCache, setCache
from urllib.parse import urlparse
import requests
import re
import sys

settings = Setting()


class WebExtractor:

    def __init__(self,search_list:list[str]):
        self.search_string = search_list

    def search_on_web(self):
        search_results = []

        for query in self.search_string:
            cache_key = f"web_search:{query}:{settings.max_google_result}"
            cached = getCache(cache_key)
            if cached is not None:
                search_results.append({
                    "query": query,
                    "result": cached,
                })
                continue

            try:
                results = list(DDGS().text(query, max_results=settings.max_google_result))
                setCache(cache_key, results)
                search_results.append({
                    "query": query,
                    "result": results,
                })
            except Exception as e:
                print(f"Web search error for '{query}': {e}", file=sys.stderr)
                search_results.append({
                    "query": query,
                    "result": [],
                })

        return search_results

    def webcontent_filter(self,search_results:list[dict[str,dict | str]]):
        for each_query_dict in search_results:
            raw_results = each_query_dict.get("result", [])
            filtered_results = []
            seen_urls = set()

            for item in raw_results:
                href = (item.get("href") or "").strip()
                if not href:
                    continue

                parsed = urlparse(href)
                host = (parsed.hostname or "").lower()

                # check blocked domains
                is_blocked_domain = False
                for blocked in settings.blocked_domains:
                    blocked_clean = blocked.lower().strip()
                    if host == blocked_clean or host.endswith(f".{blocked_clean}"):
                        is_blocked_domain = True
                        break
                if is_blocked_domain:
                    continue

                # check blocked file extensions
                path_lower = parsed.path.lower()
                is_blocked_ext = False
                for ext in settings.blocked_file_extensions:
                    if path_lower.endswith(ext.lower()):
                        is_blocked_ext = True
                        break
                if is_blocked_ext:
                    continue

                # check duplicate urls within the same query
                if href in seen_urls:
                    continue
                seen_urls.add(href)

                filtered_results.append(item)

            # safe browsing check if enabled
            if settings.use_safe_browsing and settings.google_safe_browsing_api_key and filtered_results:
                try:
                    threat_urls = self.check_safe_browsing([r["href"] for r in filtered_results])
                    filtered_results = [r for r in filtered_results if r["href"] not in threat_urls]
                except Exception as e:
                    print(f"Safe browsing check failed: {e}", file=sys.stderr)

            each_query_dict["result"] = filtered_results

        return search_results

    def check_safe_browsing(self,urls:list[str])->set[str]:
        api_url = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={settings.google_safe_browsing_api_key}"
        payload = {
            "client": {
                "clientId": "proofpick",
                "clientVersion": "1.0",
            },
            "threatInfo": {
                "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
                "platformTypes": ["ANY_PLATFORM"],
                "threatEntryTypes": ["URL"],
                "threatEntries": [{"url": u} for u in urls],
            }
        }
        res = requests.post(api_url, json=payload, timeout=10)
        threat_urls = set()
        if res.status_code == 200:
            data = res.json()
            matches = data.get("matches", [])
            for m in matches:
                u = m.get("threat", {}).get("url")
                if u:
                    threat_urls.add(u)
        return threat_urls

    def webpage_content_extractor(self,each_result:dict):
        url = each_result.get("href")
        if not url:
            return each_result

        cache_key = f"web_page:{url}"
        cached = getCache(cache_key)
        if cached is not None:
            if cached.get("text"):
                each_result["web content"] = cached["text"]
                each_result["domain"] = cached["domain"]
            return each_result

        try:
            parsed = urlparse(url)
            host = parsed.netloc or ""
            domain = host[4:] if host.startswith("www.") else host

            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"}
            response = requests.get(url, timeout=settings.web_fetch_timeout, headers=headers)
            content_type = response.headers.get("Content-Type", "").lower()
            if response.status_code != 200 or "text/html" not in content_type:
                return each_result

            soup = BeautifulSoup(response.content, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form", "noscript"]):
                tag.decompose()

            extracted_parts = []
            for tag in soup.find_all(["h1", "h2", "h3", "p", "li"]):
                tag_text = tag.get_text().strip()
                if tag_text:
                    extracted_parts.append(tag_text)

            text = " ".join(extracted_parts)
            text = re.sub(r"\s+", " ", text).strip()
            if len(text) > settings.max_web_content_chars:
                text = text[:settings.max_web_content_chars]

            if len(text) >= settings.min_web_content_chars:
                each_result["web content"] = text
                each_result["domain"] = domain
                setCache(cache_key, {"text": text, "domain": domain})
        except Exception as e:
            print(f"Web extraction failed for {url}: {e}", file=sys.stderr)

        return each_result

    def get_web_content(self,search_results:list[dict[str,dict | str]]):
        unique_urls = set()
        for query_group in search_results:
            for item in query_group.get("result", []):
                u = item.get("href")
                if u:
                    unique_urls.add(u)

        url_data_map = {}

        def fetch_page(url):
            dummy = {"href": url}
            self.webpage_content_extractor(dummy)
            return (url, dummy.get("web content"), dummy.get("domain"))

        with ThreadPoolExecutor(max_workers=settings.web_workers) as executor:
            for url, content, domain in executor.map(fetch_page, list(unique_urls)):
                if content:
                    url_data_map[url] = {"web content": content, "domain": domain}

        for query_group in search_results:
            valid_results = []
            for item in query_group.get("result", []):
                u = item.get("href")
                if u in url_data_map:
                    item["web content"] = url_data_map[u]["web content"]
                    item["domain"] = url_data_map[u]["domain"]
                    valid_results.append(item)
            query_group["result"] = valid_results

        return search_results


# if __name__=="__main__":
#     extractor = WebExtractor(search_list=["iphone 16", "iphone 16 review"])
#     raw_search_data = extractor.search_on_web()
#     complete_web_data = extractor.get_web_content(raw_search_data)
#     for query_group in complete_web_data:
#         print(f"\nQuery: {query_group['query']}")
#         for result in query_group.get("result", []):
#             print(f"Title: {result.get('title')}")
#             print(f"Content Snippet: {str(result.get('web content'))[:150]}...")