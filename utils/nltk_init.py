import os
import nltk
import logging
import ssl
from pathlib import Path
import time

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
            
            # Create an SSL context that doesn't verify certificates
            try:
                _create_unverified_https_context = ssl._create_unverified_context
            except AttributeError:
                pass
            else:
                ssl._create_default_https_context = _create_unverified_https_context
            
            # Try to download with retries
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    nltk.download('vader_lexicon', quiet=True)
                    logging.info("Successfully downloaded VADER lexicon")
                    return True
                except Exception as e:
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 2
                        logging.warning(f"Download attempt {attempt + 1} failed: {str(e)}. Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                    else:
                        logging.error(f"Failed to download VADER lexicon after {max_retries} attempts: {str(e)}")
                        
                        # Check if we have a local copy in our data directory
                        local_vader = data_path / 'sentiment' / 'vader_lexicon.zip'
                        if local_vader.exists():
                            logging.info("Found local VADER lexicon, using that instead")
                            return True
                        
                        return False
                
    except Exception as e:
        logging.error(f"Error initializing NLTK data: {str(e)}")
        return False 
