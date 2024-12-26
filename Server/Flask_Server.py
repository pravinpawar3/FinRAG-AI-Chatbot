import os
import logging
import json
import torch
import faiss
import numpy as np
import openai
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from google.cloud import storage
import firebase_admin
from firebase_admin import credentials, db
import pyarrow.parquet as pq
from llama_index.llms.openai import OpenAI
from openai import OpenAI as OpenAIClient
from pinecone import Pinecone, ServerlessSpec, PineconeVectorStore
from dotenv import load_dotenv  # Import dotenv for loading environment variables

# Set up logging
logging.basicConfig(level=logging.INFO)  # Set the log level to INFO for general application logs
logger = logging.getLogger(__name__)  # Create a logger instance

# Initialize Flask app
app = Flask(__name__)  # Flask app to handle web requests

# Initialize Firebase DB reference globally
ref = None  # Firebase reference for alert counter

# Initialize Pinecone client
def initialize_pinecone_client(api_key: str):
    """Initialize the Pinecone client with the provided API key and environment."""
    return Pinecone(api_key=api_key, environment="us-west1-gcp")

# Create or connect to Pinecone index
def create_or_connect_index(pinecone_client, index_name: str, dimension: int, metric: str):
    """
    Create a new Pinecone index if it doesn't exist, or connect to an existing one.
    :param pinecone_client: The Pinecone client instance.
    :param index_name: Name of the index to connect to or create.
    :param dimension: Dimension of the vector space (e.g., 128, 256).
    :param metric: Distance metric to use (e.g., cosine).
    :return: Pinecone index instance.
    """
    pinecone_client_names = pinecone_client.list_indexes()  # List available Pinecone indexes
    if index_name not in pinecone_client_names:  # If index doesn't exist, create it
        logger.info(f"Creating index {index_name}...")
        pinecone_client.create_index(
            name=index_name,
            dimension=dimension,
            metric=metric,
            spec=ServerlessSpec(cloud="aws", region="us-east-1")  # Define serverless configuration
        )
    else:
        logger.info(f"Index {index_name} already exists.")
    return pinecone_client.Index(index_name)  # Return the index

# Fetch vectors from Pinecone index
def fetch_vectors_in_index(index):
    """
    Set up the Pinecone vector store and return the storage context.
    :param index: The Pinecone index instance.
    :return: VectorStoreIndex object for querying.
    """
    vector_store = PineconeVectorStore(pinecone_index=index)  # Create vector store for the index
    storage_context = StorageContext.from_defaults(vector_store=vector_store)  # Default storage context
    return VectorStoreIndex.from_vector_store(vector_store=vector_store, storage_context=storage_context)

# Set embedding model for vector generation
def set_embedding_model():
    """Set the embedding model for vector generation."""
    Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")  # Load the model

# Fine-tuned OpenAI class to query the fine-tuned GPT model
class FineTunedOpenAI(OpenAI):
    def query(self, prompt: str) -> str:
        """
        Call the OpenAI API with the fine-tuned model for query generation.
        :param prompt: The input question or prompt to ask.
        :return: The response from the fine-tuned GPT model.
        """
        try:
            response = openai.ChatCompletion.create(
                messages=[{"role": "user", "content": f"For question: {prompt} and given relevant content"}],
                model=os.getenv("FINE_TUNED_MODEL")  # Get fine-tuned model name from environment variables
            )
            return response['choices'][0]['message']['content']
        except Exception as e:
            logger.error(f"Error in query: {e}")
            return "Error generating response"  # Return error message if query fails

# Load retrieval engine with a fine-tuned model
def load_retrieval_engine(index):
    """
    Load the retrieval engine with a fine-tuned model for querying.
    :param index: The Pinecone index to use.
    :return: Query engine instance.
    """
    llm = FineTunedOpenAI()  # Initialize the fine-tuned OpenAI model
    query_engine = index.as_query_engine(llm=llm, num_results=5)  # Set up query engine with 5 results
    return query_engine

# Retrieve the top-k relevant documents based on the query
def retrieve_context(query, query_engine, k=5):
    """
    Retrieve the top-k documents relevant to the query using the query engine.
    :param query: The query string.
    :param query_engine: The query engine instance.
    :param k: Number of top documents to retrieve.
    :return: List of top-k document texts.
    """
    logger.info("Retrieving context for the query...")
    response = query_engine.query(query)  # Query the engine for relevant documents
    top_5_documents = [node.node.text for node in response.source_nodes]  # Extract text from response nodes
    return top_5_documents

