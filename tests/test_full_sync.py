import os
import json
import pytest
from core.TemplateManager import TemplateManager

@pytest.fixture
def template_manager():
    """Create a TemplateManager instance for testing."""
    return TemplateManager()

@pytest.fixture
def project_context():
    """Create a sample project context."""
    return {
        "name": "test_project",
        "files": {
            "core/memory/MemoryManager.py": {
                "classes": ["MemoryManager"],
                "methods": ["load_memory", "save_memory"],
                "dependencies": ["json", "os", "logging"]
            }
        }
    }

def test_load_json_filter(template_manager, tmp_path):
    """Test the load_json filter."""
    # Create a test JSON file
    test_data = {"key": "value"}
    json_path = tmp_path / "test.json"
    with open(json_path, 'w') as f:
        json.dump(test_data, f)

    # Create a test template that uses the load_json filter
    template_str = "{{ json_file | load_json }}"
    template = template_manager.environments["general"].from_string(template_str)
    
    # Render the template
    result = template.render(json_file=str(json_path))
    assert json.loads(result)["key"] == "value"

def test_tojson_filter(template_manager):
    """Test the tojson filter."""
    test_data = {"key": "value"}
    template_str = "{{ data | tojson }}"
    template = template_manager.environments["general"].from_string(template_str)
    
    # Render the template
    result = template.render(data=test_data)
    assert json.loads(result)["key"] == "value"

def test_full_sync_templates(template_manager, project_context, tmp_path):
    """Test that Full Sync templates can be rendered with project context."""
    # Create test templates
    test_gen_template = """\
    You are a test generation expert. Generate tests for {{ target_file }}.
    Project Context: {{ project_context | tojson }}
    """
    
    test_refactor_template = """\
    You are a refactoring expert. Analyze {{ target_file }}.
    Project Context: {{ project_context | tojson }}
    """

    # Save templates
    template_dir = tmp_path / "templates" / "full_sync"
    template_dir.mkdir(parents=True)
    
    with open(template_dir / "test_generation.prompt.j2", 'w') as f:
        f.write(test_gen_template)
    with open(template_dir / "refactor_suggestion.prompt.j2", 'w') as f:
        f.write(test_refactor_template)

    # Initialize TemplateManager with test directory
    tm = TemplateManager(str(template_dir))

    # Test rendering both templates
    context = {
        "target_file": "core/memory/MemoryManager.py",
        "project_context": project_context
    }

    test_gen_result = tm.render_general_template("test_generation.prompt.j2", context)
    assert "Generate tests for core/memory/MemoryManager.py" in test_gen_result
    assert '"name": "test_project"' in test_gen_result

    refactor_result = tm.render_general_template("refactor_suggestion.prompt.j2", context)
    assert "Analyze core/memory/MemoryManager.py" in refactor_result
    assert '"name": "test_project"' in refactor_result 
