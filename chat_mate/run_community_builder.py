import os
import asyncio
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv

from social.strategies.wordpress_strategy import WordPressCommunityStrategy
from social.strategies.community_scheduler import CommunityScheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    # Load environment variables
    load_dotenv()
    
    try:
        # Initialize WordPress strategy
        wp_strategy = WordPressCommunityStrategy()
        if not wp_strategy.initialize({}):
            logger.error("Failed to initialize WordPress strategy")
            return
        
        # Initialize scheduler
        scheduler = CommunityScheduler()
        
        # Schedule regular tasks
        scheduler.schedule_engagement_check(wp_strategy, interval_minutes=30)
        scheduler.schedule_ai_responses(wp_strategy, check_interval=15)
        scheduler.schedule_daily_report(wp_strategy, time="00:00")
        
        # Example: Schedule a video post for tomorrow
        tomorrow = datetime.now() + timedelta(days=1)
        test_video = {
            "title": "Sample Video",
            "description": "This is a sample video description",
            "video_id": "sample123",
            "tags": ["sample", "test"],
            "thumbnail_url": "https://example.com/thumb.jpg"
        }
        scheduler.schedule_task(wp_strategy, test_video, tomorrow)
        
        # Start the scheduler
        scheduler.start()
        
        # Keep the script running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            scheduler.stop()
            wp_strategy.cleanup()
            
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 