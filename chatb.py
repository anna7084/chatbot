import streamlit as st
import requests
import json
import time

# Set up Streamlit UI
st.title("Local LLM Chatbot")
st.write("Chat with a local language model")

# Sidebar for configuration
with st.sidebar:
    st.header("Configuration")
    model_name = st.text_input("Model Name", value="tinyllama")
    timeout_seconds = st.number_input("Timeout (seconds)", min_value=10, max_value=300, value=120)
    st.info("If you're getting timeout errors, increase this value.")
    
    # Add model information
    st.subheader("Available Models")
    if st.button("Refresh Model List"):
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                if models:
                    for model in models:
                        st.write(f"• {model['name']} ({model.get('size', 'size unknown')})")
                else:
                    st.write("No models found. Try pulling one with 'ollama pull tinyllama'")
            else:
                st.error(f"Error: {response.status_code}")
        except requests.exceptions.RequestException as e:
            st.error(f"Cannot connect to Ollama: {str(e)}")
            st.info("Make sure Ollama is running with 'ollama serve'")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "context" not in st.session_state:
    st.session_state.context = None

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Function to call the LLM API with improved error handling
def query_llm(prompt):
    # Prepare the payload - keeping it simple
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False
    }
    
    # Add context if available
    if st.session_state.context is not None:
        payload["context"] = st.session_state.context
    
    # Make the API request with the user-configured timeout
    try:
        # First check if Ollama is running
        try:
            requests.get("http://localhost:11434/", timeout=5)
        except:
            return "Error: Cannot connect to Ollama. Make sure it's running with 'ollama serve'"
            
        # Then make the actual request
        response = requests.post(
            "http://localhost:11434/api/generate", 
            json=payload, 
            timeout=timeout_seconds
        )
        
        if response.status_code != 200:
            return f"Error: {response.status_code} - {response.text}"
        
        result = response.json()
        
        # Store the context for the next request
        if "context" in result:
            st.session_state.context = result["context"]
            
        return result.get("response", "No response received")
    except requests.exceptions.ReadTimeout:
        return f"Error: The model took too long to respond (> {timeout_seconds} seconds). Try:\n1. Increasing the timeout in settings\n2. Using a smaller model\n3. Asking a simpler question"
    except requests.exceptions.RequestException as e:
        return f"Error: {str(e)}"

# Chat input
user_input = st.chat_input("Type your message...")

if user_input:
    # Display user message
    with st.chat_message("user"):
        st.write(user_input)
    
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Get response from LLM with progress indicator
    with st.status("Model is thinking... This may take a while for the first response.") as status:
        start_time = time.time()
        response = query_llm(user_input)
        elapsed_time = time.time() - start_time
        status.update(label=f"Done! Response took {elapsed_time:.2f} seconds", state="complete")
    
    # Display assistant response
    with st.chat_message("assistant"):
        st.write(response)
    
    # Add assistant response to history
    st.session_state.messages.append({"role": "assistant", "content": response})

# Add a clear button to reset the conversation
if st.button("Clear Conversation"):
    st.session_state.messages = []
    st.session_state.context = None
    st.experimental_rerun()

# Add troubleshooting tips at the bottom
with st.expander("Troubleshooting Tips"):
    st.markdown("""
    ### Common Issues:
    
    1. **Timeout Errors**: The model is taking too long to respond.
       - Increase the timeout setting in the sidebar
       - Use a smaller model like 'tinyllama:latest'
       - Make sure your computer has enough resources available
    
    2. **Connection Errors**: Cannot connect to Ollama.
       - Ensure Ollama is running with `ollama serve`
       - Check if the correct port (11434) is being used
    
    3. **First Response Delay**: The first response after starting Ollama is often slow.
       - Be patient, as the model needs to load into memory
    
    4. **Not Enough Memory**: If the model is too large for your system.
       - Try a smaller model
       - Close other memory-intensive applications
    """)