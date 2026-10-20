import ipaddress
import logging
import re
import socket
import sys
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from ddgs import DDGS
import requests
from config.settings import Setting
from models.cache import getCache, setCache

settings = Setting()
logger = logging.getLogger("proofpick.web")


def isPrivateOrLoopbackHost(host: str, timeout: float = 3.0) -> bool:
    """Checks if a hostname resolves to private, loopback, or reserved IP ranges (SSRF prevention)."""
    if not host:
        return True
    hostLower = host.lower()
    if hostLower in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        return True
    # Strip port if present in host argument (e.g., example.com:8080)
    if ":" in hostLower and not hostLower.startswith("["):
        hostLower = hostLower.split(":")[0]
    origTimeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(timeout)
        addrInfo = socket.getaddrinfo(hostLower, None)
        for family, _, _, _, sockaddr in addrInfo:
            ipStr = sockaddr[0]
            ipObj = ipaddress.ip_address(ipStr)
            if ipObj.is_private or ipObj.is_loopback or ipObj.is_reserved or ipObj.is_link_local:
                return True
    except Exception:
        return True
    finally:
        socket.setdefaulttimeout(origTimeout)
    return False


class WebExtractor:
    def __init__(self, search_list: list[str]):
        self.search_string = search_list

    def search_on_web(self):
        search_results = []
        for query in self.search_string:
            cache_key = f"web_search:{query}:{settings.max_google_result}"
            cached = getCache(cache_key)
            if cached is not None and len(cached) > 0:
                logger.info(f"Loaded {len(cached)} cached web results for '{query}'")
                search_results.append({"query": query, "result": cached})
                continue

            try:
                logger.info(f"Searching web for '{query}'...")
                results = list(DDGS().text(query, max_results=settings.max_google_result))
                if results:
                    setCache(cache_key, results)
                search_results.append({"query": query, "result": results})
            except Exception as e:
                logger.warning(f"Web search error for '{query}': {e}")
                search_results.append({"query": query, "result": []})

        return search_results

    def webcontent_filter(self, search_results: list[dict[str, dict | str]]):
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

                # Block private/loopback SSRF attempts early
                if isPrivateOrLoopbackHost(host):
                    continue

                # Block social & unwanted domains
                is_blocked_domain = False
                for blocked in settings.blocked_domains:
                    blocked_clean = blocked.lower().strip()
                    if host == blocked_clean or host.endswith(f".{blocked_clean}"):
                        is_blocked_domain = True
                        break
                if is_blocked_domain:
                    continue

                # Block file extensions
                path_lower = parsed.path.lower()
                if any(path_lower.endswith(ext.lower()) for ext in settings.blocked_file_extensions):
                    continue

                if href in seen_urls:
                    continue
                seen_urls.add(href)
                filtered_results.append(item)

            if settings.use_safe_browsing and settings.google_safe_browsing_api_key and filtered_results:
                try:
                    threat_urls = self.check_safe_browsing([r["href"] for r in filtered_results])
                    filtered_results = [r for r in filtered_results if r["href"] not in threat_urls]
                except Exception as e:
                    logger.warning(f"Safe browsing check failed: {e}")

            each_query_dict["result"] = filtered_results

        return search_results

    def check_safe_browsing(self, urls: list[str]) -> set[str]:
        api_url = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={settings.google_safe_browsing_api_key}"
        payload = {
            "client": {"clientId": "proofpick", "clientVersion": "1.0"},
            "threatInfo": {
                "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
                "platformTypes": ["ANY_PLATFORM"],
                "threatEntryTypes": ["URL"],
                "threatEntries": [{"url": u} for u in urls],
            },
        }
        res = requests.post(api_url, json=payload, timeout=10)
        threat_urls = set()
        if res.status_code == 200:
            data = res.json()
            for m in data.get("matches", []):
                u = m.get("threat", {}).get("url")
                if u:
                    threat_urls.add(u)
        return threat_urls

    def webpage_content_extractor(self, each_result: dict):
        url = each_result.get("href")
        if not url:
            return each_result

        cache_key = f"web_page:{url}"
        cached = getCache(cache_key)
        if cached is not None and cached.get("text"):
            each_result["web content"] = cached["text"]
            each_result["domain"] = cached["domain"]
            return each_result

        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        domain = host[4:] if host.startswith("www.") else host

        if isPrivateOrLoopbackHost(host):
            return each_result

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
            }
            # Follow redirects manually (max 5 hops) checking hostname on every hop to avoid SSRF bypasses
            currentUrl = url
            response = None
            maxHops = 5

            for _ in range(maxHops):
                currHost = (urlparse(currentUrl).hostname or "").lower()
                if isPrivateOrLoopbackHost(currHost):
                    return each_result

                resp = requests.get(
                    currentUrl,
                    timeout=settings.web_fetch_timeout,
                    headers=headers,
                    stream=True,
                    allow_redirects=False,
                )
                if resp.is_redirect or resp.status_code in (301, 302, 303, 307, 308):
                    redirectLocation = resp.headers.get("Location")
                    resp.close()
                    if not redirectLocation:
                        return each_result
                    from urllib.parse import urljoin
                    currentUrl = urljoin(currentUrl, redirectLocation)
                else:
                    response = resp
                    break

            if response is None or response.status_code != 200:
                if response:
                    response.close()
                return each_result

            try:
                content_type = response.headers.get("Content-Type", "").lower()
                if "text/html" not in content_type:
                    return each_result

                bodyBytes = b""
                for chunk in response.iter_content(chunk_size=8192):
                    bodyBytes += chunk
                    if len(bodyBytes) >= settings.web_max_download_bytes:
                        break
            finally:
                response.close()

            soup = BeautifulSoup(bodyBytes, "html.parser")
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
                text = text[: settings.max_web_content_chars]

            if len(text) >= settings.min_web_content_chars:
                each_result["web content"] = text
                each_result["domain"] = domain
                setCache(cache_key, {"text": text, "domain": domain})
        except Exception as e:
            logger.debug(f"Web extraction failed for {url}: {e}")

        return each_result

    def get_web_content(self, search_results: list[dict[str, dict | str]]):
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