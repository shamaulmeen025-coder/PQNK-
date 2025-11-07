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
