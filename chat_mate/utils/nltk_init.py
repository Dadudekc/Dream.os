import os
import nltk
import logging
from pathlib import Path

def ensure_nltk_data():
    """
    Ensures required NLTK data is available, with offline fallback.
    Returns True if successful, False otherwise.
    """
    try:
        # Check if data directory exists
        data_path = Path.home() / 'nltk_data'
        if not data_path.exists():
            data_path.mkdir(parents=True)
        
        # Set NLTK data path
        nltk.data.path.append(str(data_path))
        
        # Try to find vader_lexicon
        try:
            nltk.data.find('vader_lexicon')
            return True
        except LookupError:
            logging.info("VADER lexicon not found, attempting to download...")
            
            # Try to download with timeout
            try:
                nltk.download('vader_lexicon', quiet=True)
                return True
            except Exception as e:
                logging.error(f"Failed to download VADER lexicon: {str(e)}")
                
                # Check if we have a local copy in our data directory
                local_vader = data_path / 'sentiment' / 'vader_lexicon.zip'
                if local_vader.exists():
                    logging.info("Found local VADER lexicon, using that instead")
                    return True
                
                return False
                
    except Exception as e:
        logging.error(f"Error initializing NLTK data: {str(e)}")
        return False 