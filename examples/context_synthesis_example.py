#!/usr/bin/env python3
"""
PromptContextSynthesizer Usage Example

This example demonstrates how to use the PromptContextSynthesizer
to combine multiple context sources for generating Dreamscape episodes.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("context_synthesis_example")

# Import PromptContextSynthesizer
from core.services.prompt_context_synthesizer import PromptContextSynthesizer

def load_config() -> Dict[str, Any]:
    """Load context synthesis configuration."""
    config_path = Path("config/context_synthesis.json")
    if not config_path.exists():
        logger.warning(f"Configuration file not found: {config_path}")
        return {}
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        logger.info(f"Loaded configuration from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return {}

def simulate_web_scraping() -> str:
    """Simulate web-scraped content from a chat interface."""
    return """
# ChatGPT - Memory Management Discussion

## User
I've been thinking about implementing a more efficient memory system for my conversational agent. What approach would you recommend?

## Assistant
For efficient memory management in conversational agents, consider a hybrid approach:

1. **Short-term working memory**: Recent interactions (last 10-20 exchanges)
2. **Episodic memory**: Important conversation milestones stored as summaries
3. **Semantic memory**: Extracted knowledge, facts, and user preferences
4. **Procedural memory**: Learned patterns for handling specific conversation flows

Implement using a tiered storage system:
- In-memory cache for active conversation
- Document store (like MongoDB) for episodic and semantic memory
- Vector embeddings for similarity search

Most importantly, include a forgetting mechanism - not everything needs to be remembered forever.

## User
That makes sense. How would you handle updating the semantic memory over time?

## Summary
Discussion about implementing efficient memory systems for conversational agents, covering short-term, episodic, semantic, and procedural memory approaches with recommendations for storage and selective forgetting mechanisms.
"""

def simulate_chat_history() -> list:
    """Simulate a chat history from memory."""
    return [
        "User: I need to integrate this memory system into my existing architecture.",
        "Assistant: For integration, you'll want to create abstraction layers that separate the memory implementation from the rest of your system. This allows you to swap out different memory strategies without changing your core logic.",
        "User: What about handling conflicts between different memory sources?",
        "Assistant: That's an excellent question. When different memory sources conflict, implement a confidence-based resolution system. Each memory retrieval should include a confidence score. When conflicts occur, prefer the memory with higher confidence. For equally confident memories, either use recency as a tiebreaker or present both options to a higher-level reasoning module."
    ]

def main():
    """Main function demonstrating context synthesis."""
    logger.info("Starting context synthesis example")
    
    # Load configuration
    config = load_config()
    
    # Create the context synthesizer
    synthesizer = PromptContextSynthesizer(logger=logger)
    
    # Example 1: Using web-scraped content
    logger.info("Example 1: Synthesis with web-scraped content")
    web_context = synthesizer.synthesize_context(
        chat_title="Memory Management Discussion",
        web_scraped_content=simulate_web_scraping(),
        config=config
    )
    
    print("\n=== Web-Scraped Content Synthesis ===")
    print(f"Context sources: {web_context['context_quality']['sources_used']}")
    print(f"Overall confidence: {web_context['context_quality']['overall_confidence']:.2f}")
    print(f"Semantic summary: {web_context['semantic_summary']}")
    
    # Example 2: Using chat history from memory
    logger.info("Example 2: Synthesis with chat history")
    memory_context = synthesizer.synthesize_context(
        chat_title="Architecture Integration Chat",
        chat_history=simulate_chat_history(),
        config=config
    )
    
    print("\n=== Chat History Synthesis ===")
    print(f"Context sources: {memory_context['context_quality']['sources_used']}")
    print(f"Overall confidence: {memory_context['context_quality']['overall_confidence']:.2f}")
    print(f"Semantic summary: {memory_context['semantic_summary']}")
    
    # Example 3: Hybrid approach with custom weights
    logger.info("Example 3: Hybrid synthesis with custom weights")
    custom_config = config.copy()
    custom_config["context_weights"] = {
        "web_scraping": 0.5,
        "episode_chain": 0.3,
        "semantic_memory": 0.2
    }
    
    hybrid_context = synthesizer.synthesize_context(
        chat_title="Memory Architecture Discussion",
        web_scraped_content=simulate_web_scraping(),
        chat_history=simulate_chat_history(),
        config=custom_config,
        additional_context={
            "user_preference": "Technical, detailed explanations",
            "conversation_goal": "System architecture design",
            "semantic_themes": ["memory management", "system integration", "architecture design"]
        }
    )
    
    print("\n=== Hybrid Synthesis with Custom Weights ===")
    print(f"Context sources: {hybrid_context['context_quality']['sources_used']}")
    print(f"Source contributions: {json.dumps(hybrid_context['context_quality']['contributions'], indent=2)}")
    print(f"Overall confidence: {hybrid_context['context_quality']['overall_confidence']:.2f}")
    print(f"Semantic summary: {hybrid_context['semantic_summary']}")
    
    # Example 4: Leveraging episode chain context (if available)
    print("\n=== Episode Chain Integration ===")
    if hybrid_context.get("has_previous_episode"):
        print(f"Last episode: {hybrid_context.get('last_episode', 'Unknown')}")
        print(f"Ongoing quests: {hybrid_context.get('ongoing_quests', [])}")
        print(f"Current location: {hybrid_context.get('last_location', 'Unknown')}")
    else:
        print("No previous episode data available")
    
    logger.info("Context synthesis example completed")

if __name__ == "__main__":
    main() 
