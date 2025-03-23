import os
import sys
import json
import datetime
from typing import Dict, Any, List, Optional
import logging

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, QPushButton, QFrame,
    QTableWidget, QTableWidgetItem, QComboBox, QScrollArea, QSplitter,
    QGraphicsView, QGraphicsScene, QProgressBar, QTextEdit, QGroupBox, QHeaderView,
    QGridLayout, QToolButton
)
from PyQt5.QtGui import QFont, QPixmap, QColor, QPainter, QPen, QBrush, QIcon
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QValueAxis, QPieSeries

# Import the community dashboard
from core.social.UnifiedCommunityDashboard import UnifiedCommunityDashboard, CommunityMetrics
from core.social.CommunityIntegrationManager import CommunityIntegrationManager
from utils.SentimentAnalyzer import SentimentAnalyzer

logger = logging.getLogger(__name__)

class CommunityDashboardTab(QWidget):
    """
    Provides a comprehensive dashboard for monitoring social media community metrics
    and insights across all platforms.
    """
    
    # Signals
    platformSelected = pyqtSignal(str)
    refreshRequested = pyqtSignal()
    insightsRequested = pyqtSignal()
    
    def __init__(self, parent=None, community_manager=None):
        super().__init__(parent)
        
        # Store parent reference
        self.parent = parent
        
        # Initialize the integration manager or use the provided one
        self.integration_manager = community_manager or CommunityIntegrationManager()
        
        # Get dashboard reference from integration manager
        self.dashboard = self.integration_manager.dashboard
        
        # Connect signals from dashboard if available
        if self.dashboard:
            if hasattr(self.dashboard, 'metricsUpdated'):
                self.dashboard.metricsUpdated.connect(self.update_metrics_view)
            if hasattr(self.dashboard, 'insightsGenerated'):
                self.dashboard.insightsGenerated.connect(self.update_insights_view)
            if hasattr(self.dashboard, 'topMembersUpdated'):
                self.dashboard.topMembersUpdated.connect(self.update_members_view)
        
        # Setup UI
        self.setup_ui()
        
        # Setup refresh timer (every 30 minutes)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(30 * 60 * 1000)  # 30 minutes
        
        # Initial data load
        self.refresh_data()
    
    def setup_ui(self):
        """Setup the UI components for the dashboard"""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # ===== Control Panel =====
        control_panel = QHBoxLayout()
        
        # Platform selector
        self.platform_selector = QComboBox()
        self.platform_selector.addItem("All Platforms", "all")
        
        # Add available platforms
        platforms = self.integration_manager.get_available_platforms()
        for platform_id, platform in platforms.items():
            self.platform_selector.addItem(platform["name"], platform_id)
        
        self.platform_selector.currentIndexChanged.connect(self.on_platform_changed)
        
        # Refresh button
        self.refresh_button = QPushButton("Refresh Data")
        self.refresh_button.clicked.connect(self.refresh_data)
        
        # Insights button
        self.insights_button = QPushButton("Generate Insights")
        self.insights_button.clicked.connect(self.generate_insights)
        
        # Add controls to panel
        control_panel.addWidget(QLabel("Platform:"))
        control_panel.addWidget(self.platform_selector)
        control_panel.addStretch()
        control_panel.addWidget(self.refresh_button)
        control_panel.addWidget(self.insights_button)
        
        main_layout.addLayout(control_panel)
        
        # ===== Dashboard Tab Widget =====
        self.tab_widget = QTabWidget()
        
        # === Overview Tab ===
        self.overview_tab = QWidget()
        self.setup_overview_tab()
        self.tab_widget.addTab(self.overview_tab, "Overview")
        
        # === Insights Tab ===
        self.insights_tab = QWidget()
        self.setup_insights_tab()
        self.tab_widget.addTab(self.insights_tab, "Insights")
        
        # === Community Tab ===
        self.community_tab = QWidget()
        self.setup_community_tab()
        self.tab_widget.addTab(self.community_tab, "Community")
        
        # === Planning Tab ===
        self.planning_tab = QWidget()
        self.setup_planning_tab()
        self.tab_widget.addTab(self.planning_tab, "Planning")
        
        main_layout.addWidget(self.tab_widget)
    
    def setup_overview_tab(self):
        """Setup the Overview tab"""
        layout = QVBoxLayout(self.overview_tab)
        
        # ===== Health Score Panel =====
        health_panel = QHBoxLayout()
        
        # Health score widget
        health_group = QGroupBox("Community Health Score")
        health_layout = QVBoxLayout(health_group)
        
        self.health_score_label = QLabel("--")
        self.health_score_label.setAlignment(Qt.AlignCenter)
        self.health_score_label.setStyleSheet("font-size: 48px; font-weight: bold;")
        
        self.health_status_label = QLabel("No data available")
        self.health_status_label.setAlignment(Qt.AlignCenter)
        self.health_status_label.setStyleSheet("font-size: 18px;")
        
        self.health_progress = QProgressBar()
        self.health_progress.setRange(0, 100)
        self.health_progress.setValue(0)
        self.health_progress.setTextVisible(False)
        self.health_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                width: 1px;
            }
        """)
        
        health_layout.addWidget(self.health_score_label)
        health_layout.addWidget(self.health_progress)
        health_layout.addWidget(self.health_status_label)
        
        health_panel.addWidget(health_group)
        
        # Key metrics group
        metrics_group = QGroupBox("Key Metrics")
        metrics_layout = QGridLayout(metrics_group)
        
        # Create metric widgets
        self.metric_widgets = {
            "engagement_rate": {
                "label": QLabel("Engagement Rate"),
                "value": QLabel("--"),
                "change": QLabel("")
            },
            "sentiment_score": {
                "label": QLabel("Sentiment Score"),
                "value": QLabel("--"),
                "change": QLabel("")
            },
            "growth_rate": {
                "label": QLabel("Growth Rate"),
                "value": QLabel("--"),
                "change": QLabel("")
            },
            "active_members": {
                "label": QLabel("Active Members"),
                "value": QLabel("--"),
                "change": QLabel("")
            }
        }
        
        # Add metrics to layout
        row = 0
        for metric_id, widgets in self.metric_widgets.items():
            metrics_layout.addWidget(widgets["label"], row, 0)
            widgets["value"].setAlignment(Qt.AlignRight)
            widgets["value"].setStyleSheet("font-weight: bold; font-size: 16px;")
            metrics_layout.addWidget(widgets["value"], row, 1)
            widgets["change"].setAlignment(Qt.AlignRight)
            metrics_layout.addWidget(widgets["change"], row, 2)
            row += 1
        
        health_panel.addWidget(metrics_group)
        
        layout.addLayout(health_panel)
        
        # ===== Platform Status Panel =====
        platform_group = QGroupBox("Platform Status")
        platform_layout = QTableWidget()
        self.platform_table = platform_layout
        
        platform_layout.setColumnCount(5)
        platform_layout.setHorizontalHeaderLabels(["Platform", "Status", "Last Updated", "Engagement", "Content"])
        platform_layout.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        platform_group.setLayout(QVBoxLayout())
        platform_group.layout().addWidget(platform_layout)
        
        layout.addWidget(platform_group)
        
        # ===== Latest Activity Panel =====
        activity_group = QGroupBox("Latest Community Activity")
        activity_layout = QVBoxLayout(activity_group)
        
        self.activity_log = QTextEdit()
        self.activity_log.setReadOnly(True)
        self.activity_log.setMaximumHeight(150)
        
        activity_layout.addWidget(self.activity_log)
        
        layout.addWidget(activity_group)
    
    def setup_insights_tab(self):
        """Setup the Insights tab"""
        layout = QVBoxLayout(self.insights_tab)
        
        # Create a scroll area for insights
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # ===== Summary Panel =====
        summary_group = QGroupBox("Community Summary")
        summary_layout = QVBoxLayout(summary_group)
        
        self.summary_text = QLabel("No insights available. Click 'Generate Insights' to analyze your community data.")
        self.summary_text.setWordWrap(True)
        self.summary_text.setStyleSheet("font-size: 14px;")
        
        summary_layout.addWidget(self.summary_text)
        
        scroll_layout.addWidget(summary_group)
        
        # ===== Strengths & Weaknesses =====
        strengths_weaknesses = QHBoxLayout()
        
        # Strengths group
        strengths_group = QGroupBox("Community Strengths")
        strengths_layout = QVBoxLayout(strengths_group)
        
        self.strengths_list = QTextEdit()
        self.strengths_list.setReadOnly(True)
        
        strengths_layout.addWidget(self.strengths_list)
        strengths_weaknesses.addWidget(strengths_group)
        
        # Weaknesses group
        weaknesses_group = QGroupBox("Areas for Improvement")
        weaknesses_layout = QVBoxLayout(weaknesses_group)
        
        self.weaknesses_list = QTextEdit()
        self.weaknesses_list.setReadOnly(True)
        
        weaknesses_layout.addWidget(self.weaknesses_list)
        strengths_weaknesses.addWidget(weaknesses_group)
        
        scroll_layout.addLayout(strengths_weaknesses)
        
        # ===== Opportunities & Recommendations =====
        opportunities_recommendations = QHBoxLayout()
        
        # Opportunities group
        opportunities_group = QGroupBox("Opportunities")
        opportunities_layout = QVBoxLayout(opportunities_group)
        
        self.opportunities_list = QTextEdit()
        self.opportunities_list.setReadOnly(True)
        
        opportunities_layout.addWidget(self.opportunities_list)
        opportunities_recommendations.addWidget(opportunities_group)
        
        # Recommendations group
        recommendations_group = QGroupBox("Recommendations")
        recommendations_layout = QVBoxLayout(recommendations_group)
        
        self.recommendations_list = QTextEdit()
        self.recommendations_list.setReadOnly(True)
        
        recommendations_layout.addWidget(self.recommendations_list)
        opportunities_recommendations.addWidget(recommendations_group)
        
        scroll_layout.addLayout(opportunities_recommendations)
        
        # ===== Platform-specific Insights =====
        platform_insights_group = QGroupBox("Platform-specific Insights")
        platform_insights_layout = QVBoxLayout(platform_insights_group)
        
        self.platform_insights = QTabWidget()
        
        # Add a tab for each platform
        platforms = self.integration_manager.get_available_platforms()
        for platform_id, platform in platforms.items():
            platform_tab = QWidget()
            platform_tab_layout = QVBoxLayout(platform_tab)
            
            platform_text = QTextEdit()
            platform_text.setReadOnly(True)
            
            # Store reference to the text widget
            setattr(self, f"{platform_id}_insights", platform_text)
            
            platform_tab_layout.addWidget(platform_text)
            self.platform_insights.addTab(platform_tab, platform["name"])
        
        platform_insights_layout.addWidget(self.platform_insights)
        scroll_layout.addWidget(platform_insights_group)
        
        # Add scroll area to layout
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)
    
    def setup_community_tab(self):
        """Setup the Community tab"""
        layout = QVBoxLayout(self.community_tab)
        
        # ===== Top Members Panel =====
        top_members_group = QGroupBox("Top Community Members")
        top_members_layout = QVBoxLayout(top_members_group)
        
        self.top_members_table = QTableWidget()
        self.top_members_table.setColumnCount(6)
        self.top_members_table.setHorizontalHeaderLabels(["Name", "Platform", "Engagement Score", "Sentiment", "Last Interaction", "Profile"])
        self.top_members_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        top_members_layout.addWidget(self.top_members_table)
        
        layout.addWidget(top_members_group)
        
        # ===== Member Statistics Panel =====
        member_stats_group = QGroupBox("Member Statistics")
        member_stats_layout = QGridLayout(member_stats_group)
        
        # Create statistic widgets
        self.member_stats = {
            "total_members": {
                "label": QLabel("Total Members"),
                "value": QLabel("--")
            },
            "active_percentage": {
                "label": QLabel("Active Members (%)"),
                "value": QLabel("--")
            },
            "new_members": {
                "label": QLabel("New Members (30d)"),
                "value": QLabel("--")
            },
            "churn_rate": {
                "label": QLabel("Churn Rate (%)"),
                "value": QLabel("--")
            }
        }
        
        # Add statistics to layout
        row = 0
        col = 0
        for stat_id, widgets in self.member_stats.items():
            member_stats_layout.addWidget(widgets["label"], row, col)
            widgets["value"].setStyleSheet("font-weight: bold; font-size: 16px;")
            member_stats_layout.addWidget(widgets["value"], row, col + 1)
            
            col += 2
            if col >= 4:
                col = 0
                row += 1
        
        layout.addWidget(member_stats_group)
        
        # ===== Member Engagement Chart =====
        engagement_group = QGroupBox("Member Engagement Trends")
        engagement_layout = QVBoxLayout(engagement_group)
        
        self.engagement_chart_label = QLabel("No engagement data available")
        self.engagement_chart_label.setAlignment(Qt.AlignCenter)
        
        engagement_layout.addWidget(self.engagement_chart_label)
        
        layout.addWidget(engagement_group)
    
    def setup_planning_tab(self):
        """Setup the Planning tab"""
        layout = QVBoxLayout(self.planning_tab)
        
        # ===== Community Building Plan =====
        plan_group = QGroupBox("30-Day Community Building Plan")
        plan_layout = QVBoxLayout(plan_group)
        
        # Add controls
        plan_controls = QHBoxLayout()
        
        plan_controls.addWidget(QLabel("Focus Area:"))
        self.focus_selector = QComboBox()
        self.focus_selector.addItems(["All", "Engagement", "Content", "Community Building", "Mixed Focus"])
        self.focus_selector.currentTextChanged.connect(self.on_focus_changed)
        plan_controls.addWidget(self.focus_selector)
        
        plan_controls.addStretch()
        
        self.generate_plan_button = QPushButton("Generate New Plan")
        self.generate_plan_button.clicked.connect(self.generate_plan)
        plan_controls.addWidget(self.generate_plan_button)
        
        plan_layout.addLayout(plan_controls)
        
        # Add plan table
        self.plan_table = QTableWidget()
        self.plan_table.setColumnCount(4)
        self.plan_table.setHorizontalHeaderLabels(["Day", "Date", "Focus", "Activities"])
        self.plan_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.plan_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        
        plan_layout.addWidget(self.plan_table)
        
        layout.addWidget(plan_group)
        
        # ===== Content Strategy Panel =====
        content_group = QGroupBox("Content Strategy")
        content_layout = QVBoxLayout(content_group)
        
        self.content_strategy_text = QTextEdit()
        self.content_strategy_text.setReadOnly(True)
        self.content_strategy_text.setPlaceholderText("Content strategy recommendations will appear here after generating insights.")
        
        content_layout.addWidget(self.content_strategy_text)
        
        layout.addWidget(content_group)
    
    def refresh_data(self):
        """Refresh all dashboard data"""
        if not self.dashboard:
            self.add_activity_log("Error: Dashboard not initialized")
            return
        
        # Run daily management workflow through integration manager
        results = self.integration_manager.run_daily_community_management()
        
        if results["metrics_collected"]:
            # Update metrics view if metrics were collected
            metrics = self.dashboard.get_latest_metrics()
            self.update_metrics_view(metrics)
        
        if results["insights_generated"]:
            # Update insights view if insights were generated
            insights = results["insights"]
            self.update_insights_view(insights)
        
        # Update community members
        self.integration_manager.identify_advocates()
        if hasattr(self.dashboard, 'top_members'):
            self.update_members_view(self.dashboard.top_members)
        
        # Update platform status
        self.update_platform_status()
        
        # Update plan view if plan was updated
        if results["plan_updated"]:
            plan = self.integration_manager.create_community_building_plan()
            self.update_plan_view(plan)
        
        # Update activity log with new activity
        self.add_activity_log("Dashboard data refreshed")
    
    def generate_insights(self):
        """Generate fresh insights based on current data"""
        # Generate insights through integration manager
        insights = self.integration_manager.generate_insights_and_recommendations()
        
        if insights:
            # Update insights view
            self.update_insights_view(insights)
            
            # Also update content strategy
            content_strategy = self.generate_content_strategy(insights)
            self.content_strategy_text.setText(content_strategy)
        
        # Update activity log
        self.add_activity_log("Community insights generated")
    
    def generate_plan(self):
        """Generate a new community building plan"""
        # Get plan from integration manager
        plan = self.integration_manager.create_community_building_plan()
        
        if not plan or "error" in plan:
            error_msg = plan.get("error", "Unknown error generating plan") if plan else "Failed to generate plan"
            self.add_activity_log(f"Error generating plan: {error_msg}")
            return
        
        # Update plan table
        self.update_plan_view(plan)
        
        # Update activity log
        self.add_activity_log("New community building plan generated")
    
    def on_platform_changed(self, index):
        """Handle platform selector changes"""
        platform_id = self.platform_selector.currentData()
        self.platformSelected.emit(platform_id)
        
        # Update views with platform-specific data
        if self.dashboard:
            self.update_metrics_view(self.dashboard.get_latest_metrics(platform_id))
        
        # Update activity log
        if platform_id == "all":
            self.add_activity_log("Viewing all platforms")
        else:
            platform_name = self.platform_selector.currentText()
            self.add_activity_log(f"Viewing {platform_name} platform")
    
    def on_focus_changed(self, focus_text):
        """Handle focus selector changes"""
        # Get the plan and update view with new focus filter
        if hasattr(self.integration_manager, 'create_community_building_plan'):
            plan = self.integration_manager.create_community_building_plan()
            if plan:
                self.update_plan_view(plan)
    
    def update_metrics_view(self, metrics):
        """Update the metrics view with new data"""
        if not metrics:
            return
        
        # Update health score
        if "total" in metrics:
            total = metrics["total"]
            
            # Health score
            health_score = total.get("community_health_score", 0)
            self.health_score_label.setText(f"{health_score:.1f}")
            self.health_progress.setValue(int(health_score))
            
            # Set health status text and color
            if health_score > 75:
                status = "Thriving"
                color = "#4CAF50"  # Green
            elif health_score > 50:
                status = "Healthy"
                color = "#2196F3"  # Blue
            elif health_score > 25:
                status = "Needs Attention"
                color = "#FF9800"  # Orange
            else:
                status = "At Risk"
                color = "#F44336"  # Red
            
            self.health_status_label.setText(status)
            self.health_progress.setStyleSheet(f"""
                QProgressBar {{
                    border: 2px solid grey;
                    border-radius: 5px;
                    height: 20px;
                }}
                QProgressBar::chunk {{
                    background-color: {color};
                    width: 1px;
                }}
            """)
            
            # Update key metrics
            for metric_id, widgets in self.metric_widgets.items():
                if metric_id in total:
                    value = total[metric_id]
                    
                    # Format value based on metric type
                    if metric_id in ["engagement_rate", "growth_rate"]:
                        widgets["value"].setText(f"{value * 100:.1f}%")
                    elif metric_id == "sentiment_score":
                        widgets["value"].setText(f"{value:.2f}")
                    else:
                        widgets["value"].setText(f"{value:.0f}")
            
            # Add activity log entry
            self.add_activity_log(f"Metrics updated - Health score: {health_score:.1f}")
        
        # Platform-specific metrics
        elif self.platform_selector.currentData() != "all":
            platform_id = self.platform_selector.currentData()
            platform_name = self.platform_selector.currentText()
            
            # Update key metrics for this platform
            for metric_id, widgets in self.metric_widgets.items():
                if metric_id in metrics:
                    value = metrics[metric_id]
                    
                    # Format value based on metric type
                    if metric_id in ["engagement_rate", "growth_rate"]:
                        widgets["value"].setText(f"{value * 100:.1f}%")
                    elif metric_id == "sentiment_score":
                        widgets["value"].setText(f"{value:.2f}")
                    else:
                        widgets["value"].setText(f"{value:.0f}")
            
            # Add activity log entry
            self.add_activity_log(f"{platform_name} metrics updated")
    
    def update_insights_view(self, insights):
        """Update the insights view with new data"""
        if not insights:
            return
        
        # Update summary
        if "overall" in insights and "summary" in insights["overall"]:
            self.summary_text.setText(insights["overall"]["summary"])
        
        # Update strengths
        if "overall" in insights and "strengths" in insights["overall"]:
            self.strengths_list.clear()
            strengths = insights["overall"]["strengths"]
            if strengths:
                self.strengths_list.setText("\n".join(f"• {s}" for s in strengths))
            else:
                self.strengths_list.setText("No specific strengths identified.")
        
        # Update weaknesses
        if "overall" in insights and "weaknesses" in insights["overall"]:
            self.weaknesses_list.clear()
            weaknesses = insights["overall"]["weaknesses"]
            if weaknesses:
                self.weaknesses_list.setText("\n".join(f"• {w}" for w in weaknesses))
            else:
                self.weaknesses_list.setText("No specific weaknesses identified.")
        
        # Update opportunities
        if "overall" in insights and "opportunities" in insights["overall"]:
            self.opportunities_list.clear()
            opportunities = insights["overall"]["opportunities"]
            if opportunities:
                self.opportunities_list.setText("\n".join(f"• {o}" for o in opportunities))
            else:
                self.opportunities_list.setText("No specific opportunities identified.")
        
        # Update recommendations
        if "overall" in insights and "recommendations" in insights["overall"]:
            self.recommendations_list.clear()
            recommendations = insights["overall"]["recommendations"]
            if recommendations:
                self.recommendations_list.setText("\n".join(f"• {r}" for r in recommendations))
            else:
                self.recommendations_list.setText("No specific recommendations available.")
        
        # Update platform-specific insights
        if "platforms" in insights:
            for platform_id, platform_insight in insights["platforms"].items():
                # Get the text widget for this platform
                text_widget = getattr(self, f"{platform_id}_insights", None)
                if not text_widget:
                    continue
                
                text_widget.clear()
                
                # Add strengths
                if "strengths" in platform_insight and platform_insight["strengths"]:
                    text_widget.append("<b>Strengths:</b>")
                    for strength in platform_insight["strengths"]:
                        text_widget.append(f"• {strength}")
                    text_widget.append("")
                
                # Add weaknesses
                if "weaknesses" in platform_insight and platform_insight["weaknesses"]:
                    text_widget.append("<b>Areas for Improvement:</b>")
                    for weakness in platform_insight["weaknesses"]:
                        text_widget.append(f"• {weakness}")
                    text_widget.append("")
                
                # Add recommendations
                if "recommendations" in platform_insight and platform_insight["recommendations"]:
                    text_widget.append("<b>Recommendations:</b>")
                    for recommendation in platform_insight["recommendations"]:
                        text_widget.append(f"• {recommendation}")
                    text_widget.append("")
                
                # Add opportunities
                if "opportunities" in platform_insight and platform_insight["opportunities"]:
                    text_widget.append("<b>Opportunities:</b>")
                    for opportunity in platform_insight["opportunities"]:
                        text_widget.append(f"• {opportunity}")
        
        # Update content strategy
        content_strategy = self.generate_content_strategy(insights)
        self.content_strategy_text.setText(content_strategy)
        
        # Add activity log entry
        self.add_activity_log("Insights view updated with fresh analysis")
    
    def update_members_view(self, members):
        """Update the community members view with new data"""
        if not members:
            return
        
        # Update top members table
        self.top_members_table.setRowCount(len(members))
        
        for i, member in enumerate(members):
            # Name
            name_item = QTableWidgetItem(member["name"])
            self.top_members_table.setItem(i, 0, name_item)
            
            # Platform
            platform_item = QTableWidgetItem(member["primary_platform"].capitalize())
            self.top_members_table.setItem(i, 1, platform_item)
            
            # Engagement Score
            engagement_item = QTableWidgetItem(f"{member['engagement_score']:.1f}")
            engagement_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.top_members_table.setItem(i, 2, engagement_item)
            
            # Sentiment
            sentiment = member.get("sentiment_score", 0)
            sentiment_item = QTableWidgetItem()
            if sentiment > 0:
                sentiment_item.setText("Positive")
                sentiment_item.setForeground(QColor(76, 175, 80))  # Green
            elif sentiment < 0:
                sentiment_item.setText("Negative")
                sentiment_item.setForeground(QColor(244, 67, 54))  # Red
            else:
                sentiment_item.setText("Neutral")
            self.top_members_table.setItem(i, 3, sentiment_item)
            
            # Last Interaction
            last_interaction = member.get("last_interaction", "")
            interaction_item = QTableWidgetItem(last_interaction)
            self.top_members_table.setItem(i, 4, interaction_item)
            
            # Profile URL
            profile_url = member.get("profile_url", "")
            profile_item = QTableWidgetItem(profile_url)
            self.top_members_table.setItem(i, 5, profile_item)
        
        # Update member statistics
        # This would come from a more detailed analysis of the community
        # For now, we'll use placeholder calculations
        total_members = len(members)
        active_members = sum(1 for m in members if m["engagement_score"] > 10)
        active_percentage = (active_members / total_members * 100) if total_members > 0 else 0
        
        self.member_stats["total_members"]["value"].setText(str(total_members))
        self.member_stats["active_percentage"]["value"].setText(f"{active_percentage:.1f}%")
        
        # Add activity log entry
        self.add_activity_log(f"Community members view updated with {len(members)} members")
    
    def update_platform_status(self):
        """Update the platform status table"""
        # Get platform status from integration manager
        status = self.integration_manager.get_all_platforms()
        
        # Update table
        self.platform_table.setRowCount(len(status))
        
        row = 0
        for platform_id, platform_status in status.items():
            # Platform name
            platform_name = platform_status.get("name", platform_id.capitalize())
            platform_item = QTableWidgetItem(platform_name)
            self.platform_table.setItem(row, 0, platform_item)
            
            # Connection status
            status_text = "Connected" if platform_status.get("connected", False) else "Disconnected"
            status_item = QTableWidgetItem(status_text)
            if platform_status.get("connected", False):
                status_item.setForeground(QColor(76, 175, 80))  # Green
            else:
                status_item.setForeground(QColor(244, 67, 54))  # Red
            self.platform_table.setItem(row, 1, status_item)
            
            # Last updated
            last_updated = platform_status.get("last_connected") or "Never"
            updated_item = QTableWidgetItem(last_updated)
            self.platform_table.setItem(row, 2, updated_item)
            
            # Placeholder data for engagement and content
            engagement_item = QTableWidgetItem("--")
            self.platform_table.setItem(row, 3, engagement_item)
            
            content_item = QTableWidgetItem("--")
            self.platform_table.setItem(row, 4, content_item)
            
            row += 1
    
    def update_plan_view(self, plan):
        """Update the community building plan view"""
        if not plan or "error" in plan:
            return
        
        # Get focus filter
        focus_filter = self.focus_selector.currentText()
        
        # Filter days by focus if needed
        filtered_days = plan.get("days", [])
        if focus_filter != "All":
            filtered_days = [day for day in filtered_days if day.get("focus") == focus_filter]
        
        # Update table
        self.plan_table.setRowCount(len(filtered_days))
        
        for i, day in enumerate(filtered_days):
            # Day number
            day_item = QTableWidgetItem(str(day.get("day", i+1)))
            self.plan_table.setItem(i, 0, day_item)
            
            # Date
            date_item = QTableWidgetItem(day.get("date", ""))
            self.plan_table.setItem(i, 1, date_item)
            
            # Focus
            focus_item = QTableWidgetItem(day.get("focus", ""))
            self.plan_table.setItem(i, 2, focus_item)
            
            # Activities
            activities = day.get("activities", [])
            activities_text = "\n".join(f"• {activity}" for activity in activities)
            activities_item = QTableWidgetItem(activities_text)
            self.plan_table.setItem(i, 3, activities_item)
    
    def generate_content_strategy(self, insights):
        """Generate content strategy based on insights"""
        if not insights or "overall" not in insights:
            return "Insufficient data to generate content strategy."
        
        strategy_text = "# Content Strategy Recommendations\n\n"
        
        # Add overall strategy based on health score
        health_score = 0
        if "trends" in insights and "total" in insights["trends"]:
            health_trend = insights["trends"]["total"].get("community_health_score", {})
            health_score = health_trend.get("value", 0)
        elif "health_report" in insights:
            health_score = insights["health_report"].get("overall_score", 0)
        
        if health_score > 75:
            strategy_text += "## Overall Strategy: Growth & Expansion\n\n"
            strategy_text += "Your community is thriving, making this an ideal time to focus on growth strategies and "
            strategy_text += "expanding your influence. Consider these content themes:\n\n"
            
            strategy_text += "1. Thought leadership content to establish your authority\n"
            strategy_text += "2. Community spotlight features to showcase member contributions\n"
            strategy_text += "3. Exclusive content that provides additional value to members\n"
            strategy_text += "4. Collaborative content with other influencers in your space\n\n"
        
        elif health_score > 50:
            strategy_text += "## Overall Strategy: Engagement & Strengthening\n\n"
            strategy_text += "Your community is healthy, but could benefit from increased engagement. Focus on content that:\n\n"
            
            strategy_text += "1. Encourages discussion and participation\n"
            strategy_text += "2. Educates your audience on topics they care about\n"
            strategy_text += "3. Addresses common questions and challenges\n"
            strategy_text += "4. Creates opportunities for members to connect with each other\n\n"
        
        else:
            strategy_text += "## Overall Strategy: Rebuilding & Reengagement\n\n"
            strategy_text += "Your community needs attention and revitalization. Prioritize content that:\n\n"
            
            strategy_text += "1. Addresses pain points and concerns directly\n"
            strategy_text += "2. Demonstrates your commitment to the community\n"
            strategy_text += "3. Provides immediate value through helpful resources\n"
            strategy_text += "4. Creates opportunities for feedback and improvement\n\n"
        
        # Add platform-specific content recommendations
        strategy_text += "## Platform-Specific Content\n\n"
        
        if "platforms" in insights:
            for platform_id, platform_insight in insights["platforms"].items():
                platform_name = platform_id.capitalize()
                strategy_text += f"### {platform_name}\n\n"
                
                if "recommendations" in platform_insight and platform_insight["recommendations"]:
                    strategy_text += "Content recommendations:\n"
                    for rec in platform_insight["recommendations"]:
                        strategy_text += f"- {rec}\n"
                    strategy_text += "\n"
                else:
                    strategy_text += "No specific recommendations available for this platform.\n\n"
        
        # Add content mix recommendations
        strategy_text += "## Recommended Content Mix\n\n"
        strategy_text += "- 40% Educational content\n"
        strategy_text += "- 30% Engagement content (questions, polls, discussions)\n"
        strategy_text += "- 20% Promotional content (your products/services)\n"
        strategy_text += "- 10% Personal/behind-the-scenes content\n\n"
        
        strategy_text += "## Posting Frequency\n\n"
        strategy_text += "- Twitter: 3-5 times per day\n"
        strategy_text += "- Facebook: 1-2 times per day\n"
        strategy_text += "- Instagram: 1-2 times per day\n"
        strategy_text += "- LinkedIn: 1 time per day\n"
        strategy_text += "- Reddit: 2-3 times per week in relevant subreddits\n"
        
        return strategy_text
    
    def add_activity_log(self, message):
        """Add a message to the activity log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.activity_log.append(log_entry)

# For testing the widget standalone
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Create a sample dashboard for testing
    from core.social.UnifiedCommunityDashboard import UnifiedCommunityDashboard
    
    dashboard = UnifiedCommunityDashboard()
    
    # Create test config for manager
    from core.social.community_integration import CommunityIntegrationManager
    manager = CommunityIntegrationManager(config)
    manager.dashboard = dashboard
    
    # Create widget
    widget = CommunityDashboardTab(community_manager=manager)
    widget.setMinimumSize(900, 600)
    widget.show()
    
    sys.exit(app.exec_()) 