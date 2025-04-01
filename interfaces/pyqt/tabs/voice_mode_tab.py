#!/usr/bin/env python3
"""
Voice Mode Tab

PyQt5 interface for voice-based interaction with Dream.OS.
Provides real-time speech input/output and visual feedback.
"""

import logging
from typing import Optional, Dict
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QSpinBox, QDoubleSpinBox,
    QProgressBar, QFrame, QScrollArea, QTextEdit
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QIcon, QFont

from core.voice.voice_io_service import VoiceIOService, VoiceConfig, VoiceEvent
from core.chat.chat_manager import ChatManager

logger = logging.getLogger('dream_os.voice_tab')

class VoiceStatusWidget(QFrame):
    """Widget displaying voice I/O status and events."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout()
        
        # Status indicators
        status_layout = QHBoxLayout()
        self.listen_indicator = QLabel("🎙")
        self.speak_indicator = QLabel("🔈")
        status_layout.addWidget(self.listen_indicator)
        status_layout.addWidget(self.speak_indicator)
        layout.addLayout(status_layout)
        
        # Event log
        self.event_log = QTextEdit()
        self.event_log.setReadOnly(True)
        self.event_log.setMaximumHeight(100)
        layout.addWidget(self.event_log)
        
        self.setLayout(layout)
    
    def update_status(self, is_listening: bool, is_speaking: bool):
        """Update status indicators."""
        self.listen_indicator.setEnabled(is_listening)
        self.speak_indicator.setEnabled(is_speaking)
    
    def log_event(self, event: VoiceEvent):
        """Add event to log."""
        self.event_log.append(
            f"[{event.type}] {event.data.get('text', event.data.get('message', ''))}"
        )

class VoiceConfigWidget(QFrame):
    """Widget for configuring voice I/O settings."""
    
    config_changed = pyqtSignal(VoiceConfig)
    
    def __init__(self, voice_service: VoiceIOService, parent=None):
        super().__init__(parent)
        self.voice_service = voice_service
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout()
        
        # Voice selection
        voice_layout = QHBoxLayout()
        voice_layout.addWidget(QLabel("Voice:"))
        self.voice_combo = QComboBox()
        self._populate_voices()
        voice_layout.addWidget(self.voice_combo)
        layout.addLayout(voice_layout)
        
        # Rate control
        rate_layout = QHBoxLayout()
        rate_layout.addWidget(QLabel("Rate:"))
        self.rate_spin = QSpinBox()
        self.rate_spin.setRange(50, 300)
        self.rate_spin.setValue(170)
        rate_layout.addWidget(self.rate_spin)
        layout.addLayout(rate_layout)
        
        # Volume control
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(QLabel("Volume:"))
        self.volume_spin = QDoubleSpinBox()
        self.volume_spin.setRange(0.0, 1.0)
        self.volume_spin.setSingleStep(0.1)
        self.volume_spin.setValue(1.0)
        volume_layout.addWidget(self.volume_spin)
        layout.addLayout(volume_layout)
        
        # Apply button
        self.apply_btn = QPushButton("Apply Settings")
        self.apply_btn.clicked.connect(self._apply_config)
        layout.addWidget(self.apply_btn)
        
        self.setLayout(layout)
    
    def _populate_voices(self):
        """Populate voice selection combo box."""
        voices = self.voice_service.get_available_voices()
        for voice in voices:
            self.voice_combo.addItem(voice['name'], voice['id'])
    
    def _apply_config(self):
        """Apply voice configuration changes."""
        config = VoiceConfig(
            rate=self.rate_spin.value(),
            volume=self.volume_spin.value(),
            voice_id=self.voice_combo.currentData()
        )
        self.config_changed.emit(config)

class VoiceModeTab(QWidget):
    """
    Tab interface for voice-based interaction with Dream.OS.
    
    Features:
    - Voice input/output controls
    - Real-time status display
    - Voice configuration
    - Chat history view
    """
    
    def __init__(self, chat_manager: ChatManager, parent=None):
        super().__init__(parent)
        self.chat_manager = chat_manager
        self.voice = VoiceIOService()
        self.voice.add_event_handler(self._handle_voice_event)
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI layout."""
        layout = QVBoxLayout()
        
        # Status widget
        self.status_widget = VoiceStatusWidget()
        layout.addWidget(self.status_widget)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.listen_btn = QPushButton("🎙 Listen")
        self.listen_btn.setCheckable(True)
        self.listen_btn.clicked.connect(self._toggle_listening)
        button_layout.addWidget(self.listen_btn)
        
        self.speak_btn = QPushButton("🔈 Speak Last Reply")
        self.speak_btn.clicked.connect(self._speak_last_reply)
        button_layout.addWidget(self.speak_btn)
        
        layout.addLayout(button_layout)
        
        # Chat display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        layout.addWidget(self.chat_display)
        
        # Configuration
        self.config_widget = VoiceConfigWidget(self.voice)
        self.config_widget.config_changed.connect(self._update_voice_config)
        layout.addWidget(self.config_widget)
        
        self.setLayout(layout)
        
        # Initialize state
        self.last_reply: Optional[str] = None
        self._listening_timer = QTimer()
        self._listening_timer.timeout.connect(self._stop_listening)
    
    def _toggle_listening(self, checked: bool):
        """Toggle voice input listening."""
        if checked:
            self._start_listening()
        else:
            self._stop_listening()
    
    def _start_listening(self):
        """Start listening for voice input."""
        self.listen_btn.setText("🔴 Stop")
        self._listening_timer.start(5000)  # 5 second timeout
        
        def listen_thread():
            text = self.voice.listen()
            if text:
                self._handle_voice_input(text)
            self.listen_btn.setChecked(False)
        
        from threading import Thread
        Thread(target=listen_thread, daemon=True).start()
    
    def _stop_listening(self):
        """Stop listening for voice input."""
        self.listen_btn.setText("🎙 Listen")
        self._listening_timer.stop()
        self.listen_btn.setChecked(False)
    
    def _handle_voice_input(self, text: str):
        """Process voice input and get AI response."""
        self.chat_display.append(f"You: {text}")
        
        # Get AI response
        reply = self.chat_manager.send_prompt(text)
        self.last_reply = reply
        self.chat_display.append(f"AI: {reply}")
        
        # Auto-speak reply
        self.voice.speak(reply)
    
    def _speak_last_reply(self):
        """Speak the last AI reply."""
        if self.last_reply:
            self.voice.speak(self.last_reply)
    
    def _handle_voice_event(self, event: VoiceEvent):
        """Handle voice service events."""
        self.status_widget.log_event(event)
        self.status_widget.update_status(
            self.voice.is_listening,
            self.voice.is_speaking
        )
    
    def _update_voice_config(self, config: VoiceConfig):
        """Update voice service configuration."""
        self.voice.update_config(config)
    
    def closeEvent(self, event):
        """Clean up resources when tab is closed."""
        try:
            self.voice.engine.stop()
        except:
            pass
        event.accept() 