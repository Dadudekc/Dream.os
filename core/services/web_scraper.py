"""
WebScraper for Dream.OS

This scraper is designed to collect data from web pages,
clean it, and structure it into ChatGPT-ready prompts using
Jinja2 templates. It directly interfaces with PromptService,
serving as a bridge between external data and Dream.OS prompt cycles.

This is NOT a standalone scraper — it is part of a full feedback loop:
[User/Agent] -> WebScraper -> TemplateEngine -> PromptService -> ChatGPT -> Action/Memory

Flow:
1. Receive URL or content request
2. Fetch and clean HTML content
3. Extract relevant data using BeautifulSoup
4. Structure data through Jinja2 templates
5. Generate ChatGPT-ready prompts
6. Feed to PromptService for execution
"""

import os
import sys
import logging
import requests
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup
from pathlib import Path

logger = logging.getLogger(__name__)

class WebScraper:
    """
    Intelligent web scraping agent that transforms web content into ChatGPT prompts.
    
    This class is a core part of the Dream.OS prompt pipeline, responsible for:
    - Fetching and cleaning web content
    - Structuring data through templates
    - Generating context-aware prompts for ChatGPT
    - Maintaining scraping history and context
    
    Dependencies:
        - TemplateEngine: For rendering prompts from templates
        - PromptService: For executing generated prompts
    """
    
    def __init__(self, template_engine=None, prompt_service=None):
        """
        Initialize the WebScraper with required services.
        
        Args:
            template_engine: TemplateEngine instance for prompt rendering
            prompt_service: PromptService for executing prompts
        """
        self.template_engine = template_engine
        self.prompt_service = prompt_service
        self.logger = logger
        
        # Ensure required packages
        self._check_dependencies()
        
    def _check_dependencies(self):
        """Verify and install required packages."""
        try:
            import requests
            import bs4
        except ImportError:
            self.logger.warning("Installing required packages...")
            import pip
            pip.main(['install', 'requests', 'beautifulsoup4'])
            
    async def scrape_and_prompt(self, url: str, template_name: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Scrape a URL and generate a ChatGPT prompt using the specified template.
        
        Args:
            url: The URL to scrape
            template_name: Name of the Jinja2 template to use
            context: Additional context for prompt generation
            
        Returns:
            Generated prompt ready for ChatGPT
        """
        try:
            # Fetch and parse content
            html_content = await self._fetch_url(url)
            parsed_text = self._parse_html(html_content)
            
            # Prepare template context
            template_context = {
                'url': url,
                'content': parsed_text,
                'metadata': self._extract_metadata(html_content)
            }
            
            if context:
                template_context.update(context)
            
            # Generate prompt using template
            if self.template_engine:
                prompt = self.template_engine.render_from_template(
                    template_name,
                    template_context
                )
            else:
                self.logger.warning("TemplateEngine not available, using basic prompt")
                prompt = self._generate_basic_prompt(template_context)
                
            return prompt
            
        except Exception as e:
            self.logger.error(f"Error in scrape_and_prompt: {str(e)}")
            raise
            
    async def _fetch_url(self, url: str) -> str:
        """Fetch HTML content from URL with proper error handling."""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except Exception as e:
            self.logger.error(f"Error fetching URL {url}: {str(e)}")
            raise
            
    def _parse_html(self, html: str) -> str:
        """Parse and clean HTML content using BeautifulSoup."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'iframe', 'nav']):
                element.decompose()
                
            # Get clean text
            text = soup.get_text(separator='\n')
            
            # Clean up whitespace
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            return '\n'.join(lines)
            
        except Exception as e:
            self.logger.error(f"Error parsing HTML: {str(e)}")
            raise
            
    def _extract_metadata(self, html: str) -> Dict[str, str]:
        """Extract metadata from HTML content."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            return {
                'title': soup.title.string if soup.title else '',
                'description': soup.find('meta', {'name': 'description'})['content'] if soup.find('meta', {'name': 'description'}) else '',
                'keywords': soup.find('meta', {'name': 'keywords'})['content'] if soup.find('meta', {'name': 'keywords'}) else ''
            }
        except Exception as e:
            self.logger.warning(f"Error extracting metadata: {str(e)}")
            return {}
            
    def _generate_basic_prompt(self, context: Dict[str, Any]) -> str:
        """Generate a basic prompt when TemplateEngine is unavailable."""
        return f"""
        Analyze and summarize the following web content:
        
        URL: {context.get('url')}
        Title: {context.get('metadata', {}).get('title', 'Unknown')}
        
        Content:
        {context.get('content')}
        
        Please provide a comprehensive analysis and summary.
        """
        
    def get_status(self) -> Dict[str, bool]:
        """Get the status of the scraper and its dependencies."""
        return {
            'requests_available': 'requests' in sys.modules,
            'bs4_available': 'bs4' in sys.modules,
            'template_engine_available': self.template_engine is not None,
            'prompt_service_available': self.prompt_service is not None
        } 