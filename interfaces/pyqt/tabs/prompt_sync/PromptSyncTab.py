"""
Prompt Sync Tab

This tab orchestrates the full prompt lifecycle:
1. Ingest: Web scraping and content preparation
2. Prompt: Template rendering and configuration
3. Sync: Execution monitoring and streaming
4. Episode: Content management and dispatching
"""

import logging
from typing import Optional, Dict, Any
from pathlib import Path
import json
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QSplitter, QLabel,
    QStatusBar, QGroupBox
)
from PyQt5.QtCore import Qt, pyqtSignal

from .components.IngestPanel import IngestPanel
from .components.PromptPanel import PromptPanel
from .components.SyncPanel import SyncPanel
from .components.EpisodePanel import EpisodePanel

logger = logging.getLogger(__name__)

class PromptSyncTab(QWidget):
    """
    Main tab for the Prompt Sync Engine
    
    Features:
    - Full prompt lifecycle management
    - Real-time status updates
    - Service dependency injection
    - State persistence
    """
    
    def __init__(self, services: Dict[str, Any]):
        """Initialize the Prompt Sync Tab.
        
        Args:
            services: Dictionary containing required services:
                     - template_engine: For template rendering
                     - prompt_service: For prompt execution
                     - episode_service: For episode management
                     - export_service: For content export
                     - web_scraper: For web content ingestion
        """
        super().__init__()
        
        self.services = services
        self.logger = logger
        
        # Initialize UI
        self._init_ui()
        self._connect_signals()
        
        # Load any saved state
        self._load_state()
        
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Create main splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Left side: Phase tabs
        phase_tabs = QTabWidget()
        
        # Ingest panel
        self.ingest_panel = IngestPanel(self.services)
        phase_tabs.addTab(self.ingest_panel, "Ingest")
        
        # Prompt panel
        self.prompt_panel = PromptPanel(self.services)
        phase_tabs.addTab(self.prompt_panel, "Prompt")
        
        # Sync panel
        self.sync_panel = SyncPanel(self.services)
        phase_tabs.addTab(self.sync_panel, "Sync")
        
        # Episode panel
        self.episode_panel = EpisodePanel(self.services)
        phase_tabs.addTab(self.episode_panel, "Episode")
        
        # Add phase tabs to splitter
        splitter.addWidget(phase_tabs)
        
        # Right side: Control deck
        control_deck = self._create_control_deck()
        splitter.addWidget(control_deck)
        
        # Set splitter sizes (80% left, 20% right)
        splitter.setSizes([800, 200])
        
        # Add splitter to layout
        layout.addWidget(splitter)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.status_bar.showMessage("Ready")
        layout.addWidget(self.status_bar)
        
    def _create_control_deck(self) -> QWidget:
        """Create the control deck widget."""
        control_deck = QWidget()
        layout = QVBoxLayout(control_deck)
        
        # Service status
        status_group = QGroupBox("Service Status")
        status_layout = QVBoxLayout()
        
        self.service_status = {}
        required_services = [
            'template_engine',
            'prompt_service',
            'episode_service',
            'export_service',
            'web_scraper'
        ]
        
        for service in required_services:
            status_label = QLabel()
            self._update_service_status(service, status_label)
            status_layout.addWidget(status_label)
            self.service_status[service] = status_label
            
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Current template info
        template_group = QGroupBox("Current Template")
        template_layout = QVBoxLayout()
        
        self.template_info = QLabel("No template selected")
        self.template_info.setWordWrap(True)
        template_layout.addWidget(self.template_info)
        
        template_group.setLayout(template_layout)
        layout.addWidget(template_group)
        
        # Prompt metrics
        metrics_group = QGroupBox("Prompt Metrics")
        metrics_layout = QVBoxLayout()
        
        self.prompt_metrics = QLabel("No metrics available")
        metrics_layout.addWidget(self.prompt_metrics)
        
        metrics_group.setLayout(metrics_layout)
        layout.addWidget(metrics_group)
        
        # Add stretch to push everything up
        layout.addStretch()
        
        return control_deck
        
    def _connect_signals(self):
        """Connect component signals."""
        # Ingest panel signals
        self.ingest_panel.content_ready.connect(self._handle_content_ready)
        self.ingest_panel.status_update.connect(self._update_status)
        
        # Prompt panel signals
        self.prompt_panel.prompt_ready.connect(self._handle_prompt_ready)
        self.prompt_panel.status_update.connect(self._update_status)
        
        # Sync panel signals
        self.sync_panel.response_ready.connect(self._handle_response_ready)
        self.sync_panel.status_update.connect(self._update_status)
        
        # Episode panel signals
        self.episode_panel.episode_saved.connect(self._handle_episode_saved)
        self.episode_panel.status_update.connect(self._update_status)
        
    def _update_service_status(self, service: str, label: QLabel):
        """Update the status display for a service."""
        if service in self.services:
            service_obj = self.services[service]
            
            # Check if it's a mock service
            if hasattr(service_obj, 'name') and service_obj.name == service:
                label.setText(f"{service}: Mock Implementation")
                label.setStyleSheet("color: orange")
            else:
                try:
                    # Try to get service status if available
                    if hasattr(service_obj, 'get_status'):
                        status = service_obj.get_status()
                        label.setText(f"{service}: {status}")
                    else:
                        label.setText(f"{service}: Available")
                    label.setStyleSheet("color: green")
                except Exception as e:
                    label.setText(f"{service}: Error - {str(e)}")
                    label.setStyleSheet("color: red")
        else:
            label.setText(f"{service}: Not Available")
            label.setStyleSheet("color: gray")
            
    def _update_status(self, message: str):
        """Update the status bar message."""
        self.status_bar.showMessage(message)
        
    def _handle_content_ready(self, content: Dict[str, Any]):
        """Handle content ready from ingest panel."""
        # Switch to prompt tab
        self.parent().setCurrentIndex(1)
        
        # Update prompt panel
        self.prompt_panel.set_content(content)
        
        # Update control deck
        if 'url' in content:
            self._update_status(f"Content ingested from {content['url']}")
            
    def _handle_prompt_ready(self, prompt: str):
        """Handle prompt ready from prompt panel."""
        # Switch to sync tab
        self.parent().setCurrentIndex(2)
        
        # Get model key from prompt panel
        model_key = self.prompt_panel._resolve_model_key(
            self.prompt_panel.model_combo.currentText()
        )
        
        # Update sync panel
        self.sync_panel.set_prompt(prompt, model_key)
        
        # Update control deck
        self._update_metrics({
            'template': self.prompt_panel.template_combo.currentText(),
            'model': model_key,
            'tokens': len(prompt.split())
        })
        
    def _handle_response_ready(self, response: Dict[str, Any]):
        """Handle response ready from sync panel."""
        # Switch to episode tab
        self.parent().setCurrentIndex(3)
        
        # Update episode panel
        self.episode_panel.set_content(
            response['content'],
            {
                'title': f"Generated content {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                'category': "Generated",
                'tags': ["ai-generated"],
                'description': "Content generated using prompt sync engine"
            }
        )
        
        # Update control deck
        self._update_metrics({
            'response_tokens': len(response['content'].split()),
            'total_cost': response.get('cost', 0)
        })
        
    def _handle_episode_saved(self, episode: Dict[str, Any]):
        """Handle episode saved from episode panel."""
        # Update control deck
        self._update_status(f"Episode saved: {episode['metadata']['title']}")
        
    def _update_metrics(self, metrics: Dict[str, Any]):
        """Update the metrics display in control deck."""
        lines = []
        
        if 'template' in metrics:
            lines.append(f"Template: {metrics['template']}")
            
        if 'model' in metrics:
            lines.append(f"Model: {metrics['model']}")
            
        if 'tokens' in metrics:
            lines.append(f"Prompt Tokens: {metrics['tokens']}")
            
        if 'response_tokens' in metrics:
            lines.append(f"Response Tokens: {metrics['response_tokens']}")
            
        if 'total_cost' in metrics:
            lines.append(f"Total Cost: ${metrics['total_cost']:.4f}")
            
        self.prompt_metrics.setText("\n".join(lines))
        
    def _save_state(self):
        """Save the current state of all panels."""
        try:
            state = {
                'ingest': self.ingest_panel.get_state(),
                'prompt': self.prompt_panel.get_state(),
                'sync': self.sync_panel.get_state(),
                'episode': self.episode_panel.get_state()
            }
            
            state_path = Path("state/prompt_sync_state.json")
            state_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(state_path, 'w') as f:
                json.dump(state, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error saving state: {str(e)}")
            
    def _load_state(self):
        """Load the saved state of all panels."""
        try:
            state_path = Path("state/prompt_sync_state.json")
            if state_path.exists():
                with open(state_path) as f:
                    state = json.load(f)
                    
                # Restore panel states
                if 'ingest' in state:
                    self.ingest_panel.restore_state(state['ingest'])
                    
                if 'prompt' in state:
                    self.prompt_panel.restore_state(state['prompt'])
                    
                if 'sync' in state:
                    self.sync_panel.restore_state(state['sync'])
                    
                if 'episode' in state:
                    self.episode_panel.restore_state(state['episode'])
                    
        except Exception as e:
            self.logger.error(f"Error loading state: {str(e)}")
            
    def closeEvent(self, event):
        """Handle tab close event."""
        # Save state before closing
        self._save_state()
        super().closeEvent(event) 