"""
Streamlit UI for AI Command Center
"""

import streamlit as st
import requests
import json
import os
from typing import Optional

# Configure page
st.set_page_config(
    page_title="AI Command Center",
    page_icon="🤖",
    layout="wide"
)

# API Configuration - check env vars first (for Render), then secrets, then defaults
API_BASE_URL = os.getenv("API_BASE_URL") or st.secrets.get("API_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY") or st.secrets.get("API_KEY", "dev-key-change-in-production")

# Custom CSS
st.markdown("""
<style>
.main-header {
    font-size: 3rem;
    font-weight: bold;
    text-align: center;
    margin-bottom: 2rem;
}
.agent-card {
    padding: 1rem;
    border-radius: 0.5rem;
    border: 1px solid #ddd;
    margin: 0.5rem 0;
}
.stat-box {
    padding: 1rem;
    border-radius: 0.5rem;
    background-color: #f0f2f6;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# Title
st.markdown('<h1 class="main-header">🤖 AI Command Center</h1>', unsafe_allow_html=True)
st.markdown("**Multi-Agent AI System** - Research • Documents • Code Review")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    
    # API Status
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=2)
        if response.status_code == 200:
            st.success("✅ API Connected")
        else:
            st.error("❌ API Error")
    except:
        st.error("❌ API Offline")
    
    st.divider()
    
    # Stats
    st.header("📊 Usage Stats")
    
    if st.button("Refresh Stats"):
        try:
            response = requests.get(
                f"{API_BASE_URL}/stats",
                headers={"Authorization": f"Bearer {API_KEY}"},
                timeout=5
            )
            
            if response.status_code == 200:
                stats = response.json()
                
                # Manager stats
                st.subheader("Manager Agent")
                st.metric("Total Requests", stats["manager"]["total_requests"])
                st.metric("Total Cost", f"${stats['manager']['total_cost']:.4f}")
                
                # Specialist stats
                st.subheader("Specialists")
                for agent_name, agent_stats in stats["specialists"].items():
                    with st.expander(agent_name):
                        st.metric("Requests", agent_stats["total_requests"])
                        st.metric("Cost", f"${agent_stats['total_cost']:.4f}")
            else:
                st.error("Failed to fetch stats")
                
        except Exception as e:
            st.error(f"Error: {str(e)}")
    
    st.divider()
    
    # About
    st.header("ℹ️ About")
    st.markdown("""
    This AI Command Center uses multiple specialized agents:
    
    - **Research Agent**: Web search & analysis
    - **RAG Agent**: Document Q&A
    - **Code Review Agent**: Code analysis
    
    A manager agent intelligently routes your queries to the right specialists.
    """)

# Main content
tab1, tab2, tab3 = st.tabs(["💬 Chat", "📄 Documents", "🔍 Code Review"])

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

with tab1:
    st.header("Chat with AI")
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Show metadata if available
            if message["role"] == "assistant" and "metadata" in message:
                with st.expander("📊 Details"):
                    metadata = message["metadata"]
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Cost", f"${metadata.get('total_cost', 0):.4f}")
                    with col2:
                        agents_used = metadata.get('agents_used', [])
                        st.metric("Agents Used", len(agents_used))
                    with col3:
                        successful = metadata.get('agents_successful', 0)
                        st.metric("Successful", successful)
                    
                    if agents_used:
                        st.write("**Agents:**", ", ".join(agents_used))
    
    # Chat input
    if prompt := st.chat_input("Ask me anything..."):
        # Add user message
        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/query",
                        headers={
                            "Authorization": f"Bearer {API_KEY}",
                            "Content-Type": "application/json"
                        },
                        json={"query": prompt},
                        timeout=120
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        answer = result["answer"]
                        metadata = result.get("metadata", {})
                        
                        st.markdown(answer)
                        
                        # Store assistant message
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": answer,
                            "metadata": metadata
                        })
                        
                        # Show details
                        with st.expander("📊 Details"):
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Cost", f"${metadata.get('total_cost', 0):.4f}")
                            with col2:
                                agents_used = metadata.get('agents_used', [])
                                st.metric("Agents Used", len(agents_used))
                            with col3:
                                successful = metadata.get('agents_successful', 0)
                                st.metric("Successful", successful)
                            
                            if agents_used:
                                st.write("**Agents:**", ", ".join(agents_used))
                    
                    else:
                        error_msg = f"API Error: {response.status_code}"
                        st.error(error_msg)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": error_msg
                        })
                        
                except Exception as e:
                    error_msg = f"Error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })
    
    # Clear chat button
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()

with tab2:
    st.header("Document Upload (RAG)")

    st.markdown("Upload documents to build your knowledge base. The RAG agent will use these documents to answer questions.")

    # Two columns: upload and document list
    col_upload, col_docs = st.columns([1, 1])

    with col_upload:
        st.subheader("📤 Upload Document")

        uploaded_file = st.file_uploader(
            "Choose a file",
            type=["pdf", "txt", "md"],
            help="Upload PDF, TXT, or Markdown files",
            key="doc_uploader"
        )

        if uploaded_file:
            st.info(f"Selected: **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)")

            if st.button("📥 Index Document", type="primary"):
                with st.spinner(f"Processing {uploaded_file.name}..."):
                    try:
                        # Upload to backend
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
                        response = requests.post(
                            f"{API_BASE_URL}/documents/upload",
                            headers={"Authorization": f"Bearer {API_KEY}"},
                            files=files,
                            timeout=120
                        )

                        if response.status_code == 200:
                            result = response.json()
                            st.success(f"Document indexed successfully!")

                            # Show details
                            st.markdown(f"""
                            - **Chunks created:** {result.get('chunks_created', 'N/A')}
                            - **Text length:** {result.get('text_length', 'N/A'):,} characters
                            - **Total documents in DB:** {result.get('total_documents', 'N/A')}
                            """)

                            # Trigger refresh
                            st.rerun()
                        else:
                            error_detail = response.json().get("detail", "Unknown error")
                            st.error(f"Failed to index: {error_detail}")

                    except Exception as e:
                        st.error(f"Error: {str(e)}")

    with col_docs:
        st.subheader("📚 Indexed Documents")

        # Fetch document list
        try:
            response = requests.get(
                f"{API_BASE_URL}/documents",
                headers={"Authorization": f"Bearer {API_KEY}"},
                timeout=10
            )

            if response.status_code == 200:
                doc_data = response.json()
                sources = doc_data.get("sources", [])
                total_chunks = doc_data.get("total_chunks", 0)

                # Stats
                st.metric("Total Chunks", total_chunks)
                st.metric("Files Indexed", len(sources))

                if sources:
                    st.divider()
                    st.markdown("**Files:**")

                    for source in sources:
                        col_name, col_del = st.columns([4, 1])
                        with col_name:
                            st.text(f"📄 {source}")
                        with col_del:
                            if st.button("🗑️", key=f"del_{source}", help=f"Delete {source}"):
                                try:
                                    del_response = requests.delete(
                                        f"{API_BASE_URL}/documents/{source}",
                                        headers={"Authorization": f"Bearer {API_KEY}"},
                                        timeout=10
                                    )
                                    if del_response.status_code == 200:
                                        st.success(f"Deleted {source}")
                                        st.rerun()
                                    else:
                                        st.error("Failed to delete")
                                except Exception as e:
                                    st.error(f"Error: {str(e)}")
                else:
                    st.info("No documents indexed yet. Upload a file to get started!")
            else:
                st.warning("Could not fetch document list")

        except Exception as e:
            st.error(f"Error loading documents: {str(e)}")

    # Document Q&A section
    st.divider()
    st.subheader("💬 Ask About Your Documents")

    doc_question = st.text_input(
        "Ask a question about your documents",
        placeholder="What does the documentation say about...",
        key="doc_question"
    )

    if doc_question:
        if st.button("🔍 Get Answer", type="primary", key="ask_docs_btn"):
            with st.spinner("Searching documents and generating answer..."):
                try:
                    # Use the main query endpoint which routes to RAG agent
                    response = requests.post(
                        f"{API_BASE_URL}/query",
                        headers={
                            "Authorization": f"Bearer {API_KEY}",
                            "Content-Type": "application/json"
                        },
                        json={"query": f"Search my documents and answer: {doc_question}"},
                        timeout=120
                    )

                    if response.status_code == 200:
                        result = response.json()
                        st.markdown("### Answer")
                        st.markdown(result["answer"])

                        # Show metadata
                        metadata = result.get("metadata", {})
                        with st.expander("📊 Details"):
                            st.write(f"**Cost:** ${metadata.get('total_cost', 0):.4f}")
                            st.write(f"**Agents used:** {', '.join(metadata.get('agents_used', []))}")
                    else:
                        st.error(f"Failed to get answer: {response.status_code}")

                except Exception as e:
                    st.error(f"Error: {str(e)}")

    # Raw document search (for debugging/preview)
    st.divider()
    with st.expander("🔧 Raw Document Search (Debug)"):
        st.caption("This shows raw document chunks without LLM processing")

        raw_search_query = st.text_input(
            "Search query",
            placeholder="Search your documents...",
            key="raw_search"
        )

        if raw_search_query:
            with st.spinner("Searching..."):
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/documents/search",
                        headers={"Authorization": f"Bearer {API_KEY}"},
                        params={"query": raw_search_query, "n_results": 5},
                        timeout=30
                    )

                    if response.status_code == 200:
                        results = response.json()

                        if results.get("results"):
                            st.success(f"Found {results['count']} chunks")

                            for i, result in enumerate(results["results"], 1):
                                with st.expander(f"Chunk {i} - {result['metadata'].get('source', 'Unknown')}"):
                                    st.markdown(f"**Source:** {result['metadata'].get('source', 'Unknown')}")
                                    st.markdown(f"**Relevance:** {1 - result.get('distance', 0):.2%}")
                                    st.markdown("**Content:**")
                                    st.text(result["text"][:500] + "..." if len(result["text"]) > 500 else result["text"])
                        else:
                            st.info("No results found")
                    else:
                        st.error("Search failed")

                except Exception as e:
                    st.error(f"Error: {str(e)}")

with tab3:
    st.header("Code Review")
    
    st.markdown("Paste your code below for an AI-powered review.")
    
    code = st.text_area(
        "Code to review",
        height=300,
        placeholder="# Paste your code here..."
    )
    
    if st.button("🔍 Review Code"):
        if code.strip():
            with st.spinner("Analyzing code..."):
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/query",
                        headers={
                            "Authorization": f"Bearer {API_KEY}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "query": f"Please review this code:\n\n```\n{code}\n```",
                            "context": {"code": code}
                        },
                        timeout=120
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.markdown("### Review Results")
                        st.markdown(result["answer"])
                    else:
                        st.error(f"API Error: {response.status_code}")
                        
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        else:
            st.warning("Please enter some code to review")