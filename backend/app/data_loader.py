import pandas as pd
import logging
import re
import os
from typing import List, Tuple
from pypdf import PdfReader

logger = logging.getLogger(__name__)

def clean_text(text: str) -> str:
    """Clean and preprocess text data"""
    if not isinstance(text, str):
        return ""
    text = re.sub(r'\d{1,2}:\d{2}–\d{1,2}:\d{2}', '', text)
    text = re.sub(r'\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}', '', text)
    text = re.sub(r'[^\w\s.,;:?!-]', '', text)
    return ' '.join(text.split())

def load_csvs(main_paths: list, followup_path: str) -> Tuple[List[str], List[str]]:
    """Load and process PQNK knowledge from both CSV and PDF files"""
    text_data = []
    followup_questions = []

    try:
        for path in main_paths:
            logger.info(f"Processing file: {path}")
            ext = os.path.splitext(path)[1].lower()

            if ext == ".csv":
                try:
                    df = pd.read_csv(path, encoding='utf-8').dropna(how='all').fillna('')
                except UnicodeDecodeError:
                    df = pd.read_csv(path, encoding='latin1').dropna(how='all').fillna('')

                for _, row in df.iterrows():
                    content_parts = []
                    if 'Video Title' in row and row['Video Title']:
                        content_parts.append(f"Title: {row['Video Title']}")
                    if 'Transcription' in row and row['Transcription']:
                        content_parts.append(clean_text(row['Transcription']))
                    if 'Information' in row and row['Information']:
                        content_parts.append(clean_text(row['Information']))
                    if 'Quotations' in row and row['Quotations']:
                        content_parts.append(f"Key Quote: {clean_text(row['Quotations'])}")
                    if content_parts:
                        text_data.append('\n'.join(content_parts))

            elif ext == ".pdf":
                try:
                    reader = PdfReader(path)
                    pdf_text = ""
                    for page in reader.pages:
                        pdf_text += page.extract_text() or ""
                    pdf_text = clean_text(pdf_text)
                    if pdf_text.strip():
                        text_data.append(pdf_text)
                        logger.info(f"Extracted {len(pdf_text)} chars from {path}")
                except Exception as e:
                    logger.error(f"Error reading PDF {path}: {e}")

        logger.info(f"Total combined text segments: {len(text_data)}")

        # Process follow-up file (CSV)
        logger.info(f"Processing follow-up file: {followup_path}")
        followup_df = pd.read_csv(followup_path, encoding='utf-8', on_bad_lines='skip')
        question_col = next((col for col in followup_df.columns if 'question' in col.lower()), None)

        if question_col:
            followup_questions = followup_df[question_col].apply(clean_text).dropna().unique().tolist()
            logger.info(f"Loaded {len(followup_questions)} follow-up questions")
        else:
            logger.warning("No question column found in follow-up file")

    except Exception as e:
        logger.exception(f"Error loading files: {e}")
        raise

    return text_data, followup_questions
