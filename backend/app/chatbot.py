# backend/app/chatbot.py
import numpy as np
import logging
from .retriever import FAISSRetriever, Document
from .embedder import SemanticEmbedder
from .prompts import pqnk_prompt
from .utils import translate_to_english
from .confidence import compute_confidence
from transformers import pipeline
from pydantic import BaseModel

class ChatResponse(BaseModel):
    answer: str
    confidence: int

# Initialize components
logger = logging.getLogger(__name__)
embedder = SemanticEmbedder()
retriever = FAISSRetriever()
qa_pipeline = pipeline("text2text-generation", model="google/flan-t5-base")

def generate_answer(user_input: str) -> ChatResponse:
    """Generate answer to user query using RAG pipeline.
    
    Args:
        user_input: User's question
        
    Returns:
        ChatResponse with answer and confidence
    """
    try:
        # Translate non-English queries
        query = translate_to_english(user_input)
        logger.info(f"Processed query: {query}")
        
        # Embed query
        q_vec = embedder.embed_query(query)
        
        # Retrieve relevant documents
        results = retriever.search(q_vec)
        
        # Compute confidence
        top_docs, confidence = compute_confidence(results)
        
        # Handle low confidence
        if confidence < 30:
            logger.warning(f"Low confidence response ({confidence}%) for query: {query}")
            return ChatResponse(
                answer="I'm not confident about this. Could you provide more details?",
                confidence=confidence
            )
        logger.info(f"Loaded LLM: {qa_pipeline.model.name_or_path}")
        # Generate answer
        context = "\n".join([doc.text for doc in top_docs])
        prompt = pqnk_prompt.format(context=context, question=query)
        
        # Generate with LLM
        result = qa_pipeline(
            prompt, 
            max_new_tokens=256,
            temperature=0.3
        )[0]['generated_text'].strip()
        
        logger.info(f"Generated answer with confidence {confidence}%")
        return ChatResponse(answer=result, confidence=confidence)
        
    except Exception as e:
        logger.error(f"Answer generation failed: {str(e)}")
        return ChatResponse(
            answer="I encountered an error processing your request.",
            confidence=0
        )