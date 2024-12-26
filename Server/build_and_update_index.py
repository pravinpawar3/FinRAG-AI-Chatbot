# Import necessary libraries
from flask import Flask, request, jsonify
import logging
import os
import io
import pyarrow.parquet as pq
from google.cloud import storage
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.vector_stores.pinecone import PineconeVectorStore
from llama_index.core import StorageContext
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import Settings
from pinecone import Pinecone, ServerlessSpec
import json
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_pinecone_client(api_key: str):
    """
    Initialize the Pinecone client with the provided API key and environment.
    """
    return Pinecone(api_key=api_key, environment="us-west1-gcp")

def create_or_connect_index(pinecone_client, index_name: str, dimension: int, metric: str):
    """
    Create a new Pinecone index if it doesn't exist, or connect to an existing one.
    """
    pinecone_client_names = pinecone_client.list_indexes()

    if len(pinecone_client_names) == 0 or index_name not in pinecone_client_names:
        logger.info(f"Creating index {index_name}...")
        pinecone_client.create_index(
            name=index_name,
            dimension=dimension,
            metric=metric,
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1"
            )
        )
    else:
        logger.info(f"Index {index_name} already exists.")

    return pinecone_client.Index(index_name)

def setup_vector_store(index):
    """
    Set up the Pinecone vector store and return the storage context.
    """
    vector_store = PineconeVectorStore(pinecone_index=index)
    return StorageContext.from_defaults(vector_store=vector_store)

def set_embedding_model():
    """
    Set the embedding model for vector generation.
    """
    Settings.embed_model = HuggingFaceEmbedding(
        model_name="BAAI/bge-small-en-v1.5"
    )

def create_index_from_documents(documents, storage_context):
    """
    Create a vector store index from the given documents and storage context.
    """
    return VectorStoreIndex.from_documents(documents, storage_context=storage_context)

def data_news_articles_blobs(news_data_bucket_name):
    """Lists all the Parquet blobs in the specified bucket and returns their content as a list of raw text."""
    logger.info("Method: data_news_articles_blobs execution started.")
    parquet_data = []

    storage_client = storage.Client()

    try:
        config_bucket = storage_client.bucket('fin_rag_config')
        ticker_company_blob = config_bucket.blob('ticker_company_map.json')
        json_string = ticker_company_blob.download_as_string()
        ticker_company_map = json.loads(json_string)

        blobs = storage_client.list_blobs(news_data_bucket_name)

        for blob in blobs:
            if blob.name.endswith('.parquet'):
                try:
                    parquet_bytes = blob.download_as_string()
                    buffer = io.BytesIO(parquet_bytes)
                    table = pq.read_table(buffer)
                    df = table.to_pandas()

                    for index, row in df.iterrows():
                        formatted_date = index.strftime('%B %Y %d')
                        text = f"On date {formatted_date}, for company name {ticker_company_map[row['ticker']]} and Ticker name {row['ticker']} news title is \"{row['title']}\" with summary : \"{row['summary']}\" and sentiment score : \"{row['sentiment']}\""
                        parquet_data.append(text)

                except Exception as e:
                    logger.error(f"Failed to process {blob.name}: {e}")

        # Save the list of raw Parquet data to a file
        with open("news_data.json", "w") as f:
            json.dump(parquet_data, f)

        storage_client = storage.Client()
        bucket_name = 'news_data_bucket'
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob('news_data.json')
        blob.upload_from_filename('news_data.json')

        os.remove('news_data.json')
    except Exception as e:
        logger.error(f"Error accessing bucket '{bucket_name}': {e}")

    logger.info("Method: data_news_articles_blobs execution completed.")
    return parquet_data

def main(index_name):
    """
    Main method to handle the workflow of initializing Pinecone, creating or connecting to the index,
    setting up the vector store, and creating the index from documents.
    """
    # Step 1: Load Market data
    documents_data = data_news_articles_blobs('news_article-bucket_preprocessed')

    # Step 2: Initialize Pinecone client
    pinecone_client = initialize_pinecone_client(api_key=os.getenv("PINECONE_API_KEY"))

    # Step 3: Create or connect to Pinecone index
    index = create_or_connect_index(pinecone_client, index_name, dimension=384, metric="cosine")

    # Step 4: Set up vector store and embedding model
    storage_context = setup_vector_store(index)
    set_embedding_model()

    # Step 5: Create the vector store index from documents
    vector_store_index = create_index_from_documents(documents_data, storage_context)

if __name__ == "__main__":
    load_dotenv()
    main(index_name="financial_news_index")