# Generate an answer using the fine-tuned GPT model
def generate_answer_with_fine_tuned_gpt(query, retrieved_docs):
    """
    Generate an answer using the fine-tuned GPT model based on retrieved context.
    :param query: The original query string.
    :param retrieved_docs: List of documents retrieved by the query engine.
    :return: The generated answer.
    """
    logger.info("Generating answer with the fine-tuned model...")
    context = " ".join(retrieved_docs)  # Combine retrieved documents into a single context string

    try:
        # Call the OpenAI API with the query and the retrieved context
        response = OpenAIClient(api_key=os.getenv("OPENAI_API_KEY")).chat.completions.create(
            messages=[{"role": "user", "content": f"For question: {query} and given relevant content: {context}"}],
            model=os.getenv("FINE_TUNED_MODEL")
        )
        return response.choices[0].message.content  # Return the model's generated content
    except Exception as e:
        logger.error(f"Error generating answer: {e}")
        return "Failed to get response from fine-tuned model."  # Return error if generation fails

# Update the alert counter in Firebase database
def update_alert_counter(increment_factor):
    """Increment the alert counter in Firebase DB."""
    try:
        current_count = ref.child('count').get() or 0  # Get current count or initialize to 0 if not present
        new_count = current_count + increment_factor  # Increment factor
        if new_count > os.getenv("RETRAINING_THRESHOLD"):
            send_direct_slack_message(os.getenv("SLACK_WEBHOOK_URL"))
        ref.update({'count': new_count})  # Update counter in Firebase
    except Exception as e:
        logger.error(f"Error updating counter: {e}")
        return jsonify({"error": "Failed to update counter"}), 500  # Return error if update fails

# Send Slack Notification for retraining model
def send_direct_slack_message(webhook_url):
    """
    Sends a direct message to a Slack channel using a webhook URL.

    Parameters:
    - webhook_url: str, The Slack Incoming Webhook URL.
    """
    message="🔔 Alert: Model training/fine tunining is required to improve results!"
    payload = {
        "text": message
    }
    try:
        response = requests.post(webhook_url, json=payload)
        if response.status_code == 200:
            print("Message sent successfully!")
        else:
            print(f"Failed to send message: {response.status_code}, {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending message: {e}")

# Load config, models, and initialize Firebase DB at startup
@app.before_first_request
def before_first_request():
    """
    Initialize necessary services (Pinecone, Firebase, etc.) before handling requests.
    """
    try:
        global query_engine
        # Initialize Pinecone client and query engine
        pinecone_client = initialize_pinecone_client(os.getenv("PINECONE_API_KEY"))
        index = create_or_connect_index(pinecone_client, os.getenv("INDEX_NAME"), 128, "cosine")
        query_engine = load_retrieval_engine(index)  # Load the query engine with fine-tuned model
        firebase_admin.initialize_app(
            credentials.Certificate(os.getenv("FIREBASE_ACCOUNT_KEY")),  # Firebase initialization
            {'databaseURL': os.getenv("FIREBASE_DB_URL")}
        )
        global ref
        ref = db.reference('/incorrect_response_counter')  # Reference to Firebase counter
        logger.info("Configuration and Firebase initialized successfully.")
    except Exception as e:
        logger.error(f"Error during app initialization: {e}")
        raise e  # Raise error to prevent further execution if initialization fails

@app.route("/predict", methods=["POST"])
def predict():
    """
    Endpoint to generate a prediction using the fine-tuned GPT model.
    Accepts a POST request with a JSON body containing the query.
    """
    try:
        data = request.json  # Get the incoming JSON request data
        query = data.get("query")  # Extract query from the request

        # Retrieve relevant documents and generate the answer
        retrieved_docs = retrieve_context(query, query_engine)
        answer = generate_answer_with_fine_tuned_gpt(query, retrieved_docs)

        logger.info("Prediction successful.")
        return jsonify({"answer": answer})  # Return the generated answer in JSON format
    except Exception as e:
        logger.error(f"Error during prediction: {e}")
        return jsonify({"error": "An error occurred during prediction.", "details": str(e)}), 500  # Return error message

@app.route("/health", methods=["GET"])
def health_check():
    """Endpoint to check the health of the API."""
    return jsonify({"status": "healthy"}), 200  # Return a health status message

@app.route('/increment_counter', methods=['POST'])
def increment_counter():
    """
    Increment the counter for user feedback.
    Increments the count stored in Firebase and returns the updated value.
    """
    # Get the increment factor (default to 0 if not provided)
    increment_factor = request.json.get("increment_by", 0)
    update_alert_counter(increment_factor)  # Update the Firebase counter
    counter_value = ref.child('counter').get()  # Get the updated counter value
    return jsonify({'counter': counter_value}), 200  # Return the updated counter in the response

# Run the app
if __name__ == "__main__":
    load_dotenv()  # Ensure environment variables are loaded from .env file
    app.run(host="0.0.0.0", port=8085)  # Run the Flask app on port 8085
