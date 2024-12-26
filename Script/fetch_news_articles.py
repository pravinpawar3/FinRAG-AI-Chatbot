import os
import requests
from bs4 import BeautifulSoup
from google.cloud import storage
import time
import json
from datetime import datetime
import logging

# Setting up logging configuration
logger = logging.getLogger()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fetching API key and Google Cloud credentials from environment variables
API_KEY = os.getenv('POLYGON_API_KEY')
SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
BUCKET_NAME = 'news_articles-bucket'

# List of top 15 companies' ticker symbols
tickers = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
    "META", "NVDA", "BRK.B", "V", "JNJ",
    "WMT", "JPM", "PG", "MA", "UNH"
]

# Initialize Google Cloud Storage client
storage_client = storage.Client.from_service_account_json(SERVICE_ACCOUNT_JSON)
bucket = storage_client.bucket(BUCKET_NAME)

# Dictionary to store the last fetched article ID for each ticker
last_fetched_ids = {}

def get_article_content(url):
    """Scrape the full article content from the given URL."""
    try:
        response = requests.get(url)
        if response.status_code == 200:
            # Parse the HTML content to extract article paragraphs
            soup = BeautifulSoup(response.content, "html.parser")
            paragraphs = soup.find_all("p")
            content = "\n".join([para.get_text() for para in paragraphs])
            return content
        else:
            logger.error(f"Failed to retrieve content from {url}, Status Code: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error retrieving content from {url}: {e}")
        return None

def upload_to_gcs(data, folder_name, filename):
    """Upload the article data to Google Cloud Storage in the specified folder."""
    blob_path = f"{folder_name}/{filename}"
    blob = bucket.blob(blob_path)
    blob.upload_from_string(
        data=json.dumps(data),
        content_type='application/json'
    )
    logger.info(f"Uploaded {filename} to {BUCKET_NAME}/{folder_name}")

def fetch_and_store_news():
    """Fetch the latest news articles for each ticker and upload them to Google Cloud Storage."""
    base_url = "https://api.polygon.io/v2/reference/news"
    batch_size = 5  # Fetch 5 articles per batch

    # Process tickers in batches
    for i in range(0, len(tickers), batch_size):
        batch_tickers = tickers[i:i + batch_size]

        for ticker in batch_tickers:
            params = {
                "ticker": ticker,
                "limit": 1,
                "apiKey": API_KEY
            }
            response = requests.get(base_url, params=params)

            if response.status_code == 200:
                data = response.json()
                if data["results"]:
                    # Extracting the first article from the response
                    article = data["results"][0]
                    article_id = article["id"]

                    # Check if this article is new by comparing with the last fetched ID
                    if last_fetched_ids.get(ticker) == article_id:
                        logger.info(f"No new article for {ticker}. Skipping...")
                        continue

                    # Update the last fetched article ID for this ticker
                    last_fetched_ids[ticker] = article_id

                    # Extract article URL and fetch its full content
                    article_url = article["article_url"]
                    logger.info(f"Fetching new content for {ticker} from {article_url}")

                    content = get_article_content(article_url)

                    if content:
                        # Parse the article's published date to create folder structure
                        published_utc = article["published_utc"]
                        published_datetime = datetime.strptime(published_utc, "%Y-%m-%dT%H:%M:%SZ")
                        year = published_datetime.strftime("%Y")
                        month = published_datetime.strftime("%m")
                        day = published_datetime.strftime("%d")
                        hour = published_datetime.strftime("%H")
                        minute = published_datetime.strftime("%M")
                        second = published_datetime.strftime("%S")

                        # Define Google Cloud Storage folder structure based on timestamp
                        folder_name = f"{ticker}/{year}/Month={month}/Day={day}/Hour={hour}/Minute={minute}"
                        filename = f"{ticker}_{second}.json"

                        # Prepare article data for uploading
                        article_data = {
                            "ticker": ticker,
                            "title": article["title"],
                            "summary": article["description"],
                            "content": content,
                            "published_utc": published_utc
                        }

                        # Upload the article data to Google Cloud Storage
                        upload_to_gcs(article_data, folder_name, filename)
                        logger.info(f"Stored article for {ticker} in {folder_name}/{filename}")

            else:
                logger.error(f"Failed to retrieve news for {ticker}. Status Code: {response.status_code}")

        # Wait for 1 minute before fetching the next batch to comply with rate limits
        logger.info("Waiting for 1 minute before fetching the next batch of articles...")
        time.sleep(60)

# Run the function to fetch and store news articles every 24 hours continuously
if __name__ == "__main__":
    while True:
        fetch_and_store_news()
        logger.info("Waiting for 24 hours before fetching new articles...")
        time.sleep(86400)  # Wait for 24 hours (86400 seconds)
