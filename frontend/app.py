import streamlit as st
import requests
from pathlib import Path
from dotenv import load_dotenv
import os
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import uvicorn
import numpy as np
from sentence_transformers import SentenceTransformer
from backend.app.retriever import FAISSRetriever
from backend.app.pdf_processor import process_pdf
from backend.app.llm_interface import generate_llm_response

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Verify HF_TOKEN
HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    logger.error("HF_TOKEN not found in .env file")
    raise ValueError("HF_TOKEN not found in .env file")

class Document:
    def __init__(self, text: str, metadata: Dict[str, Any] = None):
        self.text = text
        self.metadata = metadata or {}

class SemanticEmbedder:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Loaded embedding model: all-MiniLM-L6-v2")

    def embed_query(self, text: str) -> np.ndarray:
        return self.model.encode(text, convert_to_numpy=True)

    def embed_documents(self, texts: List[str]) -> np.ndarray:
        return self.model.encode(texts, convert_to_numpy=True)

class EnhancedFAISSRetriever:
    def __init__(self):
        self.embedder = SemanticEmbedder()
        self.documents = []
        try:
            import faiss
            self.index = faiss.IndexFlatL2(384)  # Dimension for all-MiniLM-L6-v2
            logger.info("Created new FAISS index")
        except ImportError:
            logger.error("FAISS not available")
            raise

    def upload_documents(self, documents: List[Document]):
        if not documents:
            logger.warning("No documents to upload")
            return
        texts = [doc.text for doc in documents]
        embeddings = self.embedder.embed_documents(texts)

        if len(self.documents) == 0:
            self.index.add(embeddings)
        else:
            # For incremental updates
            self.index.add(embeddings)

        self.documents.extend(documents)
        logger.info(f"Added {len(documents)} documents to index. Total: {len(self.documents)}")

    def search(self, query_embedding: np.ndarray, k: int = 5) -> List[tuple]:
        distances, indices = self.index.search(np.array([query_embedding]), k)
        return [(self.documents[i].text, float(1 - distances[0][j]))
                for j, i in enumerate(indices[0]) if i != -1]

# Initialize retriever with enhanced functionality
retriever = EnhancedFAISSRetriever()

