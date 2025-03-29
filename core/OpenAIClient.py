def shutdown(self):
    """
    Properly shut down the OpenAI client.
    Release all resources and close the browser.
    """
    try:
        if not hasattr(self, '_initialized') or not self._initialized:
            logger.warning("❌ OpenAIClient not booted. Call `.boot()` first.")
            return

        # Save cookies before shutdown
        if self.driver:
            self.save_cookies()
            
            # Quit the WebDriver
            logger.info("🔄 Closing WebDriver...")
            try:
                self.driver.quit()
            except Exception as e:
                logger.error(f"Error closing driver: {e}")
            finally:
                self.driver = None
                
        # Reset state
        self._initialized = False
        logger.info("✅ OpenAI client shut down successfully")
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}")
        raise 