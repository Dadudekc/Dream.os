from flask import Flask, render_template, jsonify
import logging
from pathlib import Path

def create_app(services=None):
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Store services
    app.services = services or {}
    
    # Ensure templates directory exists
    templates_dir = Path(__file__).parent / 'templates'
    if not templates_dir.exists():
        templates_dir.mkdir(parents=True)
    
    # Basic route
    @app.route('/')
    def index():
        return render_template('index.html')
    
    # API endpoints
    @app.route('/api/status')
    def status():
        return jsonify({
            'status': 'running',
            'services': {
                'config': bool(app.services.get('config')),
                'logger': bool(app.services.get('logger')),
                'driver': bool(app.services.get('driver_manager'))
            }
        })
    
    return app

def start_flask_app(services=None, host='127.0.0.1', port=5000):
    """Start the Flask application"""
    app = create_app(services)
    logging.info(f"Starting Flask web server on {host}:{port}")
    app.run(host=host, port=port, debug=True) 