app = FastAPI(
    title="PQNK Farming Assistant",
    description="RAG-based expert system for PQNK farming",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    question: str

class TestQuery(BaseModel):
    query: str
    full_text: bool = False

class ChatResponse(BaseModel):
    answer: str
    follow_ups: List[str]
    youtube_link: Optional[str] = None
    confidence: int
    confidence_color: str

def is_greeting(question: str) -> bool:
    """Check if the input is a greeting based on keywords."""
    greetings = ["hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening"]
    question_lower = question.lower().strip()
    return any(greeting in question_lower for greeting in greetings)

def get_confidence_color(confidence: int) -> str:
    """Assign a color based on confidence percentage."""
    if confidence >= 80:
        return "green"
    elif confidence >= 50:
        return "yellow"
    else:
        return "red"

def find_relevant_video_link(top_results, documents) -> Optional[str]:
    """Find the most relevant video link in top search results."""
    for text, score in top_results:
        for doc in documents:
            if doc.text == text:
                metadata = doc.metadata or {}
                if metadata.get("Video Link"):
                    return metadata["Video Link"]
    return None

@app.post("/ask", response_model=ChatResponse)
async def ask_question(req: QueryRequest):
    try:
        logger.info(f"Received question: {req.question}")

        # Handle greetings
        if is_greeting(req.question):
            logger.info(f"Detected greeting: {req.question}")
            prompt = f"""
You are a friendly expert in PQNK sustainable farming.
The user has greeted you with "{req.question}".
Respond with a warm, professional greeting (1 sentence) that invites them to ask about PQNK farming.
Include a 'Follow-up' section with 2 specific and concise follow-up questions regarding PQNK-related topics.
Ensure the response is natural.
"""
            llm_output = generate_llm_response(prompt)
            logger.info(f"Received LLM greeting response: {llm_output[:100]}...")
            parts = llm_output.strip().split("Follow-up")
            answer = parts[0].strip()
            follow_ups = [f.strip("- ") for f in parts[1].split("\n") if f.strip()] if len(parts) > 1 else [
                "What are the core principles of PQNK farming?",
                "How can PQNK benefit my farm?",
                "Can you explain PQNK cost savings?"
            ]
            return ChatResponse(
                answer=answer,
                follow_ups=follow_ups[:3],
                youtube_link=None,
                confidence=100,
                confidence_color="green"
            )

        # Process non-greeting queries
        embedder = SemanticEmbedder()
        query_vec = embedder.embed_query(req.question)
        top_results = retriever.search(query_vec, k=5)

        if not top_results:
            logger.warning(f"No relevant information found for query: {req.question}")
            return ChatResponse(
                answer="This question is not related to PQNK sustainable farming. I am a chatbot designed to answer PQNK-related questions only.",
                follow_ups=[],
                youtube_link=None,
                confidence=0,
                confidence_color="red"
            )

        # Find relevant video link
        video_link = find_relevant_video_link(top_results, retriever.documents)

        # Combine context
        context = "\n\n".join([doc[0] for doc in top_results])

        # Calculate confidence
        top_similarity = top_results[0][1]
        confidence = round(top_similarity * 100)
        confidence_color = get_confidence_color(confidence)

        if confidence < 27:
            logger.info(f"Confidence {confidence}% is below threshold, returning brief response")
            return ChatResponse(
                answer="This question is not related to PQNK sustainable farming. I am a chatbot designed to answer PQNK-related questions only.",
                follow_ups=[],
                youtube_link=None,
                confidence=confidence,
                confidence_color=confidence_color
            )

        # Build prompt with video context
        video_context = f"\nRelevant video available: {video_link}" if video_link else "\nNo relevant videos found."
        prompt = f"""
You are an expert in PQNK sustainable farming.  PQNK is the abbreviation of Paedar Qudratti Nizam Kashatqari (to be pronounced as picnic)
 which means sustainable natural farming system in Urdu and it is also referred to as Paradoxical
 Agriculture. Provide a clear, concise answer to:
Question: {req.question}
Context:
{context}
{video_context}
Instructions:
1. Answer in simple, practical terms
2. If video is available and relevant, mention it naturally
3. Suggest 3 follow-up questions (the suggested questions should be written from the Users perspective, directed towards the LLM, keep the questions concise)

Example video mention: "For a demonstration, see this video: [link]"
"""
        llm_output = generate_llm_response(prompt)
        logger.info(f"LLM response: {llm_output[:100]}...")

        # Parse response
        parts = llm_output.strip().split("Follow-up")
        answer = parts[0].strip()

        follow_ups = []
        if len(parts) > 1:
            follow_up_lines = parts[1].split("\n")
            follow_ups = [line.strip("-• ").strip() for line in follow_up_lines if line.strip()]

        if not follow_ups:
            follow_ups = [
                "What are the next steps for PQNK implementation?",
                "How does PQNK improve soil health?",
                "Are there case studies for PQNK?"
            ]

        return ChatResponse(
            answer=answer,
            follow_ups=follow_ups[:3],
            youtube_link=video_link,
            confidence=confidence,
            confidence_color=confidence_color
        )
    except Exception as e:
        logger.error(f"Error in /ask endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/test-retrieval")
async def test_retrieval(req: TestQuery):
    try:
        logger.info(f"Testing retrieval for: {req.query}")
        embedder = SemanticEmbedder()
        q_vec = embedder.embed_query(req.query)
        results = retriever.search(q_vec)
        if not results:
            return {"results": [], "message": "No matches found"}
        text_processor = lambda x: x if req.full_text else (x[:1000] + "..." if len(x) > 1000 else x)
        return {
            "query": req.query,
            "top_score": results[0][1],
            "top_text": text_processor(results[0][0]),
            "all_results": [{"score": score, "text": text_processor(text)} for text, score in results[:5]],
            "total_results": len(results),
            "note": "Set full_text=true to disable truncation" if not req.full_text else None
        }
    except Exception as e:
        logger.error(f"Retrieval test failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        # Create temp directory if not exists
        temp_dir = Path("temp_uploads")
        temp_dir.mkdir(exist_ok=True)

        # Save uploaded file
        file_path = temp_dir / file.filename
        with open(file_path, "wb") as f:
            f.write(await file.read())
        logger.info(f"Processing PDF: {file.filename}")
        documents = process_pdf(file_path)

        if not documents:
            raise HTTPException(status_code=400, detail="No valid content extracted from PDF")
        retriever.upload_documents(documents)

        return {
            "status": "success",
            "filename": file.filename,
            "documents_added": len(documents),
            "total_documents": len(retriever.documents)
        }
    except Exception as e:
        logger.error(f"PDF upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    logger.info("Initializing PQNK Farming Assistant with enhanced embedding updates")
    try:
        # Process main knowledge base PDF
        pdf_path = Path("backend/app/data/pqnkfinal.pdf")
        if pdf_path.exists():
            logger.info(f"Processing main PDF: {pdf_path.name}")
            documents = process_pdf(pdf_path)
            if documents:
                retriever.upload_documents(documents)
                logger.info(f"Main PDF processed - {len(documents)} chunks added")
            else:
                logger.warning(f"No content extracted from {pdf_path.name}")

        # Process additional PDFs with proper embedding updates
        data_dir = Path("backend/app/data")
        if data_dir.exists():
            logger.info(f"Scanning for additional PDFs in: {data_dir}")
            pdf_files = list(data_dir.glob("*.pdf"))
            pdf_files = [f for f in pdf_files if f.name != "pqnkfinal.pdf"]

            for pdf_file in pdf_files:
                try:
                    logger.info(f"Processing: {pdf_file.name}")
                    documents = process_pdf(pdf_file)
                    if documents:
                        retriever.upload_documents(documents)
                        logger.info(f"Added {len(documents)} chunks from {pdf_file.name}")
                    else:
                        logger.warning(f"No content from {pdf_file.name}")
                except Exception as e:
                    logger.error(f"Error processing {pdf_file.name}: {str(e)}")

        # Verify embeddings were updated
        logger.info(f"System initialized with {len(retriever.documents)} documents")
        logger.info(f"FAISS index contains {retriever.index.ntotal} vectors")

        # Test retrieval with actual embedding verification
        test_query = "What are the principles of PQNK?"
        test_embedding = retriever.embedder.embed_query(test_query)
        results = retriever.search(test_embedding)

        if results:
            logger.info(f"Retrieval test successful. Top match score: {results[0][1]:.2f}")
            logger.debug(f"Sample result: {results[0][0][:200]}...")
        else:
            logger.warning("Retrieval test failed - no results returned")
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}", exc_info=True)
        raise

@app.get("/health")
async def health_check():
    try:
        return {
            "status": "healthy",
            "version": app.version,
            "index_status": f"{retriever.index.ntotal} vectors",
            "documents": len(retriever.documents),
            "pdf_loaded": any("pqnkfinal.pdf" in str(doc.metadata.get("source", "")) for doc in retriever.documents)
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Health check failed")

if __name__ == "__main__":
    logger.info("Starting enhanced PQNK Farming Assistant server")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
# Load environment variables
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Set page configuration
st.set_page_config(
    page_title="PQNK Farming Assistant",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS - Updated with About page styles
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&family=Playfair+Display:wght@700&display=swap');

html, body, [class*="css"] {
    font-family: 'Montserrat', sans-serif;
}

.sticky-header {
    position: sticky;
    top: 0;
    z-index: 100;
    background: #4a9f4e;
    padding: 15px 0;
    margin-bottom: 20px;
    border-radius: 0 0 16px 16px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    border-bottom: 3px solid #81c784;
}

.animated-title {
    font-size: 2.5rem !important;
    font-weight: 700 !important;
    text-align: center !important;
    font-family: 'Playfair Display', serif !important;
    color: #ffffff !important;
    margin: 0 !important;
    padding: 10px 0 !important;
    letter-spacing: 1px !important;
    text-shadow: 0 2px 4px rgba(0,0,0,0.2) !important;
}

/* Sidebar styling */
.stSidebar {
    background: linear-gradient(to bottom, #e8f5e9, #c8e6c9) !important;
    border-right: 1px solid #a5d6a7;
}

.sidebar-container {
    background-color: white;
    border-radius: 16px;
    padding: 20px;
    margin: 10px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    border: 1px solid #e0e0e0;
}

.sidebar-title {
    color: #1a4d1e;
    font-family: 'Playfair Display', serif;
    text-align: center;
    margin-bottom: 5px;
    font-size: 1.5rem;
}

.sidebar-subtitle {
    color: #2e7d32;
    text-align: center;
    font-size: 14px;
    margin-bottom: 20px;
}

.sidebar-logo {
    text-align: center;
    margin-bottom: 20px;
}

.sidebar-logo img {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    border: 3px solid #81c784;
    padding: 5px;
    background-color: white;
}

.sidebar-tips {
    margin-top: 25px;
    padding-top: 15px;
    border-top: 1px solid #e0e0e0;
}

.sidebar-tips-title {
    font-weight: 600;
    color: #1a4d1e;
    margin-bottom: 10px;
}

.sidebar-tips-list {
    padding-left: 20px;
    color: #2e7d32;
}

.sidebar-tips-list li {
    margin-bottom: 8px;
}

/* Updated Clear Conversation Button with Classy Vibrant Gradient */
.stButton > button {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    color: white !important;
    border-radius: 12px !important;
    padding: 12px !important;
    width: 80% !important;
    border: none !important;
    font-weight: 600 !important;
    transition: all 0.3s ease !important;
    margin: 10px auto !important;
    display: block !important;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2) !important;
    font-size: 16px !important;
}

.stButton > button:hover {
    background: linear-gradient(135deg, #764ba2 0%, #667eea 100%) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 12px rgba(0, 0, 0, 0.3) !important;
    color: white !important;
}

/* About Page Styles */
.about-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 40px 20px;
    border-radius: 16px;
    margin-bottom: 30px;
    text-align: center;
    box-shadow: 0 8px 16px rgba(0,0,0,0.1);
    animation: fadeIn 0.8s ease-out;
}

.about-header h1 {
    font-family: 'Playfair Display', serif;
    font-size: 3rem;
    margin-bottom: 15px;
    text-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

.about-header p {
    font-size: 1.2rem;
    max-width: 800px;
    margin: 0 auto;
    opacity: 0.9;
}

.about-section {
    background: white;
    border-radius: 16px;
    padding: 30px;
    margin-bottom: 30px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    border-left: 5px solid #667eea;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
    animation: slideUp 0.6s ease-out;
}

.about-section:hover {
    transform: translateY(-5px);
    box-shadow: 0 8px 20px rgba(0,0,0,0.12);
}

.about-section h2 {
    color: #1a4d1e;
    font-family: 'Playfair Display', serif;
    margin-bottom: 20px;
    border-bottom: 2px solid #e0e0e0;
    padding-bottom: 10px;
}

.about-section p {
    color: #333;
    line-height: 1.8;
    margin-bottom: 15px;
}

.team-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 25px;
    margin-top: 30px;
}

.team-card {
    background: white;
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 6px 12px rgba(0,0,0,0.1);
    transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    animation: fadeIn 0.8s ease-out;
}

.team-card:hover {
    transform: translateY(-10px);
    box-shadow: 0 12px 24px rgba(0,0,0,0.15);
}

.team-image {
    height: 250px;
    overflow: hidden;
}

.team-image img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: transform 0.5s ease;
}

.team-card:hover .team-image img {
    transform: scale(1.05);
}

.team-content {
    padding: 20px;
    background: linear-gradient(to bottom, #f8f9fa, #ffffff);
}

.team-name {
    font-family: 'Playfair Display', serif;
    font-size: 1.5rem;
    color: #1a4d1e;
    margin-bottom: 5px;
}

.team-role {
    color: #667eea;
    font-weight: 600;
    margin-bottom: 15px;
    font-size: 1rem;
}

.team-bio {
    color: #555;
    line-height: 1.6;
    margin-bottom: 15px;
}

.benefit-card {
    background: white;
    border-radius: 12px;
    padding: 25px;
    margin-bottom: 20px;
    box-shadow: 0 4px 8px rgba(0,0,0,0.08);
    border-top: 4px solid #667eea;
    transition: all 0.3s ease;
}

.benefit-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 8px 16px rgba(0,0,0,0.12);
}

.benefit-icon {
    font-size: 2.5rem;
    color: #764ba2;
    margin-bottom: 15px;
}

.benefit-title {
    font-weight: 700;
    color: #1a4d1e;
    margin-bottom: 10px;
    font-size: 1.2rem;
}

.benefit-desc {
    color: #555;
    line-height: 1.6;
}

/* Chat containers and other styles remain the same */
.chat-container {
    border-radius: 16px;
    padding: 20px;
    margin: 12px 5%;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    font-size: 15px;
    line-height: 1.6;
    animation: fadeIn 0.3s ease-in;
}

.user-container {
    background-color: #e8f5e9;
    color: #1a3c2e;
    margin-left: 30%;
    border-radius: 16px 16px 0 16px;
    border: 1px solid #c8e6c9;
}

.assistant-container {
    background-color: white;
    color: #1a3c2e;
    margin-right: 30%;
    border-radius: 16px 16px 16px 0;
    border: 1px solid #e0e0e0;
    border-left: 5px solid #4a9f4e;
}

.thinking-container {
    background-color: white;
    color: #1a3c2e;
    border-radius: 16px;
    padding: 20px;
    margin: 12px 5%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-right: 30%;
    border: 1px dashed #a5d6a7;
}

.follow-up-section {
    margin: 20px 5% 10px 5%;
}

.follow-up-title {
    font-size: 15px;
    font-weight: 600;
    color: #1a4d1e;
    margin-bottom: 10px;
    padding-left: 5px;
}

.follow-up-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 12px;
}

.follow-up-btn {
    background-color: #e8f5e9;
    color: #1a4d1e;
    border: 1px solid #a5d6a7;
    border-radius: 12px;
    padding: 12px 15px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    transition: all 0.2s ease;
    text-align: left;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.follow-up-btn:hover {
    background-color: #c8e6c9;
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    color: #1a3c2e;
}

.confidence-indicator {
    display: flex;
    align-items: center;
    margin-top: 12px;
    font-size: 14px;
    font-weight: 600;
    color: #1a3c2e;
}

.confidence-bar {
    width: 100px;
    height: 8px;
    border-radius: 4px;
    background: #e0e0e0;
    margin-right: 10px;
    overflow: hidden;
}

.confidence-fill {
    height: 100%;
    border-radius: 4px;
    background: #4a9f4e;
}

.stTextInput > div > div > input {
    border-radius: 16px;
    border: 2px solid #4a9f4e;
    padding: 14px;
    font-size: 15px;
    background-color: white;
}

.footer {
    text-align: center;
    color: #1a3c2e;
    font-size: 14px;
    margin-top: 40px;
    padding: 20px;
    background-color: white;
    border-radius: 16px;
    border: 1px solid #e0e0e0;
}

/* Navigation Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 10px;
}

.stTabs [data-baseweb="tab"] {
    height: 50px;
    padding: 0 25px;
    background: #e8f5e9 !important;
    border-radius: 12px !important;
    font-weight: 600;
    color: #1a4d1e !important;
    transition: all 0.3s ease !important;
    border: 1px solid #c8e6c9 !important;
}

.stTabs [data-baseweb="tab"]:hover {
    background: #c8e6c9 !important;
    color: #1a3c2e !important;
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    color: white !important;
    border: none !important;
    box-shadow: 0 4px 8px rgba(0,0,0,0.1) !important;
}

/* Animations */
@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

@keyframes slideUp {
    from { 
        opacity: 0;
        transform: translateY(20px);
    }
    to { 
        opacity: 1;
        transform: translateY(0);
    }
}

@keyframes scaleIn {
    from { 
        opacity: 0;
        transform: scale(0.9);
    }
    to { 
        opacity: 1;
        transform: scale(1);
    }
}

@media (max-width: 768px) {
    .user-container, .assistant-container {
        margin-left: 5% !important;
        margin-right: 5% !important;
    }

    .animated-title {
        font-size: 2rem !important;
    }
    
    .team-grid {
        grid-template-columns: 1fr;
    }
}
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="sticky-header">
    <h1 class="animated-title">🌿 PQNK Farming Assistant</h1>
</div>
""", unsafe_allow_html=True)

# Navigation Tabs
tab1, tab2 = st.tabs(["Chat Assistant", "About PQNK"])

with tab1:
    # Sidebar
    with st.sidebar:
        st.markdown("""
        <div class="sidebar-container">
            <div class="sidebar-logo">
                <img src="https://cdn-icons-png.flaticon.com/512/3079/3079158.png" alt="PQNK Logo">
            </div>
            <h2 class="sidebar-title">PQNK Farming</h2>
            <p class="sidebar-subtitle">Expert guidance for sustainable farming</p>
            <div style="text-align: center;">
                <button class="stButton" onclick="window.location.reload()">Clear Conversation</button>
            </div>
            <div class="sidebar-tips">
                <div class="sidebar-tips-title">Quick Tips:</div>
                <ul class="sidebar-tips-list">
                    <li>Ask about PQNK</li>
                    <li>Inquire about crop benefits</li>
                    <li>Explore implementation</li>
                </ul>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Initialize chat history
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'follow_ups' not in st.session_state:
        st.session_state.follow_ups = []

    # Display chat messages
    for message in st.session_state.messages:
        with st.container():
            if message["role"] == "user":
                st.markdown(
                    f"<div class='chat-container user-container'>{message['content']}</div>",
                    unsafe_allow_html=True
                )
            else:
                confidence_bar = ""
                if "confidence" in message:
                    confidence_bar = f"""
                    <div class='confidence-indicator'>
                        <div class='confidence-bar'>
                            <div class='confidence-fill' style='width: {message["confidence"]}%;'></div>
                        </div>
                        Confidence: {message["confidence"]}%
                    </div>
                    """
                st.markdown(
                    f"<div class='chat-container assistant-container'>{message['content']}{confidence_bar}</div>",
                    unsafe_allow_html=True
                )

    # Handle user input
    if prompt := st.chat_input("Ask about PQNK sustainable farming..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.follow_ups = []

        with st.spinner("Analyzing your question about PQNK farming..."):
            try:
                response = requests.post(
                    "http://127.0.0.1:8000/ask",
                    json={"question": prompt},
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": data.get("answer", "No answer provided"),
                        "confidence": data.get("confidence", 0)
                    })
                    st.session_state.follow_ups = data.get("follow_ups", [])
                else:
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"Error: API returned status {response.status_code}"
                    })
            except Exception as e:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"Error: {str(e)}"
                })

        st.rerun()

    # Display follow-up questions if available
    if st.session_state.follow_ups and len(st.session_state.follow_ups) > 0:
        st.markdown("""
        <div class="follow-up-section">
            <div class="follow-up-title">Suggested Follow-up Questions:</div>
            <div class="follow-up-grid">
        """, unsafe_allow_html=True)

        for i, question in enumerate(st.session_state.follow_ups):
            if st.button(question, key=f"follow_up_{i}"):
                st.session_state.messages.append({"role": "user", "content": question})
                st.session_state.follow_ups = []

                with st.spinner("Analyzing your follow-up question..."):
                    try:
                        response = requests.post(
                            "http://127.0.0.1:8000/ask",
                            json={"question": question},
                            headers={"Content-Type": "application/json"},
                            timeout=30
                        )

                        if response.status_code == 200:
                            data = response.json()
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": data.get("answer", "No answer provided"),
                                "confidence": data.get("confidence", 0)
                            })
                            st.session_state.follow_ups = data.get("follow_ups", [])
                    except Exception as e:
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": f"Error processing follow-up: {str(e)}"
                        })

                st.rerun()

        st.markdown("</div></div>", unsafe_allow_html=True)

    # Footer
    st.markdown("""
    <div class="footer">
        <strong>PQNK Sustainable Farming Assistant</strong><br>
        Powered by xAI | Built with Streamlit | © 2025 PQNK Farming<br>
        Committed to regenerative agricultural practices
    </div>
    """, unsafe_allow_html=True)

