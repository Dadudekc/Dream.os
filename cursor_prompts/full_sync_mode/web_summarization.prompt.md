# Web Summarization Prompt Template

## TASK
Scrape a web page and extract content into a ChatGPT-compatible prompt.
Use the WebScraper service which:
- Uses `requests` + `BeautifulSoup` to fetch and clean the page
- Renders the content via Jinja2 using TemplateEngine
- Sends the prompt to PromptService for ChatGPT interaction

## CONTEXT
WebScraper is an integrated Dream.OS agent, not a passive utility.
It transforms live data into real-time intelligence by:
1. Cleaning and structuring web content
2. Applying context-aware templates
3. Generating targeted prompts for ChatGPT
4. Feeding into the Dream.OS memory system

## EXPECTED OUTPUT
- A generated prompt (rendered string)
- ChatGPT response
- Optional downstream storage in memory or Discord

## TEMPLATE VARIABLES
```python
{
    "url": "URL of the scraped page",
    "content": "Cleaned and structured content",
    "metadata": {
        "title": "Page title",
        "description": "Meta description",
        "keywords": "Meta keywords"
    },
    "context": {
        "user_intent": "Why this content is being scraped",
        "target_format": "Desired output format",
        "additional_context": "Any other relevant information"
    }
}
```

## JINJA2 TEMPLATE
```jinja2
{# web_summary_prompt.jinja #}
Analyze and summarize the following web content from {{ url }}:

Title: {{ metadata.title }}
Description: {{ metadata.description }}
Keywords: {{ metadata.keywords }}

Content:
{{ content }}

{% if context.user_intent %}
User Intent: {{ context.user_intent }}
{% endif %}

{% if context.target_format %}
Output Format: {{ context.target_format }}
{% endif %}

Please provide:
1. A comprehensive summary
2. Key points and insights
3. Relevant context and connections
4. Actionable takeaways
```

## INTEGRATION POINTS
- **Input**: Web content via WebScraper
- **Processing**: Template rendering via TemplateEngine
- **Output**: Structured prompt via PromptService
- **Storage**: Results in Dream.OS memory system
- **Notifications**: Optional Discord updates

## USAGE EXAMPLE
```python
# Initialize services
web_scraper = WebScraper(template_engine, prompt_service)

# Scrape and generate prompt
prompt = await web_scraper.scrape_and_prompt(
    url="https://example.com",
    template_name="web_summary_prompt.jinja",
    context={
        "user_intent": "Research for Dreamscape episode",
        "target_format": "Detailed analysis"
    }
)

# Send to ChatGPT via PromptService
response = await prompt_service.send_prompt(prompt)

# Store in memory or send to Discord
await memory_service.store(response)
await discord_service.send_update(response)
```

## NOTES
- This prompt template is part of the Dream.OS agent network
- It supports the full feedback loop from data ingestion to action
- Templates can be customized for different content types
- All operations are async-aware and error-handled 