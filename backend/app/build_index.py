# backend/app/build_index.py
import argparse
import logging
from .data_loader import load_csvs
from .embedder import SemanticEmbedder
from .retriever import FAISSRetriever

def main(data_paths: list, followup_path: str):
    """Build and persist FAISS index from data files"""
    logger = logging.getLogger(__name__)
    logger.info("Starting index building process")
    
    try:
        # Load data
        text_data, _ = load_csvs(data_paths, followup_path)
        logger.info(f"Loaded text data with {len(text_data)} characters")
        
        # Process text
        embedder = SemanticEmbedder()
        documents = embedder.split_and_embed(text_data)
        
        # Build index
        retriever = FAISSRetriever()
        retriever.upload_documents(documents)
        logger.info("Index build completed successfully")
        
    except Exception as e:
        logger.exception("Index build failed")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build FAISS index from data files")
    parser.add_argument("--data", nargs="+", required=True, help="Main data file paths")
    parser.add_argument("--followup", required=True, help="Followup data file path")
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    main(args.data, args.followup)