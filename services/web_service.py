from config.settings import Setting
from ddgs import DDGS
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import requests

settings = Setting()

class WebExtractor:

    def __init__(self,search_list:list[str]):
        self.search_string = search_list

    def search_on_web(self):
        search_results = []

        for query in self.search_string:
            results = DDGS().text(query,max_results=settings.max_google_result)
            search_results.append(
                {
                    "query":query,
                    "result":results
                }
            )
        return search_results

    

    def webcontent_filter(self):
        pass

    
    def webpage_content_extractor(self,each_result:dict):
        url = each_result.get('href')
        if not url:
            return each_result

        
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            response = requests.get(url,timeout=15,headers=headers)
            soup = BeautifulSoup(response.content,'html.parser')
            # extracting paragraph
            paragraph_tag = soup.findAll("p")
            if paragraph_tag:
                full_text = " ".join(tag.get_text().strip() for tag in paragraph_tag)
                text = full_text if full_text.strip() else "Empty paragraph found" 
            else:
                text = "No text content found"
            each_result["web content"] = text
        except Exception as e:
            print("Web content extraction failed")

        return each_result

    
    def get_web_content (self,search_results:list[dict[str,dict | str]]):

        for query_group in search_results:
            links_list = query_group.get("result",[])
            no_of_worker = len(links_list)

            if no_of_worker == 0:
                continue

            with ThreadPoolExecutor(max_workers=no_of_worker) as executor:
                list(executor.map(self.webpage_content_extractor,links_list))

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

        


    