import os
import json
import logging
import datetime
from typing import Dict, List, Any, Optional, Union
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from dataclasses import dataclass
from PyQt5.QtCore import QObject, pyqtSignal

# Import platform-specific strategies
from social.strategies.twitter_strategy import TwitterStrategy
from social.strategies.facebook_strategy import FacebookStrategy
from social.strategies.instagram_strategy import InstagramStrategy
from social.strategies.reddit_strategy import RedditStrategy
from social.strategies.stocktwits_strategy import StocktwitsStrategy
from social.strategies.linkedin_strategy import LinkedinStrategy

# Import core components
from core.memory import UnifiedFeedbackMemory
from utils.SentimentAnalyzer import SentimentAnalyzer
from social.log_writer import logger, write_json_log
from core.PathManager import PathManager

@dataclass
class CommunityMetrics:
    """Data structure for standardized community metrics across platforms."""
    platform: str
    likes: int = 0
    comments: int = 0
    shares: int = 0
    follows: int = 0
    engagement_rate: float = 0.0
    sentiment_score: float = 0.0
    growth_rate: float = 0.0
    retention_rate: float = 0.0
    active_members: int = 0
    timestamp: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "platform": self.platform,
            "likes": self.likes,
            "comments": self.comments,
            "shares": self.shares,
            "follows": self.follows,
            "engagement_rate": self.engagement_rate,
            "sentiment_score": self.sentiment_score,
            "growth_rate": self.growth_rate,
            "retention_rate": self.retention_rate,
            "active_members": self.active_members,
            "timestamp": self.timestamp
        }


