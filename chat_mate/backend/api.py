import json
import logging
from flask import Flask, request, jsonify
from backend.template_loader import load_template, allowed_templates

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Initialize Flask app
app = Flask(__name__)

@app.route('/api/templates/load', methods=['GET'])
def api_load_template():
    """
    Endpoint to load and render a template with context.
    
    Query parameters:
        name: Name of the template file
        context: JSON string of context data for rendering
    
    Returns:
        Rendered template content or error message
    """
    template_name = request.args.get('name')
    context_param = request.args.get('context', '{}')
    
    if not template_name:
        return jsonify({"error": "No template name provided"}), 400
    
    # Validate template name
    if template_name not in allowed_templates:
        logger.warning(f"Unauthorized template request: {template_name}")
        return jsonify({"error": f"Template '{template_name}' not allowed"}), 403
    
    try:
        # Parse context JSON
        context = json.loads(context_param)
        
        # Load and render template
        template_content = load_template(template_name, context)
        
        if template_content is None:
            return jsonify({"error": f"Failed to render template: {template_name}"}), 500
            
        # Return rendered template
        return template_content, 200, {'Content-Type': 'text/html'}
        
    except json.JSONDecodeError:
        logger.error(f"Invalid context JSON: {context_param}")
        return jsonify({"error": "Invalid context format"}), 400
    except Exception as e:
        logger.error(f"Error processing template request: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/templates/list', methods=['GET'])
def api_list_templates():
    """
    Endpoint to list all available templates.
    
    Returns:
        JSON array of template names
    """
    return jsonify(allowed_templates)

# Main entry point for running the API server
if __name__ == '__main__':
    app.run(debug=True, port=5000) 