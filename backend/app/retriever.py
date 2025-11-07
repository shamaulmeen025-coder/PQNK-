# backend/app/retriever.py

import faiss
import numpy as np
import glob
import os
import pickle
import logging
import pandas as pd
from typing import List, Tuple, Any, Optional, Dict
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer

class Document(BaseModel):
    """Document model with text and embedding data."""
    text: str
    embedding: Optional[List[float]] = Field(
        default=None,
        description="Embedding vector as list of floats",
        json_schema_extra={"format": "float32-array"}
    )
    metadata: Optional[dict] = Field(default_factory=dict)

    def to_numpy(self) -> np.ndarray:
        """Convert embedding to numpy array."""
        if self.embedding is None:
            raise ValueError("Cannot convert None embedding to numpy array.")
        return np.array(self.embedding, dtype=np.float32)

    @classmethod
    def from_numpy(cls, text: str, embedding: np.ndarray, metadata: dict = {}):
        return cls(text=text, embedding=embedding.tolist(), metadata=metadata)

    @classmethod
    def from_text_only(cls, text: str, metadata: dict = {}):
        return cls(text=text, embedding=None, metadata=metadata)


class FAISSRetriever:
    """Enhanced FAISS retriever with proper embedding updates and video link support."""

    def __init__(self, index_path: str = "faiss_index", dim: int = 384):
        self.index_path = index_path
        self.dim = dim
        self.index = None
        self.documents: List[Document] = []
        self.source_df: Optional[pd.DataFrame] = None
        self.logger = logging.getLogger(__name__)
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')

        try:
            if os.path.exists(f"{index_path}.index"):
                self.load_index()
                self.logger.info(f"Loaded existing index with {len(self.documents)} documents")
            else:
                self._create_index()
                self.logger.info("Created new FAISS index")
        except Exception as e:
            self.logger.error(f"Error initializing retriever: {str(e)}")
            raise

        self._auto_index_pdfs()

    def _create_index(self):
        """Initialize a new FAISS index."""
        self.index = faiss.IndexFlatL2(self.dim)  # Using L2 distance for better normalization
        self.documents = []

    def _auto_index_pdfs(self):
        """Automatically index PDFs from the data directory."""
        try:
            data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
            pdf_files = glob.glob(os.path.join(data_dir, "*.pdf"))
            
            if not pdf_files:
                self.logger.info(f"No PDFs found in {data_dir}")
                return

            self.logger.info(f"Found {len(pdf_files)} PDFs in {data_dir}")

            for pdf_path in pdf_files:
                pdf_name = os.path.basename(pdf_path)
                if any(doc.metadata.get("source") == pdf_name for doc in self.documents):
                    self.logger.debug(f"Skipping already indexed PDF: {pdf_name}")
                    continue

                self.logger.info(f"Processing new PDF: {pdf_name}")
                from .pdf_processor import process_pdf
                docs = process_pdf(pdf_path)
                
                if not docs:
                    self.logger.warning(f"No content extracted from {pdf_name}")
                    continue

                # Generate embeddings for new documents
                texts = [doc.text for doc in docs]
                embeddings = self.embedder.encode(texts, convert_to_numpy=True)
                
                # Add embeddings to documents
                for doc, emb in zip(docs, embeddings):
                    doc.embedding = emb.tolist()
                    doc.metadata["source"] = pdf_name

                self.upload_documents(docs)
                self.logger.info(f"Added {len(docs)} chunks from {pdf_name}")

        except Exception as e:
            self.logger.error(f"Error in auto-indexing PDFs: {str(e)}", exc_info=True)

    def save_index(self):
        """Save both FAISS index and document metadata."""
        try:
            faiss.write_index(self.index, f"{self.index_path}.index")
            with open(f"{self.index_path}.pkl", "wb") as f:
                pickle.dump([doc.model_dump() for doc in self.documents], f)
            self.logger.info(f"Saved index with {len(self.documents)} documents")
        except Exception as e:
            self.logger.error(f"Error saving index: {str(e)}")
            raise

    def load_index(self):
        """Load existing FAISS index and documents."""
        try:
            self.index = faiss.read_index(f"{self.index_path}.index")
            with open(f"{self.index_path}.pkl", "rb") as f:
                documents_data = pickle.load(f)
                self.documents = [Document(**data) for data in documents_data]
            self.logger.info(f"Loaded {len(self.documents)} documents from disk")
        except Exception as e:
            self.logger.error(f"Error loading index: {str(e)}")
            raise

    def upload_documents(self, documents: List[Document]):
        """Upload documents with proper embedding updates."""
        if not documents:
            self.logger.warning("No documents provided for upload")
            return

        try:
            # Filter out documents without embeddings
            valid_docs = [doc for doc in documents if doc.embedding is not None]
            if not valid_docs:
                self.logger.warning("No documents with valid embeddings provided")
                return

            embeddings = np.array(
                [doc.to_numpy() for doc in valid_docs],
                dtype=np.float32
            )

            # Normalize embeddings for cosine similarity
            faiss.normalize_L2(embeddings)
            
            # Add to index
            self.index.add(embeddings)
            self.documents.extend(valid_docs)
            
            self.save_index()
            self.logger.info(f"Successfully added {len(valid_docs)} documents to index")

        except Exception as e:
            self.logger.error(f"Error uploading documents: {str(e)}")
            raise

    def index_csv(self, csv_path: str, text_col: str = "text"):
        """Index a CSV file with video links and other metadata."""
        try:
            df = pd.read_csv(csv_path)
            if text_col not in df.columns:
                raise ValueError(f"Column '{text_col}' not found in CSV")

            self.source_df = df  # Save for video link matching

            new_docs = []
            texts = df[text_col].tolist()
            embeddings = self.embedder.encode(texts, convert_to_numpy=True)

            for i, (_, row) in enumerate(df.iterrows()):
                metadata = {k: v for k, v in row.items() if k != text_col}
                new_docs.append(Document.from_numpy(row[text_col], embeddings[i], metadata))

            self.upload_documents(new_docs)
            self.logger.info(f"Indexed {len(new_docs)} entries from {csv_path}")

        except Exception as e:
            self.logger.error(f"Failed to index CSV: {str(e)}")
            raise

    def search(self, query_vector: np.ndarray, k: int = 5) -> List[Tuple[str, float]]:
        """Search with enhanced similarity scoring."""
        if self.index is None or self.index.ntotal == 0:
            self.logger.warning("Attempted search on empty index")
            return []

        try:
            # Ensure proper vector shape and normalization
            query_vector = query_vector.reshape(1, -1).astype(np.float32)
            faiss.normalize_L2(query_vector)

            # Perform search
            distances, indices = self.index.search(query_vector, k)

            # Convert distances to similarity scores (1 - distance for L2)
            results = []
            for i, dist in zip(indices[0], distances[0]):
                if i >= 0:  # Valid index
                    similarity = 1.0 - dist  # Convert L2 distance to similarity
                    results.append((self.documents[i].text, float(similarity)))

            self.logger.debug(f"Search returned {len(results)} results")
            return results

        except Exception as e:
            self.logger.error(f"Search failed: {str(e)}")
            return []

    def get_video_link(self, text: str) -> Optional[str]:
        """Get video link for matching text from source CSV."""
        if self.source_df is None:
            return None

        matches = self.source_df[self.source_df["text"] == text]
        if not matches.empty:
            return matches.iloc[0].get("Video Link")
        return None

    def get_index_stats(self) -> Dict[str, int]:
        """Get statistics about the current index."""
        return {
            "documents": len(self.documents),
            "vectors": self.index.ntotal if self.index else 0,
            "dimensions": self.dim
        }