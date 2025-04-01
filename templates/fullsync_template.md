# Full Sync Mode: {{ task_name }}

## Context
I need to {{ goal }}. This is part of the {{ project_name }} project.

## Requirements
{% if requirements %}
{% for req in requirements %}
- {{ req }}
{% endfor %}
{% else %}
- Create a clean and modular implementation
- Follow project conventions
- Add appropriate error handling
- Include proper documentation
{% endif %}

## Output
Please create a {{ language }} implementation for {{ output_file }}.

{% if existing_structure %}
The existing structure I'm working with looks like:
```
{{ existing_structure }}
```
{% endif %}

{% if related_files %}
Related files that provide context:
{% for file in related_files %}
- {{ file }}
{% endfor %}
{% endif %}

## Special Instructions
{% if special_instructions %}
{{ special_instructions }}
{% else %}
- Follow domain-driven design principles
- Use dependency injection where appropriate
- Make sure to handle edge cases
{% endif %}

Thank you! 