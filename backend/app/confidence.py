# backend/app/confidence.py
import logging
from typing import List, Tuple
from .retriever import Document

logger = logging.getLogger(__name__)

def compute_confidence(results: List[Tuple[str, float]]) -> Tuple[List[Document], int]:
    """Compute confidence score for search results."""
    try:
        if not results:
            return [], 0
        
        # Convert to Document objects
        documents = [Document(text=text) for text, _ in results]
        
        # Get top 3 scores
        top_scores = [score for _, score in results[:3]]
        
        # Weighted confidence calculation
        weights = [0.5, 0.3, 0.2]
        weighted_sum = sum(score * weight 
                          for score, weight in zip(top_scores, weights[:len(top_scores)]))
        
        # Scale to percentage (0-100)
        confidence = min(max(int(weighted_sum * 100), 100), 0)
        
        logger.debug(f"Computed confidence: {confidence}%")
        return documents[:3], confidence
        
    except Exception as e:
        logger.error(f"Confidence computation failed: {str(e)}")
        return [], 0