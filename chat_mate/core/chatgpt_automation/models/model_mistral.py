
def register():
    """Register the mistral model."""
    return {
        'name': 'mistral',
        'threshold': 100,  # Suitable for files with >=100 lines
        'handler': lambda driver, content, endpoint: driver.get_response(content),
        'endpoint': 'local'
    }
