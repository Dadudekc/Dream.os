#!/usr/bin/env python3
"""
Voice I/O Service

Provides speech-to-text and text-to-speech capabilities for Dream.OS voice mode.
Handles audio input/output, voice recognition, and text-to-speech synthesis.
"""

import logging
import queue
import threading
from pathlib import Path
from typing import Optional, Dict, List, Callable

import speech_recognition as sr
import pyttsx3
from pydantic import BaseModel

logger = logging.getLogger('dream_os.voice')

class VoiceConfig(BaseModel):
    """Configuration for voice I/O settings."""
    rate: int = 170  # Words per minute
    volume: float = 1.0  # 0.0 to 1.0
    voice_id: Optional[str] = None  # System-specific voice identifier
    language: str = 'en-US'  # Recognition language
    timeout: int = 5  # Recognition timeout in seconds
    energy_threshold: int = 4000  # Microphone sensitivity
    pause_threshold: float = 0.8  # Seconds of silence to mark end of phrase

class VoiceEvent(BaseModel):
    """Voice event data model."""
    type: str  # 'start_listen', 'recognized', 'speaking', 'error'
    data: Dict  # Event-specific data
    timestamp: float  # Event timestamp

class VoiceIOService:
    """
    Handles voice input/output operations for Dream.OS.
    
    Features:
    - Real-time speech recognition
    - Text-to-speech synthesis
    - Event-based status updates
    - Background processing
    - Error recovery
    """
    
    def __init__(self, config: Optional[VoiceConfig] = None):
        """
        Initialize voice I/O service.
        
        Args:
            config: Optional voice configuration settings
        """
        self.config = config or VoiceConfig()
        self.recognizer = sr.Recognizer()
        self.engine = pyttsx3.init()
        
        # Configure TTS engine
        self.engine.setProperty('rate', self.config.rate)
        self.engine.setProperty('volume', self.config.volume)
        if self.config.voice_id:
            self.engine.setProperty('voice', self.config.voice_id)
        
        # Configure speech recognition
        self.recognizer.energy_threshold = self.config.energy_threshold
        self.recognizer.pause_threshold = self.config.pause_threshold
        
        # Event handling
        self.event_handlers: List[Callable[[VoiceEvent], None]] = []
        self.event_queue = queue.Queue()
        self._start_event_processor()
        
        # State tracking
        self.is_listening = False
        self.is_speaking = False
        self.last_error: Optional[str] = None
        
        logger.info("VoiceIOService initialized")
    
    def add_event_handler(self, handler: Callable[[VoiceEvent], None]):
        """Register an event handler."""
        self.event_handlers.append(handler)
    
    def listen(self, timeout: Optional[int] = None) -> Optional[str]:
        """
        Listen for voice input and convert to text.
        
        Args:
            timeout: Optional timeout in seconds (overrides config)
            
        Returns:
            Recognized text or None on error
        """
        if self.is_listening:
            logger.warning("Already listening")
            return None
        
        timeout = timeout or self.config.timeout
        self.is_listening = True
        self._emit_event('start_listen', {'timeout': timeout})
        
        try:
            with sr.Microphone() as source:
                logger.info("🎙 Listening...")
                self.recognizer.adjust_for_ambient_noise(source)
                audio = self.recognizer.listen(source, timeout=timeout)
                
                text = self.recognizer.recognize_google(
                    audio, 
                    language=self.config.language
                )
                
                self._emit_event('recognized', {'text': text})
                return text
                
        except sr.WaitTimeoutError:
            self._handle_error("Listening timeout")
        except sr.UnknownValueError:
            self._handle_error("Could not understand audio")
        except sr.RequestError as e:
            self._handle_error(f"Recognition service error: {str(e)}")
        except Exception as e:
            self._handle_error(f"Unexpected error: {str(e)}")
        finally:
            self.is_listening = False
        
        return None
    
    def speak(self, text: str) -> bool:
        """
        Convert text to speech.
        
        Args:
            text: Text to speak
            
        Returns:
            Whether speech completed successfully
        """
        if self.is_speaking:
            logger.warning("Already speaking")
            return False
        
        self.is_speaking = True
        self._emit_event('speaking', {'text': text})
        
        try:
            logger.info(f"🔈 Speaking: {text}")
            self.engine.say(text)
            self.engine.runAndWait()
            return True
            
        except Exception as e:
            self._handle_error(f"Speech error: {str(e)}")
            return False
            
        finally:
            self.is_speaking = False
    
    def get_available_voices(self) -> List[Dict]:
        """Get list of available system voices."""
        voices = []
        for voice in self.engine.getProperty('voices'):
            voices.append({
                'id': voice.id,
                'name': voice.name,
                'languages': voice.languages,
                'gender': voice.gender
            })
        return voices
    
    def update_config(self, config: VoiceConfig):
        """Update voice configuration."""
        self.config = config
        self.engine.setProperty('rate', config.rate)
        self.engine.setProperty('volume', config.volume)
        if config.voice_id:
            self.engine.setProperty('voice', config.voice_id)
        self.recognizer.energy_threshold = config.energy_threshold
        self.recognizer.pause_threshold = config.pause_threshold
    
    def _emit_event(self, event_type: str, data: Dict):
        """Emit a voice event."""
        from time import time
        event = VoiceEvent(
            type=event_type,
            data=data,
            timestamp=time()
        )
        self.event_queue.put(event)
    
    def _handle_error(self, error_msg: str):
        """Handle and log an error."""
        logger.error(error_msg)
        self.last_error = error_msg
        self._emit_event('error', {'message': error_msg})
    
    def _start_event_processor(self):
        """Start background event processing thread."""
        def process_events():
            while True:
                try:
                    event = self.event_queue.get()
                    for handler in self.event_handlers:
                        try:
                            handler(event)
                        except Exception as e:
                            logger.error(f"Event handler error: {str(e)}")
                except Exception as e:
                    logger.error(f"Event processing error: {str(e)}")
        
        thread = threading.Thread(
            target=process_events,
            daemon=True,
            name="VoiceEventProcessor"
        )
        thread.start()
    
    def __del__(self):
        """Cleanup resources."""
        try:
            self.engine.stop()
        except:
            pass 