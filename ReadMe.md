# RAG-based Financial Analysis Chatbot

In the rapidly evolving financial landscape, rapid access to accurate information is crucial for making informed, high-stakes decisions. To meet this demand, we propose the development of a Retrieval-Augmented Generation (RAG)-based chatbot designed for fast and efficient information retrieval in the financial sector. By leveraging comprehensive datasets, including real-time stock prices and financial news, this chatbot delivers precise answers, insightful analysis, and up-to-date information to its users.

By integrating advanced natural language processing (NLP) with robust, real-time data sources, our solution aims to enhance user experience, streamline the information retrieval process, and enable financial professionals to make swift, data-driven decisions. This chatbot will empower traders and finance experts by providing tailored, real-time insights, helping them maintain a competitive edge in the face of a dynamic market environment.

# Chatbot UI:

![image](https://github.com/user-attachments/assets/2d89614a-8788-4190-9f9d-c0286dd2fcd2)

<img width="1352" alt="s2" src="https://github.com/user-attachments/assets/4d4df974-8511-4e03-81f4-e73a3adfafa7" />

<img width="1352" alt="s1" src="https://github.com/user-attachments/assets/8594d68b-7bb3-447d-a0c0-d1b8f982f4a0" />


# Fine-Tuned ChatGPT-4 Model
<img width="1512" alt="Screenshot 2024-12-11 at 12 57 24 AM" src="https://github.com/user-attachments/assets/f82bb29f-297a-4a8d-b29a-bdda7abe64f1">

<img width="1512" alt="Screenshot 2024-12-11 at 12 56 43 AM" src="https://github.com/user-attachments/assets/e4b7861c-5011-4899-a1d0-0d512ade1ce6">

# Alerts:
<img width="1278" alt="image" src="https://github.com/user-attachments/assets/4e1b4be9-7991-4da2-abd2-9b057565f272">


# Dataset Information:

The core of our RAG-based chatbot is built upon two key datasets: stock prices and financial news.

Stock Prices: This dataset includes both historical and real-time market data, such as opening, closing, high, and low prices, trading volumes, and other key financial indicators. It provides the quantitative foundation for analyzing market trends, conducting technical analysis, and making data-driven financial forecasts.

Financial News: This dataset encompasses articles, press releases, and reports from reputable financial outlets. It offers qualitative insights into market sentiment, company performance, economic indicators, and other factors that influence stock prices. Financial news is essential for understanding the broader context of market movements and investor behavior.

Together, these datasets empower the chatbot to deliver comprehensive, context-aware responses. By combining quantitative data with qualitative insights, the chatbot can provide robust, accurate, and timely information to support critical financial decision-making.


# Data Source:

To ensure the reliability and comprehensiveness of our datasets following sources are used:

Stock Prices:

Yahoo Finance API: Provides real-time and historical stock data, including prices and trading volumes.
Financial News:

Polygon: Aggregates financial news, offering timely updates on market trends and company performance.
These sources supply the essential data for the chatbot. APIs allow seamless integration for real-time data, and web scraping is used where necessary to collect additional news articles.

Flow Chart for the approach <img width="962" alt="Screenshot 2024-10-01 at 9 49 50 PM" src="https://github.com/user-attachments/assets/5db6837d-094b-471e-b194-c07248fd35f8">

Tools & Technologies:

Flask: A lightweight framework for building the chatbot's backend and API services.
Streamlit: A framework for rapidly developing and deploying interactive web interfaces for financial data visualization.
ChatGPT Fine-tuning: Customizing GPT to provide specialized financial analysis and insights.
Google Cloud: For scalable cloud infrastructure and data storage.
Cloud Run: Deploying containerized applications for high availability and autoscaling.
Docker: Containerizing the application for consistency across development and production environments.
AWS Cloud: For hosting, storage, and resource management.
Pincone : Utilizing Pincone DB on AWS Cloud for efficient vector-based search and retrieval of financial data.


# Cost Analysis:
Since we are using the GCP environment, the cost of resources is relatively low. Each application deployment server costs around $25 per month. To utilize an efficient, custom fine-tuned ChatGPT-4 model, we will require a fine-tuning billing plan priced at $5 per 1M request hits, along with a subscription cost of $20.