with tab2:
    # About Page Content
    st.markdown("""
    <div class="about-header">
        <h1>About PQNK Farming</h1>
        <p>Revolutionizing agriculture through sustainable practices and AI-powered intelligence</p>
    </div>
    """, unsafe_allow_html=True)
    
    # What is PQNK Section
    st.markdown("""
    <div class="about-section">
        <h2>What is PQNK Farming?</h2>
        <p>PQNK Farming represents a paradigm shift in sustainable agriculture, combining cutting-edge biological solutions with advanced technology to create farming systems that are both highly productive and environmentally regenerative.</p>
        <p>At its core, PQNK focuses on enhancing soil microbiome health to create self-sustaining ecosystems that require fewer external inputs while delivering superior crop yields and nutritional quality. Our approach goes beyond organic farming to create truly regenerative systems that improve with each growing season.</p>
        <p>The PQNK methodology is built on three pillars:</p>
        <ul>
            <li><strong>Biological Optimization:</strong> Harnessing natural microbial communities to enhance plant health and soil fertility</li>
            <li><strong>Precision Monitoring:</strong> Advanced sensing and data collection for real-time ecosystem insights</li>
            <li><strong>Adaptive Management:</strong> AI-driven decision support that evolves with your farm's unique conditions</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # AI Benefits Section
    st.markdown("""
    <div class="about-section">
        <h2>The Power of AI in PQNK Farming</h2>
        <p>Our AI-powered assistant represents the next generation of agricultural decision support, combining vast datasets with deep learning to provide personalized recommendations for your farm.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Benefits Cards in Columns
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="benefit-card">
            <div class="benefit-icon">🌱</div>
            <h3 class="benefit-title">Microbiome Analysis</h3>
            <p class="benefit-desc">Our AI processes soil test results to recommend optimal microbial inoculants tailored to your specific conditions and crops.</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="benefit-card">
            <div class="benefit-icon">📊</div>
            <h3 class="benefit-title">Predictive Analytics</h3>
            <p class="benefit-desc">Machine learning models forecast pest pressures, nutrient needs, and yield potential with remarkable accuracy.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="benefit-card">
            <div class="benefit-icon">🔄</div>
            <h3 class="benefit-title">Adaptive Learning</h3>
            <p class="benefit-desc">The system continuously improves its recommendations based on outcomes from thousands of similar farms.</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="benefit-card">
            <div class="benefit-icon">🌍</div>
            <h3 class="benefit-title">Sustainability Metrics</h3>
            <p class="benefit-desc">Track and optimize your farm's carbon footprint, water usage, and biodiversity impact in real-time.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Team Section
    st.markdown("""
    <div class="about-section">
        <h2>Meet Our Team</h2>
        <p>The brilliant minds behind PQNK's revolutionary approach to sustainable agriculture.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Team Cards in Columns
    team_col1, team_col2 = st.columns(2)
    
    with team_col1:
        st.markdown("""
        <div class="team-card">
            <div class="team-image">
                <img src="https://images.unsplash.com/photo-1560250097-0b93528c311a?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=687&q=80" alt="Dr. Sarah Chen">
            </div>
            <div class="team-content">
                <h3 class="team-name">Dr. Sarah Chen</h3>
                <p class="team-role">Chief Scientist & Microbiome Expert</p>
                <p class="team-bio">PhD in Soil Microbiology from Stanford. 15 years experience in microbial ecology and plant-microbe interactions. Developed PQNK's core microbial formulations.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="team-card">
            <div class="team-image">
                <img src="https://images.unsplash.com/photo-1551836022-d5d88e9218df?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=687&q=80" alt="Elena Rodriguez">
            </div>
            <div class="team-content">
                <h3 class="team-name">Elena Rodriguez</h3>
                <p class="team-role">Director of Field Operations</p>
                <p class="team-bio">3rd generation farmer with agronomy degree from UC Davis. Leads our global network of demonstration farms and field trials.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with team_col2:
        st.markdown("""
        <div class="team-card">
            <div class="team-image">
                <img src="https://images.unsplash.com/photo-1573497019940-1c28c88b4f3e?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=687&q=80" alt="Raj Patel">
            </div>
            <div class="team-content">
                <h3 class="team-name">Raj Patel</h3>
                <p class="team-role">AI & Data Science Lead</p>
                <p class="team-bio">Former Google AI researcher specializing in agricultural applications. Built PQNK's predictive models and recommendation engines.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="team-card">
            <div class="team-image">
                <img src="https://images.unsplash.com/photo-1568602471122-7832951cc4c5?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1470&q=80" alt="Michael Johnson">
            </div>
            <div class="team-content">
                <h3 class="team-name">Michael Johnson</h3>
                <p class="team-role">Sustainability Economist</p>
                <p class="team-bio">Develops financial models proving the long-term profitability of regenerative practices. Former World Bank agriculture specialist.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Footer for About Page
    st.markdown("""
    <div class="footer">
        <strong>PQNK Sustainable Farming Initiative</strong><br>
        Transforming Agriculture Through Science & Technology<br>
        © 2025 PQNK Farming | Contact: info@pqnk.ag
    </div>
    """, unsafe_allow_html=True)
