import os
import json
import logging
import time
import random
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from core.social.strategies.wordpress_strategy import WordPressCommunityStrategy
from core.social.AIChatAgent import AIChatAgent

class CommunityScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.logger = logging.getLogger(__name__)
        self.ai_agent = AIChatAgent()
        self.scheduled_tasks = {}
        
        # Initialize paths
        self.data_dir = os.getenv("DATA_DIR", "./data")
        self.schedule_file = os.path.join(self.data_dir, "scheduled_tasks.json")
        
        # Load existing schedules
        self._load_schedules()

    def schedule_task(self, strategy: WordPressCommunityStrategy, video_data: Dict[str, Any], post_time: datetime):
        """Schedule a task to post a video at a specific time."""
        job = self.scheduler.add_job(
            strategy.sync_youtube_video,
            args=[video_data],
            trigger='date',
            run_date=post_time,
            id=f"post_{video_data['video_id']}",
            replace_existing=True
        )
        
        # Track the scheduled task
        self.scheduled_tasks[job.id] = {
            "type": "video_post",
            "data": video_data,
            "scheduled_time": post_time.isoformat(),
            "status": "scheduled"
        }
        
        self._save_schedules()
        self.logger.info(f" Scheduled task for video {video_data['video_id']} at {post_time}")

    def schedule_engagement_check(self, strategy: WordPressCommunityStrategy, interval_minutes: int = 30):
        """Schedule regular engagement checks."""
        job = self.scheduler.add_job(
            self._check_engagement,
            args=[strategy],
            trigger=IntervalTrigger(minutes=interval_minutes),
            id="engagement_check",
            replace_existing=True
        )
        
        self.scheduled_tasks[job.id] = {
            "type": "engagement_check",
            "interval": interval_minutes,
            "last_run": None,
            "status": "scheduled"
        }
        
        self._save_schedules()
        self.logger.info(f" Scheduled engagement checks every {interval_minutes} minutes")

    def schedule_ai_responses(self, strategy: WordPressCommunityStrategy, check_interval: int = 15):
        """Schedule automated AI responses to comments."""
        job = self.scheduler.add_job(
            self._process_comments,
            args=[strategy],
            trigger=IntervalTrigger(minutes=check_interval),
            id="ai_responses",
            replace_existing=True
        )
        
        self.scheduled_tasks[job.id] = {
            "type": "ai_responses",
            "interval": check_interval,
            "last_run": None,
            "status": "scheduled"
        }
        
        self._save_schedules()
        self.logger.info(f" Scheduled AI responses every {check_interval} minutes")

    def schedule_daily_report(self, strategy: WordPressCommunityStrategy, time: str = "00:00"):
        """Schedule daily engagement report generation."""
        job = self.scheduler.add_job(
            self._generate_daily_report,
            args=[strategy],
            trigger=CronTrigger.from_crontab(f"0 {time.replace(':', ' ')} * * *"),
            id="daily_report",
            replace_existing=True
        )
        
        self.scheduled_tasks[job.id] = {
            "type": "daily_report",
            "time": time,
            "last_run": None,
            "status": "scheduled"
        }
        
        self._save_schedules()
        self.logger.info(f" Scheduled daily reports at {time}")

    async def _process_comments(self, strategy: WordPressCommunityStrategy):
        """Process new comments and generate AI responses."""
        try:
            # Get recent comments
            recent_comments = strategy.wp_client.call(comments.GetComments({'number': 10}))
            
            for comment in recent_comments:
                # Skip if already processed
                if self._is_comment_processed(comment.id):
                    continue
                
                # Generate AI response
                prompt = f"Generate a friendly and engaging response to this comment: {comment.content}"
                response = await self.ai_agent.ask(prompt)
                
                if response:
                    # Post the response
                    strategy.wp_client.call(comments.NewComment({
                        'post_id': comment.post_id,
                        'content': response,
                        'parent': comment.id
                    }))
                    
                    # Track the processed comment
                    self._mark_comment_processed(comment.id)
                    
            self.logger.info(" Processed new comments")
            
        except Exception as e:
            self.logger.error(f"Error processing comments: {e}")

    def _check_engagement(self, strategy: WordPressCommunityStrategy):
        """Check engagement metrics and take action if needed."""
        try:
            metrics = strategy.get_community_metrics()
            
            # If engagement is low, generate engagement prompt
            if metrics["engagement_rate"] < 0.3:
                prompt = "Generate an engaging question to ask the community about recent content"
                response = self.ai_agent.ask(prompt)
                
                if response:
                    # Post the engagement prompt
                    post = WordPressPost()
                    post.title = "Let's Discuss!"
                    post.content = response
                    post.post_status = 'publish'
                    strategy.wp_client.call(posts.NewPost(post))
            
            self.logger.info(" Completed engagement check")
            
        except Exception as e:
            self.logger.error(f"Error checking engagement: {e}")

    async def _generate_daily_report(self, strategy: WordPressCommunityStrategy):
        """Generate and store daily engagement report."""
        try:
            report = strategy.generate_engagement_report()
            
            # Save report
            report_file = os.path.join(self.data_dir, f"report_{datetime.now().strftime('%Y%m%d')}.json")
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=4)
            
            self.logger.info(" Generated daily report")
            
        except Exception as e:
            self.logger.error(f"Error generating daily report: {e}")

    def _load_schedules(self):
        """Load scheduled tasks from file."""
        if os.path.exists(self.schedule_file):
            with open(self.schedule_file, 'r') as f:
                self.scheduled_tasks = json.load(f)

    def _save_schedules(self):
        """Save scheduled tasks to file."""
        os.makedirs(os.path.dirname(self.schedule_file), exist_ok=True)
        with open(self.schedule_file, 'w') as f:
            json.dump(self.scheduled_tasks, f, indent=4)

    def _is_comment_processed(self, comment_id: str) -> bool:
        """Check if a comment has been processed."""
        processed_file = os.path.join(self.data_dir, "processed_comments.json")
        if os.path.exists(processed_file):
            with open(processed_file, 'r') as f:
                processed = json.load(f)
                return str(comment_id) in processed
        return False

    def _mark_comment_processed(self, comment_id: str):
        """Mark a comment as processed."""
        processed_file = os.path.join(self.data_dir, "processed_comments.json")
        processed = {}
        if os.path.exists(processed_file):
            with open(processed_file, 'r') as f:
                processed = json.load(f)
        
        processed[str(comment_id)] = datetime.now().isoformat()
        
        with open(processed_file, 'w') as f:
            json.dump(processed, f, indent=4)

    def start(self):
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            self.logger.info(" Scheduler started")

    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()
        self.logger.info("Scheduler stopped.") 