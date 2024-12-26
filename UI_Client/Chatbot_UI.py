import streamlit as st
import requests

# Function to query the Flask app
def query_flask_app(prompt):
    try:
        # Payload to send to the Flask app
        payload = {"query": prompt}

        # Send POST request
        response = requests.post(os.getenv("FLASK_APP_URL"), json=payload)

        # Check if the request was successful
        if response.status_code == 200:
            # Parse the JSON response
            response_data = response.json()
            if "answer" in response_data:
                return response_data["answer"]
            else:
                # Debugging: Show the full response content if 'answer' key is missing
                st.error(f"Unexpected response format: {response_data}")
                return "Oops! I got an unexpected response from the server. 🤔"
        else:
            # Log the status code and response content for debugging
            st.error(f"Flask app query failed with status code: {response.status_code}")
            st.error(f"Response content: {response.text}")
            return "Hmm, the server seems to be snoozing. Try again later! 😴"
    except Exception as e:
        # Log the exception details
        st.error(f"An error occurred: {e}")
        return "Yikes! Something went wrong while contacting the server. 🚨"

# Function to increment counter using the REST API
def update_counter(inc_factor=1):
    try:
        # Construct the payload for increment or decrement
        payload = {"increment_by": inc_factor}

        # Make a POST request to the counter API with the payload
        response = requests.post(os.getenv("COUNTER_API_URL"), json=payload)

        # Check if the request was successful
        if response.status_code == 200:
            response_data = response.json()
            if "count" in response_data:  # Assume the API returns the updated count
                return response_data["count"]
            else:
                st.error(f"Unexpected response format: {response_data}")
                return None
        else:
            st.error(f"Failed to increment counter. Status code: {response.status_code}")
            st.error(f"Response content: {response.text}")
            return None
    except Exception as e:
        st.error(f"An error occurred while incrementing counter: {e}")
        return None

# Main function for the app
def main():

    # Page state management
    if "page" not in st.session_state:
        st.session_state.page = "home"  # Default to the home page

    # Home Page
    if st.session_state.page == "home":
        st.title("Welcome to Your Financial Assistant Bot! 💸")
        st.write("""
        ### Meet Your Intelligent Financial Assistant:
        🚀 Our financial bot is designed to simplify your interactions with financial data.
        With cutting-edge AI capabilities, it can:
        - **Analyze trends** in stock prices.
        - **Summarize financial news** for faster decision-making.
        - **Provide market insights** in seconds.

        Whether you're a trader, an investor, or simply curious about the market, this bot is here to assist you.

        🤖 **Why this bot?**
        - Always up-to-date with the latest financial trends.
        - Simple, intuitive, and lightning-fast responses.
        - Built on state-of-the-art AI technology to give you the edge in financial insights.
        """)
        st.write("Click below to start exploring!")

        # "Try Me" button
        if st.button("Try Me"):
            st.session_state.page = "chatbot"

    # Chatbot Page
    elif st.session_state.page == "chatbot":
        st.title("Financial News & Stock Price Chatbot")
        st.write("👋 Welcome! Ask me about financial news or stock prices.")

        # User input
        user_input = st.text_input("Enter your query:", placeholder="Type here...")

        # Handle query
        if st.button("Send"):
            if user_input:
                with st.spinner("Processing..."):
                    response = query_flask_app(user_input)
                st.success("Response:")
                st.write(response)

                # Feedback buttons
                col1, col2 = st.columns(2)
                with col1:
                    thumbs_up_button = st.button("👍 Thumbs Up")
                with col2:
                    thumbs_down_button = st.button("👎 Thumbs Down")

                # Handle thumbs up or thumbs down feedback
                if thumbs_up_button:
                    st.write("You liked the response! 👍 Counter updated.")
                    update_counter(inc_factor=1)  # Increment the counter by 1

                if thumbs_down_button:
                    st.write("You disliked the response. 👎 Counter updated.")
                    update_counter(inc_factor=-1)  # Decrement the counter by 1
            else:
                st.warning("Please enter a query.")

# Run the app
if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()
    main()
