import logging

logger = logging.getLogger(__name__)

class DreamscapeService:
    def __init__(self):
        self.active = False
        logger.info("DreamscapeService initialized.")

    def start(self):
        if not self.active:
            self.active = True
            logger.info("DreamscapeService has started.")

    def stop(self):
        if self.active:
            self.active = False
            logger.info("DreamscapeService has stopped.")

    def get_status(self):
        return "Running" if self.active else "Stopped"

dreamscape_service = DreamscapeService() 