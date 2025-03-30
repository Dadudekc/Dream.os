"""
Mock dependencies for MeredithTab tests.

This module provides mock implementations of the dependencies required by MeredithTab.
"""

import os
import sys

# Add mocks to Python path
sys.modules['core.meredith.profile_scraper'] = type('mock_module', (), {
    'ScraperManager': type('ScraperManager', (), {
        '__init__': lambda self, headless=True: None,
        'register_default_scrapers': lambda self: None,
        'run_all': lambda self: [],
        'close': lambda self: None
    }),
    'ProfileFilter': type('ProfileFilter', (), {
        'filter_by_location': staticmethod(lambda profiles, cities, zipcode: profiles),
        'filter_by_gender': staticmethod(lambda profiles, gender: profiles)
    })
})

sys.modules['core.meredith.resonance_scorer'] = type('mock_module', (), {
    'ResonanceScorer': type('ResonanceScorer', (), {
        '__init__': lambda self, model_path=None: None,
        'load_model': lambda self, model_path: None,
        'score': lambda self, profile: 85
    })
})

sys.modules['core.PathManager'] = type('mock_module', (), {
    'PathManager': type('PathManager', (), {
        '__init__': lambda self: None,
        'get_path': lambda self, key: os.path.join(os.getcwd(), 'mock_data', key)
    })
})

sys.modules['core.meredith.meredith_dispatcher'] = type('mock_module', (), {
    'MeredithDispatcher': type('MeredithDispatcher', (), {
        '__init__': lambda self: None,
        'process_profile': lambda self, profile: {
            'resonance_score': 91,
            'should_save_to_meritchain': True
        }
    })
})

# Mock rendering module
sys.modules['core.rendering'] = type('mock_module', (), {})
sys.modules['core.rendering.template_engine'] = type('mock_module', (), {
    'TemplateEngine': type('TemplateEngine', (), {
        '__init__': lambda self: None,
        'render_template': lambda self, template_name, context: "Rendered template"
    })
})

# Mock additional modules that might be imported
sys.modules['core.services'] = type('mock_module', (), {})
sys.modules['core.services.discord'] = type('mock_module', (), {})
sys.modules['core.services.discord.DiscordManager'] = type('mock_module', (), {
    'DiscordManager': type('DiscordManager', (), {
        '__init__': lambda self: None,
        'send_message': lambda self, channel, message: None
    })
})

sys.modules['core.services.prompt_execution_service'] = type('mock_module', (), {
    'PromptExecutionService': type('PromptExecutionService', (), {
        '__init__': lambda self: None,
        'execute': lambda self, prompt, model="gpt-4": "Response"
    })
})

# Create necessary mock directories
os.makedirs(os.path.join(os.getcwd(), 'mock_data', 'resonance_models'), exist_ok=True)

# Create a mock model file
model_path = os.path.join(os.getcwd(), 'mock_data', 'resonance_models', 'romantic.json')
with open(model_path, 'w') as f:
    f.write('{"name": "romantic", "weights": {"appearance": 0.3, "personality": 0.7}}') 