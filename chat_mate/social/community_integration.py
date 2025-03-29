import logging
import sys
import os
from typing import Dict, Any, List, Optional

# Import platform-specific strategies  
from social.strategies.twitter_strategy import TwitterStrategy
from social.strategies.facebook_strategy import FacebookStrategy
from social.strategies.reddit_strategy import RedditStrategy
from social.strategies.stocktwits_strategy import StocktwitsStrategy
from social.strategies.linkedin_strategy import LinkedinStrategy
from social.strategies.instagram_strategy import InstagramStrategy

# Import the unified dashboard
from social.UnifiedCommunityDashboard import UnifiedCommunityDashboard as CommunityDashboard
from social.social_post_manager import SocialPostManager
from social.log_writer import logger

class CommunityIntegrationManager:
    """
    Integrates all social media platforms with the unified community dashboard.
    
    This class serves as the main entry point for community management,
    connecting platform-specific strategies with unified analytics and reporting.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the community integration manager with configuration."""
        self.config = config
        self.platform_strategies = {}
        self.dashboard = None
        self.post_manager = None
        
        # Initialize components
        self._initialize_strategies()
        self._initialize_dashboard()
        self._initialize_post_manager()
        
        logger.info(" Community Integration Manager initialized")
    
    def _initialize_strategies(self) -> None:
        """Initialize strategy objects for each enabled platform."""
        platform_configs = self.config.get("platforms", {})
        
        # Twitter
        if platform_configs.get("twitter", {}).get("enabled", False):
            try:
                twitter_config = platform_configs.get("twitter", {})
                self.platform_strategies["twitter"] = TwitterStrategy(
                    config=twitter_config,
                    feedback_file=twitter_config.get("feedback_file", "social/data/twitter_feedback.json")
                )
                logger.info(" Twitter strategy initialized")
            except Exception as e:
                logger.error(f" Failed to initialize Twitter strategy: {e}")
        
        # Facebook
        if platform_configs.get("facebook", {}).get("enabled", False):
            try:
                facebook_config = platform_configs.get("facebook", {})
                self.platform_strategies["facebook"] = FacebookStrategy(
                    config=facebook_config,
                    feedback_file=facebook_config.get("feedback_file", "social/data/facebook_feedback.json")
                )
                logger.info(" Facebook strategy initialized")
            except Exception as e:
                logger.error(f" Failed to initialize Facebook strategy: {e}")
        
        # Reddit
        if platform_configs.get("reddit", {}).get("enabled", False):
            try:
                reddit_config = platform_configs.get("reddit", {})
                self.platform_strategies["reddit"] = RedditStrategy(
                    config=reddit_config,
                    feedback_file=reddit_config.get("feedback_file", "social/data/reddit_feedback.json")
                )
                logger.info(" Reddit strategy initialized")
            except Exception as e:
                logger.error(f" Failed to initialize Reddit strategy: {e}")
        
        # Stocktwits
        if platform_configs.get("stocktwits", {}).get("enabled", False):
            try:
                stocktwits_config = platform_configs.get("stocktwits", {})
                self.platform_strategies["stocktwits"] = StocktwitsStrategy(
                    config=stocktwits_config,
                    feedback_file=stocktwits_config.get("feedback_file", "social/data/stocktwits_feedback.json")
                )
                logger.info(" Stocktwits strategy initialized")
            except Exception as e:
                logger.error(f" Failed to initialize Stocktwits strategy: {e}")
        
        # LinkedIn
        if platform_configs.get("linkedin", {}).get("enabled", False):
            try:
                linkedin_config = platform_configs.get("linkedin", {})
                self.platform_strategies["linkedin"] = LinkedinStrategy(
                    config=linkedin_config,
                    feedback_file=linkedin_config.get("feedback_file", "social/data/linkedin_feedback.json")
                )
                logger.info(" LinkedIn strategy initialized")
            except Exception as e:
                logger.error(f" Failed to initialize LinkedIn strategy: {e}")
        
        # Instagram
        if platform_configs.get("instagram", {}).get("enabled", False):
            try:
                instagram_config = platform_configs.get("instagram", {})
                self.platform_strategies["instagram"] = InstagramStrategy(
                    config=instagram_config,
                    feedback_file=instagram_config.get("feedback_file", "social/data/instagram_feedback.json")
                )
                logger.info(" Instagram strategy initialized")
            except Exception as e:
                logger.error(f" Failed to initialize Instagram strategy: {e}")
    
    def _initialize_dashboard(self) -> None:
        """Initialize the unified community dashboard."""
        try:
            self.dashboard = CommunityDashboard(platform_strategies=self.platform_strategies)
            logger.info(" Unified Community Dashboard initialized")
        except Exception as e:
            logger.error(f" Failed to initialize Unified Community Dashboard: {e}")
            self.dashboard = None
    
    def _initialize_post_manager(self) -> None:
        """Initialize the social post manager."""
        try:
            self.post_manager = SocialPostManager(
                platform_configs=self.config.get("platforms", {}),
                platform_strategies=self.platform_strategies
            )
            logger.info(" Social Post Manager initialized")
        except Exception as e:
            logger.error(f" Failed to initialize Social Post Manager: {e}")
            self.post_manager = None
    
    def analyze_community_health(self) -> Dict[str, Any]:
        """Analyze community health across all platforms."""
        if not self.dashboard:
            logger.error(" Cannot analyze community health - dashboard not initialized")
            return {}
        
        try:
            # Collect latest metrics from all platforms
            self.dashboard.collect_all_platforms_metrics()
            
            # Generate health report
            health_report = self.dashboard.analyze_community_health()
            logger.info(f" Community health analysis completed with score: {health_report['overall_score']}")
            
            return health_report
        except Exception as e:
            logger.error(f" Error in community health analysis: {e}")
            return {}
    
    def generate_insights_and_recommendations(self) -> Dict[str, Any]:
        """Generate community insights and actionable recommendations."""
        if not self.dashboard:
            logger.error(" Cannot generate insights - dashboard not initialized")
            return {}
        
        try:
            insights = self.dashboard.generate_community_insights()
            logger.info(f" Generated {len(insights.get('recommended_actions', []))} community recommendations")
            return insights
        except Exception as e:
            logger.error(f" Error generating community insights: {e}")
            return {}
    
    def create_community_building_plan(self, days: int = 30) -> Dict[str, Any]:
        """Create a structured community building plan."""
        if not self.dashboard:
            logger.error(" Cannot create community plan - dashboard not initialized")
            return {}
        
        try:
            plan = self.dashboard.create_community_building_plan(days=days)
            logger.info(f" Created {days}-day community building plan")
            return plan
        except Exception as e:
            logger.error(f" Error creating community building plan: {e}")
            return {}
    
    def identify_advocates(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Identify top community advocates across all platforms."""
        if not self.dashboard:
            logger.error(" Cannot identify advocates - dashboard not initialized")
            return []
        
        try:
            advocates = self.dashboard.identify_top_community_members(limit=limit)
            logger.info(f" Identified {len(advocates)} community advocates")
            return advocates
        except Exception as e:
            logger.error(f" Error identifying community advocates: {e}")
            return []
    
    def post_across_platforms(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Post content across multiple platforms."""
        if not self.post_manager:
            logger.error(" Cannot post content - post manager not initialized")
            return {"success": False, "message": "Post manager not initialized"}
        
        try:
            results = self.post_manager.post_content(content)
            
            # Track community engagement for all successful posts
            if self.dashboard:
                for platform, result in results.items():
                    if result.get("success", False) and "post_id" in result:
                        # This would be expanded with actual engagement data in a real system
                        self.platform_strategies[platform].schedule_engagement_tracking(
                            post_id=result["post_id"],
                            duration_hours=24  # Track for 24 hours
                        )
            
            return results
        except Exception as e:
            logger.error(f" Error posting across platforms: {e}")
            return {"success": False, "message": str(e)}
    
    def track_member_interaction(self, platform: str, member_id: str, username: str, 
                               interaction_data: Dict[str, Any]) -> bool:
        """
        Track a community member's interaction.
        
        Args:
            platform: Social platform identifier
            member_id: Unique ID of the member on the platform
            username: Display name of the member
            interaction_data: Data about the interaction (type, content, etc.)
        
        Returns:
            bool: Success status
        """
        if not self.dashboard:
            logger.error(" Cannot track member - dashboard not initialized")
            return False
        
        try:
            # Analyze sentiment if content is available
            if "content" in interaction_data and self.dashboard.sentiment_analyzer:
                sentiment = self.dashboard.sentiment_analyzer.analyze(interaction_data["content"])
                interaction_data["sentiment"] = sentiment
            
            # Track the member
            self.dashboard.track_community_member(
                platform=platform,
                member_id=member_id,
                username=username,
                interaction_data=interaction_data
            )
            return True
        except Exception as e:
            logger.error(f" Error tracking member interaction: {e}")
            return False
    
    def optimize_platform_strategies(self) -> Dict[str, List[str]]:
        """Optimize strategies for each platform based on community data."""
        if not self.dashboard:
            logger.error(" Cannot optimize strategies - dashboard not initialized")
            return {}
        
        try:
            optimization = self.dashboard.run_strategy_optimization()
            
            # Apply the optimization recommendations to the strategies
            for platform, recommendations in optimization.items():
                if platform in self.platform_strategies:
                    strategy = self.platform_strategies[platform]
                    if hasattr(strategy, 'update_strategy_parameters'):
                        # This would be expanded with actual parameter updates in a real system
                        strategy.update_strategy_parameters({
                            "recommendations": recommendations,
                            "applied_at": "now"  # Would be a timestamp in real system
                        })
            
            logger.info(f" Optimized strategies for {len(optimization)} platforms")
            return optimization
        except Exception as e:
            logger.error(f" Error optimizing platform strategies: {e}")
            return {}
    
    def generate_visualizations(self, output_dir: Optional[str] = None) -> bool:
        """Generate visualizations of community metrics."""
        if not self.dashboard:
            logger.error(" Cannot generate visualizations - dashboard not initialized")
            return False
        
        try:
            if output_dir:
                self.dashboard.visualize_community_metrics(output_dir=output_dir)
            else:
                self.dashboard.visualize_community_metrics()
            
            logger.info(" Generated community visualizations")
            return True
        except Exception as e:
            logger.error(f" Error generating visualizations: {e}")
            return False
    
    def run_daily_community_management(self) -> Dict[str, Any]:
        """
        Execute a complete daily community management workflow.
        
        This includes:
        1. Collecting metrics
        2. Analyzing community health
        3. Generating insights
        4. Optimizing strategies
        5. Creating/updating community plan
        6. Generating visualizations
        
        Returns:
            Dict with results from each component
        """
        results = {
            "metrics_collected": False,
            "health_analyzed": False,
            "insights_generated": False,
            "strategies_optimized": False,
            "plan_updated": False,
            "visualizations_generated": False,
            "health_report": {},
            "insights": {},
            "optimizations": {}
        }
        
        try:
            # 1. Collect metrics
            if self.dashboard:
                metrics = self.dashboard.collect_all_platforms_metrics()
                results["metrics_collected"] = len(metrics) > 0
            
            # 2. Analyze health
            health_report = self.analyze_community_health()
            results["health_analyzed"] = bool(health_report)
            results["health_report"] = health_report
            
            # 3. Generate insights
            insights = self.generate_insights_and_recommendations()
            results["insights_generated"] = bool(insights)
            results["insights"] = insights
            
            # 4. Optimize strategies
            optimizations = self.optimize_platform_strategies()
            results["strategies_optimized"] = bool(optimizations)
            results["optimizations"] = optimizations
            
            # 5. Update community plan
            plan = self.create_community_building_plan(days=30)
            results["plan_updated"] = bool(plan)
            
            # 6. Generate visualizations
            viz_success = self.generate_visualizations()
            results["visualizations_generated"] = viz_success
            
            logger.info(" Daily community management workflow completed")
            return results
        except Exception as e:
            logger.error(f" Error in daily community management workflow: {e}")
            return results

# Example usage
if __name__ == "__main__":
    # Simple example configuration
    config = {
        "platforms": {
            "twitter": {
                "enabled": True,
                "api_key": os.environ.get("TWITTER_API_KEY"),
                "api_secret": os.environ.get("TWITTER_API_SECRET"),
                "access_token": os.environ.get("TWITTER_ACCESS_TOKEN"),
                "access_token_secret": os.environ.get("TWITTER_ACCESS_SECRET"),
                "feedback_file": "social/data/twitter_feedback.json"
            },
            "facebook": {
                "enabled": True,
                "page_id": os.environ.get("FACEBOOK_PAGE_ID"),
                "access_token": os.environ.get("FACEBOOK_ACCESS_TOKEN"),
                "feedback_file": "social/data/facebook_feedback.json"
            },
            "reddit": {
                "enabled": True,
                "client_id": os.environ.get("REDDIT_CLIENT_ID"),
                "client_secret": os.environ.get("REDDIT_CLIENT_SECRET"),
                "username": os.environ.get("REDDIT_USERNAME"),
                "password": os.environ.get("REDDIT_PASSWORD"),
                "feedback_file": "social/data/reddit_feedback.json"
            }
        }
    }
    
    # Initialize the manager
    manager = CommunityIntegrationManager(config)
    
    # Run the daily workflow
    results = manager.run_daily_community_management()
    
    # Check results
    if results["health_analyzed"]:
        score = results["health_report"].get("overall_score", 0)
        print(f"Community Health Score: {score}/100")
        
        if results["insights_generated"]:
            for action in results["insights"].get("recommended_actions", [])[:3]:
                print(f"Recommended Action: {action}")
