# backend/app/utils.py
from deep_translator import GoogleTranslator
import logging

logger = logging.getLogger(__name__)

def translate_to_english(text: str) -> str:
    """Translate text to English if needed.
    
    Args:
        text: Input text in any language
        
    Returns:
        English translated text
    """
    try:
        if not text.strip():
            return text
            
        # Skip translation if already English
        if text.isascii():
            return text
            
        translated = GoogleTranslator(source="auto", target="en").translate(text)
        logger.debug(f"Translated text: {text} -> {translated}")
        return translated
    except Exception as e:
        logger.error(f"Translation failed: {str(e)}")
        return text