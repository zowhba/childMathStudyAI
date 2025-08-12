import streamlit as st
import chromadb
import pandas as pd
import os

# --- Configuration ---
DB_PATH = "chroma_db"
st.set_page_config(page_title="ChromaDB Viewer", layout="wide")

# --- Helper Functions ---
@st.cache_resource
def get_chroma_client():
    """Create and cache a ChromaDB client."""
    if not os.path.exists(DB_PATH):
        st.error(f"Database path '{DB_PATH}' not found. Please make sure the database is in the correct directory.")
        return None
    return chromadb.PersistentClient(path=DB_PATH)

def get_collections(_client):
    """Get all collections from the client."""
    if _client:
        return [c.name for c in _client.list_collections()]
    return []

def get_collection_data(_client, collection_name):
    """Fetch all data from a specific collection and return as a DataFrame."""
    if not _client or not collection_name:
        return pd.DataFrame()

    try:
        collection = _client.get_collection(name=collection_name)
        data = collection.get(include=["metadatas", "documents"])
        
        # Combine ids, metadatas, and documents into a list of dictionaries
        combined_data = []
        for i, doc_id in enumerate(data['ids']):
            item = {
                'id': doc_id,
                'document': data['documents'][i],
                **data['metadatas'][i]
            }
            combined_data.append(item)
            
        return pd.DataFrame(combined_data)

    except Exception as e:
        st.error(f"Failed to load data from collection '{collection_name}': {e}")
        return pd.DataFrame()

# --- Streamlit UI ---
st.title("🔍 ChromaDB Viewer")

client = get_chroma_client()

if client:
    collections = get_collections(client)
    
    if not collections:
        st.warning("No collections found in the database.")
    else:
        st.sidebar.header("Collections")
        selected_collection = st.sidebar.selectbox(
            "Select a collection to view:",
            options=collections
        )
        
        if selected_collection:
            st.header(f"Data from: `{selected_collection}`")
            with st.spinner(f"Loading data from '{selected_collection}'..."):
                df = get_collection_data(client, selected_collection)
                
                if not df.empty:
                    st.dataframe(df, use_container_width=True)
                    st.info(f"Found **{len(df)}** documents in this collection.")
                else:
                    st.warning("No data found in this collection or failed to load.")
else:
    st.info("Could not connect to ChromaDB. Please check the path and ensure the database exists.") 