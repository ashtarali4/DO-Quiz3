import os
import time
import nltk
from fastapi import FastAPI, Query

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from bs4 import BeautifulSoup
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer

# NLTK data is pre-downloaded via the Dockerfile
app = FastAPI()

REGISTRATION_NUMBER = "FA23-BAI-049"
NEWS_SOURCE = "South China Morning Post"

def get_driver():
    print("Initializing Chrome Driver...")
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(30)
    print("Chrome Driver initialized.")
    return driver

def summarize_text(text: str, sentences_count: int = 3) -> str:
    print(f"Summarizing text of length {len(text)}...")
    parser = PlaintextParser.from_string(text, Tokenizer("english"))
    summarizer = LsaSummarizer()
    summary_sentences = summarizer(parser.document, sentences_count)
    return " ".join([str(sentence) for sentence in summary_sentences])

@app.get("/get")
def get_news(keyword: str = Query(..., description="Keyword to search for")):
    print(f"Received request for keyword: {keyword}")
    driver = None
    try:
        driver = get_driver()
        search_url = f"https://www.scmp.com/search/{keyword}"
        print(f"Navigating to {search_url}")
        driver.get(search_url)

        print("Waiting for links to load...")
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "a"))
        )
        time.sleep(3) 

        links = driver.find_elements(By.TAG_NAME, "a")
        article_url = None
        for link in links:
            href = link.get_attribute('href')
            if href and ('/news/' in href or '/tech/' in href or '/economy/' in href) and 'module=hamburger_menu' not in href and 'pgtype=others' not in href:
                article_url = href
                break
        
        if not article_url:
            print("No article found.")
            return {"error": "No article found for the given keyword."}

        print(f"Found article: {article_url}")
        driver.get(article_url)
        print("Waiting for article paragraphs to load...")
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "p"))
        )
        time.sleep(2)

        print("Extracting text...")
        soup = BeautifulSoup(driver.page_source, "html.parser")
        paragraphs = soup.find_all("p")
        article_text = " ".join([p.get_text() for p in paragraphs if len(p.get_text().split()) > 5])

        if not article_text:
            print("Failed to extract text.")
            return {"error": "Failed to extract article content."}

        summary = summarize_text(article_text, sentences_count=4)
        print("Summary generated successfully!")

        return {
            "registration": REGISTRATION_NUMBER,
            "newssource": NEWS_SOURCE,
            "keyword": keyword,
            "url": article_url,
            "summary": summary
        }

    except Exception as e:
        return {"error": str(e)}
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7000)
