import streamlit as st
import requests
from datetime import datetime
from typing import List, Dict, Any
import json

# Backend configuration
BACKEND_URL = "https://agentic-backend-x5i7.onrender.com"  
CHAT_ENDPOINT = f"{BACKEND_URL}/chat"
UPLOAD_ENDPOINT = f"{BACKEND_URL}/process-documents"

st.set_page_config(
    page_title="Agentic Chatbot",
    page_icon="🤖",
    layout="wide"
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "agent_thinking" not in st.session_state:
    st.session_state.agent_thinking = False
if "uploaded_docs" not in st.session_state:
    st.session_state.uploaded_docs = []
if "processed_documents" not in st.session_state:
    st.session_state.processed_documents = []
if "current_agent" not in st.session_state:
    st.session_state.current_agent = "Generic News Agent"

def test_backend_connection():
    """Test if backend is reachable"""
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        return response.status_code == 200, response.status_code
    except requests.exceptions.ConnectionError:
        return False, "Connection refused"
    except requests.exceptions.Timeout:
        return False, "Timeout"
    except Exception as e:
        return False, str(e)

def reset_session():
    """Reset session state for new agent session"""
    st.session_state.messages = []
    st.session_state.agent_thinking = False
    st.session_state.uploaded_docs = []
    st.session_state.processed_documents = []

def upload_documents_to_backend(uploaded_files) -> List[Dict[str, Any]]:
    """Upload documents to backend and return processed document info"""
    if not uploaded_files:
        return []
    
    try:
        files = []
        for uploaded_file in uploaded_files:
            # Reset file pointer to beginning
            uploaded_file.seek(0)
            files.append(('files', (uploaded_file.name, uploaded_file.read(), uploaded_file.type)))
        
        response = requests.post(UPLOAD_ENDPOINT, files=files, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            return result.get('documents', [])
        else:
            st.error(f"Failed to upload documents: {response.text}")
            return []
            
    except Exception as e:
        st.error(f"Error uploading documents: {str(e)}")
        return []

def get_agent_response(user_message: str, selected_agent: str, processed_docs: List[Dict[str, Any]]) -> str:
    """Get response from the backend API"""
    try:
        # Convert chat history to the format expected by backend
        chat_history = []
        for msg in st.session_state.messages[:-1]:  # Exclude the current message
            chat_history.append({
                "role": msg["role"],
                "content": msg["content"],
                "timestamp": msg.get("timestamp", datetime.now().strftime("%H:%M:%S"))
            })
        
        # Prepare the request payload to match your working curl command
        payload = {
            "message": user_message,
            "agent_type": selected_agent,
            "chat_history": chat_history
        }
        
        # Add documents only if using Doc Chat Agent and documents are available
        if selected_agent == "Doc Chat Agent" and processed_docs:
            payload["documents"] = [{"filename": doc["stored_filename"]} for doc in processed_docs]
        
        # Make the API call with proper headers
        response = requests.post(
            CHAT_ENDPOINT,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            timeout=120  # 2 minutes timeout for long operations
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get("response", "No response received")
        else:
            # Better error handling
            try:
                error_detail = response.json().get("detail", "Unknown error")
            except:
                error_detail = response.text
            return f"❌ Error (Status {response.status_code}): {error_detail}"
            
    except requests.exceptions.Timeout:
        return "⏱️ Request timed out. The agent is taking too long to process your request."
    except requests.exceptions.ConnectionError:
        return "🔌 Connection error. Please make sure the backend server is running"
    except requests.exceptions.RequestException as e:
        return f"🌐 Network error: {str(e)}"
    except json.JSONDecodeError:
        return "📦 Invalid JSON response from backend"
    except Exception as e:
        return f"❌ Unexpected error: {str(e)}"

# Sidebar
with st.sidebar:
    st.header("🔧 System Status")
    
    # Backend connection test
    with st.spinner("Testing backend connection..."):
        is_connected, status = test_backend_connection()
    
    if is_connected:
        st.success("🟢 Backend Connected")
    else:
        st.error(f"🔴 Backend Offline: {status}")
        st.write("**Troubleshooting:**")
        st.write("1. Make sure backend is running")
        st.write("2. Check if /health endpoint exists")
        st.write("3. Verify no firewall/port blocking")
    
    # Agent status
    if st.session_state.agent_thinking:
        st.status("🤔 Agent is thinking...", state="running")
    else:
        st.status("✅ Ready to assist", state="complete")

    st.markdown("---")
    st.subheader("🤖 Agent Selection")
    selected_agent = st.radio(
        "Choose an agent:", 
        ["Generic News Agent", "Doc Chat Agent"]
    )
    
    # Check if agent changed and reset session if needed
    if selected_agent != st.session_state.current_agent:
        reset_session()
        st.session_state.current_agent = selected_agent
        st.rerun()
    
    # Document upload section
    if selected_agent == "Doc Chat Agent":
        st.subheader("📄 Document Upload")
        uploaded_files = st.file_uploader(
            "Upload documents:", 
            accept_multiple_files=True,
            type=['txt', 'pdf', 'docx', 'xlsx', 'xls', 'csv', 'json', 'md'],
            help="Upload documents to analyze with the Doc Chat Agent"
        )
        
        # Process uploaded files
        if uploaded_files and uploaded_files != st.session_state.uploaded_docs:
            st.session_state.uploaded_docs = uploaded_files
            with st.spinner("Uploading and processing documents..."):
                processed_docs = upload_documents_to_backend(uploaded_files)
                st.session_state.processed_documents = processed_docs
            
            if processed_docs:
                st.success(f"✅ Successfully processed {len(processed_docs)} documents")
                with st.expander("View processed documents"):
                    for doc in processed_docs:
                        st.write(f"📄 **{doc['original_filename']}**")
                        st.write(f"   - Size: {doc['size']} bytes")
                        st.write(f"   - Type: {doc['content_type']}")
                        st.write(f"   - Stored as: {doc['stored_filename']}")
        
        # Show current documents
        if st.session_state.processed_documents:
            st.info(f"📚 {len(st.session_state.processed_documents)} documents ready for analysis")
        else:
            st.warning("📝 No documents uploaded yet")
    else:
        # Clear documents when not using Doc Chat Agent
        if st.session_state.uploaded_docs or st.session_state.processed_documents:
            st.session_state.uploaded_docs = []
            st.session_state.processed_documents = []
    
    st.markdown("---")
    
    # Session management
    st.subheader("🔄 Session Management")
    if st.button("🆕 New Session", help="Clear chat history and start fresh"):
        reset_session()
        st.success("✅ New session started!")
        st.rerun()

# Main chat interface
st.title("🤖 Agentic Chatbot")
st.markdown("**Your intelligent AI assistant for various tasks**")

# Show connection warning if backend is not connected
is_connected, _ = test_backend_connection()
if not is_connected:
    st.error("⚠️ **Backend Connection Issue**: The chat functionality may not work properly. Please check the backend server.")

# Show agent info
if selected_agent == "Generic News Agent":
    st.info("📰 **Generic News Agent** - Ask me about current events and news!")
elif selected_agent == "Doc Chat Agent":
    if st.session_state.processed_documents:
        st.info(f"📚 **Doc Chat Agent** - Ready to analyze {len(st.session_state.processed_documents)} uploaded documents!")
    else:
        st.warning("📝 **Doc Chat Agent** - Upload documents in the sidebar to get started!")

# Chat Container
chat_container = st.container()
with chat_container:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "timestamp" in message:
                st.caption(f"*{message['timestamp']}*")

# Chat Input
if prompt := st.chat_input("Ask me anything...", disabled=not is_connected):
    if not is_connected:
        st.error("Cannot send message: Backend is not connected")
    else:
        timestamp = datetime.now().strftime("%H:%M:%S")
        st.session_state.messages.append({
            "role": "user",
            "content": prompt,
            "timestamp": timestamp
        })

        with st.chat_message("user"):
            st.markdown(prompt)
            st.caption(f"*{timestamp}*")

        with st.chat_message("assistant"):
            st.session_state.agent_thinking = True
            
            # Show different loading messages based on agent type
            if selected_agent == "Generic News Agent":
                loading_msg = "🔍 Searching for latest news and information..."
            else:
                if st.session_state.processed_documents:
                    loading_msg = f"📖 Analyzing {len(st.session_state.processed_documents)} documents..."
                else:
                    loading_msg = "🔍 Processing your request..."
            
            with st.spinner(loading_msg):
                response = get_agent_response(
                    prompt, 
                    selected_agent, 
                    st.session_state.processed_documents
                )

            st.session_state.agent_thinking = False
            st.markdown(response)

            response_timestamp = datetime.now().strftime("%H:%M:%S")
            st.caption(f"*{response_timestamp}*")

            st.session_state.messages.append({
                "role": "assistant",
                "content": response,
                "timestamp": response_timestamp
            })

# Footer with tips
st.markdown("---")
if selected_agent == "Generic News Agent":
    tip_text = "💡 **Pro Tip:** Ask about current events, trending topics, or breaking news!"
else:
    if st.session_state.processed_documents:
        tip_text = f"💡 **Pro Tip:** Your {len(st.session_state.processed_documents)} documents are ready! Ask specific questions about their content."
    else:
        tip_text = "💡 **Pro Tip:** Upload documents (PDF, Word, Excel, etc.) and ask questions about their content!"

st.markdown(f"""
<div style='text-align: center; color: #666;'>
    <small>{tip_text}</small>
</div>
""", unsafe_allow_html=True)