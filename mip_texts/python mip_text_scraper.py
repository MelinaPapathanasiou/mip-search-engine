# mip_text_scraper.py

import os
import hashlib
from playwright.sync_api import sync_playwright

BASE_URL = "https://www.mip.gov.cy/dmmip/md.nsf/home/home?openform"
VISITED_HASHES = set()

def save_text(content, url):
    filename_hash = hashlib.md5(url.encode()).hexdigest()
    filename = f"{filename_hash}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"📝  Saved → {filename}")

def extract_links(page):
    return page.eval_on_selector_all("a", "elements => elements.map(el => el.href)")

def is_internal_link(link):
    return link and "mip.gov.cy/dmmip/md.nsf" in link

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        print(f"🌐 Visiting {BASE_URL}")
        page.goto(BASE_URL, timeout=60000)
        to_visit = set(extract_links(page))
        visited = set()

        while to_visit:
            url = to_visit.pop()
            if url in visited or not is_internal_link(url):
                continue
            try:
                page.goto(url, timeout=30000)
                content = page.inner_text("body")
                hash_ = hashlib.md5(content.encode()).hexdigest()
                if hash_ not in VISITED_HASHES:
                    save_text(content, url)
                    VISITED_HASHES.add(hash_)
                visited.add(url)
                new_links = extract_links(page)
                for link in new_links:
                    if link not in visited and is_internal_link(link):
                        to_visit.add(link)
            except Exception as e:
                print(f"⚠️ Error visiting {url}: {e}")
        browser.close()

if __name__ == "__main__":
    main()
