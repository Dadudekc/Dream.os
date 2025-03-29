import pytest
from pathlib import Path
import json
from social.data.post_history import PostHistory

def test_load_post_history_file_exists(tmp_path):
    """Test loading post history when file exists."""
    # Create a temporary post history file
    history_file = tmp_path / "post_history.json"
    test_data = [
        {
            "id": "1",
            "content": "Test post 1",
            "timestamp": "2024-03-21T15:30:30"
        },
        {
            "id": "2",
            "content": "Test post 2",
            "timestamp": "2024-03-21T15:31:30"
        }
    ]
    
    with open(history_file, 'w') as f:
        json.dump(test_data, f)
    
    # Initialize PostHistory with the temporary file
    post_history = PostHistory(str(history_file))
    
    # Verify that the history was loaded correctly
    assert len(post_history.history) == 2
    assert post_history.history[0]["content"] == "Test post 1"
    assert post_history.history[1]["content"] == "Test post 2"

