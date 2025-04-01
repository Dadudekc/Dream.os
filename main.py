"""
Chat Mate - Main Entry Point

This module serves as the main entry point for the Chat Mate application,
initializing the agent system and handling the main interaction loop.
"""

import logging
import sys
from typing import Optional
import yaml

from core.factories import FactoryRegistry
from core.services.service_registry import registry
from core.agents import AgentState

def setup_logging() -> logging.Logger:
    """Set up logging configuration."""
    logger = logging.getLogger("chat_mate")
    logger.setLevel(logging.INFO)
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    logger.addHandler(handler)
    
    return logger

def load_config(config_path: str = "config/config.yaml") -> dict:
    """Load configuration from YAML file."""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        raise RuntimeError(f"Failed to load config: {e}")

def initialize_system(logger: logging.Logger, config: dict) -> None:
    """Initialize core system components."""
    # Register core services
    registry.register("logger", instance=logger)
    registry.register("config", instance=config)
    
    # Initialize factories
    factory_registry = FactoryRegistry()
    registry.register("factory_registry", instance=factory_registry)

def main(config_path: str = "config/config.yaml") -> None:
    """Main entry point for the application."""
    try:
        # Setup logging and load config
        logger = setup_logging()
        config = load_config(config_path)
        
        # Initialize system
        initialize_system(logger, config)
        
        # Create agent factory
        factory = FactoryRegistry.get("agent")
        if not factory:
            raise RuntimeError("Failed to get agent factory")
        
        # Create and initialize chat agent
        agent = factory.create("chat")
        if not agent:
            raise RuntimeError("Failed to create chat agent")
        
        # Initialize agent
        agent.initialize()
        if agent.state != AgentState.READY:
            raise RuntimeError("Agent failed to initialize")
        
        logger.info("Chat Mate initialized successfully! Type 'exit' to quit.")
        
        # Main interaction loop
        while True:
            try:
                user_input = input("\nYou: ").strip()
                if user_input.lower() in ['exit', 'quit']:
                    break
                
                response = agent.execute({"message": user_input})
                if response:
                    print(f"\nVictor: {response}")
                else:
                    logger.error("Failed to get response from agent")
            
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error during interaction: {e}")
        
        # Cleanup
        agent.cleanup()
        logger.info("Chat Mate terminated successfully!")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
