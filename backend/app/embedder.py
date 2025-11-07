# backend/app/embedder.py
import numpy as np
import logging
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter
from .retriever import Document
from typing import List

class SemanticEmbedder:
    """Handles text embedding and chunking."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.logger = logging.getLogger(__name__)
        try:
            self.model = SentenceTransformer(model_name)
            self.splitter = RecursiveCharacterTextSplitter(
                chunk_size=350, 
                chunk_overlap=50
            )
            self.logger.info(f"Loaded embedding model: {model_name}")
        except Exception as e:
            self.logger.error(f"Error initializing embedder: {str(e)}")
            raise

    def embed_query(self, query: str) -> np.ndarray:
        """Embed a single query string."""
        try:
            return self.model.encode(query)
        except Exception as e:
            self.logger.error(f"Embedding failed for query: {str(e)}")
            raise

    def split_and_embed(self, text_segments: List[str]) -> List[Document]:
        """Split multiple text segments into chunks and generate embeddings."""
        try:
            all_documents = []
            all_embeddings = []
            
            for text in text_segments:
                if not text:
                    continue
                
                # Split text
                chunks = self.splitter.split_text(text)
                
                # Generate embeddings for this segment
                embeddings = self.model.encode(chunks)
                
                # Create Document objects for this segment
                segment_documents = [
                    Document.from_numpy(text=chunk, embedding=embedding)
                    for chunk, embedding in zip(chunks, embeddings)
                ]
                
                all_documents.extend(segment_documents)
                all_embeddings.extend(embeddings)
            
            self.logger.info(f"Generated {len(all_documents)} embeddings from {len(text_segments)} text segments")
            return all_documents
        except Exception as e:
            self.logger.error(f"Text processing failed: {str(e)}")
            raise
