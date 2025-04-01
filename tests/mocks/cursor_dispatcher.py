import logging

logger = logging.getLogger(__name__)

class CursorDispatcher:
    def __init__(self):
        self.connected = False
        
    def connect(self):
        self.connected = True
        
    def disconnect(self):
        self.connected = False
        
    def send_message(self, message):
        logger.info(f"Mock dispatcher sending: {message}")
        return True 