class UnifiedCommunityDashboard(QObject):
    """
    Provides a centralized dashboard for cross-platform community analytics and insights
    """
    # Signals
    metricsUpdated = pyqtSignal(dict)
    insightsGenerated = pyqtSignal(dict)
    topMembersUpdated = pyqtSignal(list)
    
    def __init__(self):
        super().__init__()
        self.strategies = {}
        self.metrics = {}
        self.insights = {}
        self.top_members = []
        self.sentiment_analyzer = SentimentAnalyzer()
        
        # Initialize platform strategies if available
        self._initialize_strategies()
        
        # Create data directory if it doesn't exist
        self.data_dir = os.path.join(PathManager.get_path('social'), 'data')
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Load saved data if available
        self._load_saved_data()
    
    def _initialize_strategies(self):
        """Initialize available social media platform strategies"""
        # Twitter
        try:
            self.strategies['twitter'] = TwitterStrategy()
        except Exception as e:
            print(f"Twitter strategy initialization failed: {e}")
        
        # Facebook
        try:
            self.strategies['facebook'] = FacebookStrategy()
        except Exception as e:
            print(f"Facebook strategy initialization failed: {e}")
        
        # Reddit
        try:
            self.strategies['reddit'] = RedditStrategy()
        except Exception as e:
            print(f"Reddit strategy initialization failed: {e}")
            
        # StockTwits
        try:
            self.strategies['stocktwits'] = StocktwitsStrategy()
        except Exception as e:
            print(f"StockTwits strategy initialization failed: {e}")
            
        # LinkedIn
        try:
            self.strategies['linkedin'] = LinkedinStrategy()
        except Exception as e:
            print(f"LinkedIn strategy initialization failed: {e}")
            
        # Instagram
        try:
            self.strategies['instagram'] = InstagramStrategy()
        except Exception as e:
            print(f"Instagram strategy initialization failed: {e}")
    
    def _load_saved_data(self):
        """Load previously saved community data"""
        # Load metrics
        metrics_file = os.path.join(self.data_dir, 'unified_community_metrics.json')
        if os.path.exists(metrics_file):
            try:
                with open(metrics_file, 'r') as f:
                    self.metrics = json.load(f)
            except Exception as e:
                print(f"Error loading metrics data: {e}")
        
        # Load insights
        insights_file = os.path.join(self.data_dir, 'community_insights.json')
        if os.path.exists(insights_file):
            try:
                with open(insights_file, 'r') as f:
                    self.insights = json.load(f)
            except Exception as e:
                print(f"Error loading insights data: {e}")
        
        # Load top members
        members_file = os.path.join(self.data_dir, 'unified_community_members.json')
        if os.path.exists(members_file):
            try:
                with open(members_file, 'r') as f:
                    self.top_members = json.load(f)
            except Exception as e:
                print(f"Error loading top members data: {e}")
    
    def save_data(self):
        """Save current data to files"""
        # Save metrics
        metrics_file = os.path.join(self.data_dir, 'unified_community_metrics.json')
        try:
            with open(metrics_file, 'w') as f:
                json.dump(self.metrics, f, indent=4)
        except Exception as e:
            print(f"Error saving metrics data: {e}")
        
        # Save insights
        insights_file = os.path.join(self.data_dir, 'community_insights.json')
        try:
            with open(insights_file, 'w') as f:
                json.dump(self.insights, f, indent=4)
        except Exception as e:
            print(f"Error saving insights data: {e}")
        
        # Save top members
        members_file = os.path.join(self.data_dir, 'unified_community_members.json')
        try:
            with open(members_file, 'w') as f:
                json.dump(self.top_members, f, indent=4)
        except Exception as e:
            print(f"Error saving top members data: {e}")
    
    def update_metrics(self):
        """Update community metrics from all platforms"""
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Create entry for current time if not exists
        if now not in self.metrics:
            self.metrics[now] = {
                "total": {
                    "engagement_rate": 0,
                    "sentiment_score": 0,
                    "growth_rate": 0,
                    "active_members": 0,
                    "content_interactions": 0,
                    "community_health_score": 0
                },
                "platforms": {}
            }
        
        # Collect metrics from each platform
        total_metrics = {
            "engagement_rate": 0,
            "sentiment_score": 0,
            "growth_rate": 0,
            "active_members": 0,
            "content_interactions": 0
        }
        
        platform_count = 0
        
        for platform, strategy in self.strategies.items():
            try:
                # Get metrics from platform strategy
                platform_metrics = strategy.analyze_engagement_metrics()
                
                # Add sentiment analysis
                content_samples = strategy.get_recent_content(limit=100)
                if content_samples:
                    sentiment = self.sentiment_analyzer.analyze_batch(content_samples)
                    platform_metrics["sentiment_score"] = sentiment["compound"]
                else:
                    platform_metrics["sentiment_score"] = 0
                
                # Add to totals
                for key in total_metrics:
                    if key in platform_metrics:
                        total_metrics[key] += platform_metrics[key]
                
                # Save platform metrics
                self.metrics[now]["platforms"][platform] = platform_metrics
                platform_count += 1
                
            except Exception as e:
                print(f"Error updating metrics for {platform}: {e}")
        
        # Calculate averages for the total metrics
        if platform_count > 0:
            for key in total_metrics:
                total_metrics[key] /= platform_count
        
        # Calculate community health score (weighted average)
        health_score = (
            total_metrics["engagement_rate"] * 0.3 +
            (total_metrics["sentiment_score"] + 1) * 0.5 * 0.25 +  # Normalize from [-1,1] to [0,1]
            total_metrics["growth_rate"] * 0.25 +
            min(1.0, total_metrics["active_members"] / 1000) * 0.2  # Cap at 1000 active members
        ) * 100  # Convert to 0-100 scale
        
        total_metrics["community_health_score"] = round(health_score, 1)
        
        # Update the total metrics
        self.metrics[now]["total"] = total_metrics
        
        # Emit signal with latest metrics
        self.metricsUpdated.emit(self.metrics[now])
        
        # Save data
        self.save_data()
        
        return self.metrics[now]
    
    def update_top_members(self):
        """Identify and update top community members across all platforms"""
        members = {}
        
        # Collect member data from each platform
        for platform, strategy in self.strategies.items():
            try:
                platform_members = strategy.get_top_members(limit=50)
                
                for member in platform_members:
                    member_id = f"{platform}:{member['id']}"
                    
                    if member_id in members:
                        # Update existing member data
                        members[member_id]["engagement_score"] += member["engagement_score"]
                        members[member_id]["platforms"].append(platform)
                    else:
                        # Add new member
                        members[member_id] = {
                            "id": member["id"],
                            "name": member["name"],
                            "primary_platform": platform,
                            "platforms": [platform],
                            "engagement_score": member["engagement_score"],
                            "sentiment_score": member.get("sentiment_score", 0),
                            "last_interaction": member.get("last_interaction", ""),
                            "profile_url": member.get("profile_url", "")
                        }
            except Exception as e:
                print(f"Error getting top members for {platform}: {e}")
        
        # Convert to list and sort by engagement score
        members_list = list(members.values())
        members_list.sort(key=lambda x: x["engagement_score"], reverse=True)
        
        # Keep top 100 members
        self.top_members = members_list[:100]
        
        # Emit signal with updated members
        self.topMembersUpdated.emit(self.top_members)
        
        # Save data
        self.save_data()
        
        return self.top_members
    
    def generate_insights(self):
        """Generate actionable insights based on community metrics"""
        # Ensure we have metrics data
        if not self.metrics:
            return {"error": "No metrics data available"}
        
        # Get timestamps and convert to datetime objects
        timestamps = list(self.metrics.keys())
        timestamps.sort()
        
        # Need at least two data points for trend analysis
        if len(timestamps) < 2:
            return {"error": "Not enough historical data for insights"}
        
        # Get current and previous metrics
        current = self.metrics[timestamps[-1]]
        previous = self.metrics[timestamps[-2]]
        
        # Calculate trends
        trends = self._calculate_trends(current, previous)
        
        # Generate platform-specific insights
        platform_insights = {}
        for platform in current["platforms"]:
            if platform in previous["platforms"]:
                platform_trends = self._calculate_trends(
                    current["platforms"][platform],
                    previous["platforms"][platform]
                )
                platform_insights[platform] = self._generate_platform_insights(
                    platform, platform_trends
                )
        
        # Generate overall insights
        overall_insights = self._generate_overall_insights(trends, platform_insights)
        
        # Create insights object
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.insights[now] = {
            "overall": overall_insights,
            "platforms": platform_insights,
            "trends": trends,
            "generated_at": now
        }
        
        # Emit signal with new insights
        self.insightsGenerated.emit(self.insights[now])
        
        # Save data
        self.save_data()
        
        return self.insights[now]
    
    def _calculate_trends(self, current, previous):
        """Calculate trends between current and previous metrics"""
        trends = {}
        
        # For total metrics
        if "total" in current and "total" in previous:
            trends["total"] = {}
            for metric, value in current["total"].items():
                prev_value = previous["total"].get(metric, 0)
                if prev_value != 0:
                    change = ((value - prev_value) / prev_value) * 100
                else:
                    change = 0
                trends["total"][metric] = {
                    "value": value,
                    "previous": prev_value,
                    "change": round(change, 2),
                    "direction": "up" if change > 0 else "down" if change < 0 else "stable"
                }
        
        # For platform metrics
        if "platforms" in current and "platforms" in previous:
            trends["platforms"] = {}
            for platform, metrics in current["platforms"].items():
                if platform in previous["platforms"]:
                    trends["platforms"][platform] = {}
                    for metric, value in metrics.items():
                        prev_value = previous["platforms"][platform].get(metric, 0)
                        if prev_value != 0:
                            change = ((value - prev_value) / prev_value) * 100
                        else:
                            change = 0
                        trends["platforms"][platform][metric] = {
                            "value": value,
                            "previous": prev_value,
                            "change": round(change, 2),
                            "direction": "up" if change > 0 else "down" if change < 0 else "stable"
                        }
        
        return trends
    
    def _generate_platform_insights(self, platform, trends):
        """Generate insights for a specific platform"""
        insights = {
            "strengths": [],
            "weaknesses": [],
            "opportunities": [],
            "recommendations": []
        }
        
        # Identify strengths (metrics with positive changes)
        for metric, data in trends.items():
            if data["direction"] == "up" and data["change"] > 5:
                strength = f"{metric.replace('_', ' ').title()} increased by {data['change']}%"
                insights["strengths"].append(strength)
        
        # Identify weaknesses (metrics with negative changes)
        for metric, data in trends.items():
            if data["direction"] == "down" and data["change"] < -5:
                weakness = f"{metric.replace('_', ' ').title()} decreased by {abs(data['change'])}%"
                insights["weaknesses"].append(weakness)
        
        # Generate platform-specific recommendations
        if platform == "twitter":
            if "engagement_rate" in trends and trends["engagement_rate"]["direction"] == "down":
                insights["recommendations"].append(
                    "Increase tweet frequency during peak hours"
                )
                insights["recommendations"].append(
                    "Use more hashtags relevant to your community's interests"
                )
                insights["opportunities"].append(
                    "Create Twitter polls to boost engagement"
                )
            
            if "sentiment_score" in trends and trends["sentiment_score"]["direction"] == "down":
                insights["recommendations"].append(
                    "Address negative feedback promptly and publicly"
                )
                insights["opportunities"].append(
                    "Launch a positive hashtag campaign"
                )
        
        elif platform == "facebook":
            if "engagement_rate" in trends and trends["engagement_rate"]["direction"] == "down":
                insights["recommendations"].append(
                    "Post more video content, which typically gets higher engagement"
                )
                insights["recommendations"].append(
                    "Create more interactive posts (questions, polls)"
                )
                insights["opportunities"].append(
                    "Consider Facebook Live sessions to boost engagement"
                )
        
        elif platform == "reddit":
            if "engagement_rate" in trends and trends["engagement_rate"]["direction"] == "down":
                insights["recommendations"].append(
                    "Create more discussion-oriented posts"
                )
                insights["recommendations"].append(
                    "Engage more with commenters on your posts"
                )
                insights["opportunities"].append(
                    "Host an AMA (Ask Me Anything) session"
                )
        
        # Add generic recommendations if we don't have platform-specific ones
        if not insights["recommendations"]:
            insights["recommendations"] = [
                "Create more engaging content that encourages discussion",
                "Respond promptly to comments and messages",
                "Post during peak activity hours for your audience"
            ]
            
            # Add opportunities
            insights["opportunities"] = [
                "Collaborate with influential community members",
                "Create exclusive content for your most engaged followers",
                "Run a community challenge or contest"
            ]
        
        return insights
    
    def _generate_overall_insights(self, trends, platform_insights):
        """Generate overall community insights across platforms"""
        insights = {
            "summary": "",
            "strengths": [],
            "weaknesses": [],
            "opportunities": [],
            "recommendations": []
        }
        
        # Generate summary
        total_trends = trends.get("total", {})
        health_trend = total_trends.get("community_health_score", {})
        health_score = health_trend.get("value", 0)
        health_change = health_trend.get("change", 0)
        health_direction = health_trend.get("direction", "stable")
        
        if health_score > 75:
            status = "thriving"
        elif health_score > 50:
            status = "healthy"
        elif health_score > 25:
            status = "needs attention"
        else:
            status = "at risk"
        
        insights["summary"] = f"Your community is {status} with a health score of {health_score}. "
        if health_direction == "up":
            insights["summary"] += f"It has improved by {health_change}% since the last measurement."
        elif health_direction == "down":
            insights["summary"] += f"It has declined by {abs(health_change)}% since the last measurement."
        else:
            insights["summary"] += "It has remained stable since the last measurement."
        
        # Aggregate platform strengths and weaknesses
        for platform, platform_insight in platform_insights.items():
            for strength in platform_insight["strengths"]:
                insights["strengths"].append(f"{platform.capitalize()}: {strength}")
            
            for weakness in platform_insight["weaknesses"]:
                insights["weaknesses"].append(f"{platform.capitalize()}: {weakness}")
        
        # Top overall recommendations
        if health_score < 50:
            # For struggling communities
            insights["recommendations"] = [
                "Focus on core engagement: respond to every comment and message",
                "Create more value-driven content that addresses community needs",
                "Re-evaluate posting frequency and timing",
                "Consider a community survey to understand member needs"
            ]
        else:
            # For healthy communities
            insights["recommendations"] = [
                "Identify and nurture potential community advocates",
                "Create exclusive content for your most engaged members",
                "Consider expanding to additional platforms where your audience is active",
                "Implement a community recognition program"
            ]
        
        # Add cross-platform opportunities
        insights["opportunities"] = [
            "Create a consistent cross-platform content strategy",
            "Implement a community ambassador program",
            "Develop a content calendar based on community metrics",
            "Consider creating platform-specific content for each community"
        ]
        
        # Add best performing platform recommendation
        best_platform = None
        best_engagement = -1
        
        for platform, platform_data in trends.get("platforms", {}).items():
            if "engagement_rate" in platform_data:
                engagement = platform_data["engagement_rate"]["value"]
                if engagement > best_engagement:
                    best_engagement = engagement
                    best_platform = platform
        
        if best_platform:
            insights["recommendations"].append(
                f"Consider adapting your {best_platform.capitalize()} strategy to other platforms"
            )
        
        return insights
    
    def get_metrics_history(self, days=30, platform=None):
        """Get historical metrics for the specified period"""
        # Ensure we have metrics data
        if not self.metrics:
            return []
        
        # Calculate cutoff date
        cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
        cutoff_str = cutoff.strftime("%Y-%m-%d")
        
        # Filter metrics by date
        filtered_metrics = {}
        for timestamp, metrics in self.metrics.items():
            if timestamp.split(" ")[0] >= cutoff_str:
                filtered_metrics[timestamp] = metrics
        
        # If platform is specified, extract only that platform's data
        if platform and platform != "all":
            platform_metrics = []
            for timestamp, metrics in filtered_metrics.items():
                if "platforms" in metrics and platform in metrics["platforms"]:
                    platform_metrics.append({
                        "timestamp": timestamp,
                        "metrics": metrics["platforms"][platform]
                    })
            return platform_metrics
        
        # Otherwise return all metrics
        return [{"timestamp": t, "metrics": m} for t, m in filtered_metrics.items()]
    
    def get_latest_metrics(self, platform=None):
        """Get the most recent metrics"""
        # Ensure we have metrics data
        if not self.metrics:
            return {}
        
        # Get the most recent timestamp
        timestamps = list(self.metrics.keys())
        timestamps.sort()
        latest = timestamps[-1] if timestamps else None
        
        if not latest:
            return {}
        
        # If platform is specified, return only that platform's metrics
        if platform and platform != "all":
            if "platforms" in self.metrics[latest] and platform in self.metrics[latest]["platforms"]:
                return self.metrics[latest]["platforms"][platform]
            return {}
        
        # Otherwise return all metrics
        return self.metrics[latest]
    
    def generate_metrics_chart(self, metric="engagement_rate", days=30, platform=None):
        """Generate a chart for the specified metric"""
        # Get historical data
        history = self.get_metrics_history(days, platform)
        
        if not history:
            return None
        
        # Extract data for the chart
        dates = []
        values = []
        
        for entry in history:
            timestamp = entry["timestamp"]
            metrics = entry["metrics"]
            
            if platform and platform != "all":
                if metric in metrics:
                    dates.append(timestamp.split(" ")[0])
                    values.append(metrics[metric])
            else:
                if "total" in metrics and metric in metrics["total"]:
                    dates.append(timestamp.split(" ")[0])
                    values.append(metrics["total"][metric])
        
        if not dates or not values:
            return None
        
        # Create the chart
        plt.figure(figsize=(10, 6))
        plt.plot(dates, values, marker='o')
        plt.title(f"{metric.replace('_', ' ').title()} over time")
        plt.xlabel("Date")
        plt.ylabel(metric.replace('_', ' ').title())
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Save the chart to a temporary file
        chart_path = os.path.join(self.data_dir, f"{metric}_chart.png")
        plt.savefig(chart_path)
        plt.close()
        
        return chart_path
    
    def get_platform_status(self):
        """Get the status of each platform integration"""
        status = {}
        
        for platform in ["twitter", "facebook", "reddit", "stocktwits", "linkedin", "instagram"]:
            if platform in self.strategies:
                status[platform] = {
                    "active": True,
                    "connected": self.strategies[platform].is_authenticated(),
                    "last_updated": self.strategies[platform].get_last_updated()
                }
            else:
                status[platform] = {
                    "active": False,
                    "connected": False,
                    "last_updated": None
                }
        
        return status
    
    def get_community_building_plan(self):
        """Generate a 30-day community building plan based on insights"""
        # Ensure we have insights
        if not self.insights:
            return {"error": "No insights available to create a plan"}
        
        # Get the latest insights
        timestamps = list(self.insights.keys())
        timestamps.sort()
        latest = timestamps[-1] if timestamps else None
        
        if not latest:
            return {"error": "No insights available to create a plan"}
        
        latest_insights = self.insights[latest]
        
        # Create the plan
        plan = {
            "title": "30-Day Community Building Plan",
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "days": []
        }
        
        # Define activities based on insights
        engagement_activities = [
            "Create a poll asking for community feedback",
            "Host a live Q&A session",
            "Share user-generated content",
            "Create a roundup of top community contributions",
            "Post a discussion thread on a trending topic",
            "Share a success story from a community member",
            "Create a challenge for community members",
            "Host a virtual meetup"
        ]
        
        content_activities = [
            "Share an educational tutorial",
            "Create a 'behind the scenes' post",
            "Share industry news with your analysis",
            "Create a resource guide for your community",
            "Share a case study",
            "Create a list of tips or best practices",
            "Share an inspirational quote or story",
            "Create a comparison or review post"
        ]
        
        community_activities = [
            "Reach out to your top 5 most engaged members",
            "Create a spotlight feature for an active member",
            "Start a mentorship or buddy program",
            "Create a special role for active contributors",
            "Send a survey to understand community needs",
            "Create a community newsletter",
            "Establish community guidelines or values",
            "Create a resource library for your community"
        ]
        
        # Generate daily activities for 30 days
        for day in range(1, 31):
            # Determine focus areas based on day of week
            weekday = (datetime.datetime.now() + datetime.timedelta(days=day)).weekday()
            
            if weekday == 0:  # Monday
                focus = "Engagement"
                activities = engagement_activities
            elif weekday == 2:  # Wednesday
                focus = "Content"
                activities = content_activities
            elif weekday == 4:  # Friday
                focus = "Community Building"
                activities = community_activities
            else:
                # Mix of activities for other days
                focus = "Mixed Focus"
                activities = engagement_activities + content_activities + community_activities
            
            # Select activities for the day
            daily_activities = []
            for _ in range(min(2, len(activities))):
                if activities:
                    activity = activities.pop(0)
                    daily_activities.append(activity)
                    activities.append(activity)  # Put back at end for reuse
            
            # Create day entry
            day_date = (datetime.datetime.now() + datetime.timedelta(days=day)).strftime("%Y-%m-%d")
            plan["days"].append({
                "day": day,
                "date": day_date,
                "focus": focus,
                "activities": daily_activities,
                "platforms": self._get_recommended_platforms_for_day(day)
            })
        
        return plan
    
    def _get_recommended_platforms_for_day(self, day):
        """Determine which platforms to focus on for a specific day"""
        # Get platform status
        status = self.get_platform_status()
        active_platforms = [p for p, s in status.items() if s["active"] and s["connected"]]
        
        if not active_platforms:
            return ["No active platforms"]
        
        # Rotate through platforms based on day
        if day % 7 == 1:  # Day 1, 8, 15, 22, 29
            return ["All platforms"]
        elif len(active_platforms) >= 3:
            # Return different platform combos based on day
            index = day % len(active_platforms)
            return [active_platforms[index], active_platforms[(index+1) % len(active_platforms)]]
        else:
            # If we have few platforms, use all of them
            return active_platforms

# Example usage
if __name__ == "__main__":
    dashboard = UnifiedCommunityDashboard()
    metrics = dashboard.collect_all_platforms_metrics()
    health_report = dashboard.analyze_community_health()
    insights = dashboard.generate_community_insights()
    optimization = dashboard.run_strategy_optimization()
    plan = dashboard.create_community_building_plan(days=30)
    
    print("Community Dashboard initialized and test functions executed successfully.") 
