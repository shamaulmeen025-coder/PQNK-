# backend/app/pdf_processor.py
from pathlib import Path
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from .retriever import Document
import logging

logger = logging.getLogger(__name__)

def process_pdf(pdf_path: Path):
    """Extract and chunk text from PDF"""
    try:
        # Read PDF
        reader = PdfReader(pdf_path)
        text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
        
        # Split into chunks
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=200,
            length_function=len
        )
        
        chunks = splitter.split_text(text)
        
        # Create document objects with dummy embeddings (or without)
        documents = [
            Document.from_text_only(
                text=chunk,
                metadata={"source": pdf_path.name, "page": i // 3}
            )
            for i, chunk in enumerate(chunks)
        ]
        
        logger.info(f"Processed {len(documents)} chunks from {pdf_path.name}")
        print(f"Processing PDF: {pdf_path.name}")
        print(f"Number of chunks: {len(documents)}")
        return documents
    
        
    except Exception as e:
        logger.error(f"Failed to process PDF: {str(e)}")
        raise
