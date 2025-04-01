#!/usr/bin/env python3
"""
Generate test tasks for the autonomous loop system.

This script creates multiple prompt task files in the queued_tasks directory
to test the autonomous execution system.
"""

import os
import json
import time

# Configuration
OUTPUT_DIR = "queued_tasks"
SERVICE_TEMPLATES = [
    {
        "service_name": "LoggerService",
        "service_function": "application-wide logging and monitoring",
        "dependency_1": "ConfigService",
        "dependency_2": "ErrorHandler"
    },
    {
        "service_name": "UserService",
        "service_function": "user management and profile operations",
        "dependency_1": "DatabaseService",
        "dependency_2": "CacheManager"
    },
    {
        "service_name": "PaymentProcessor",
        "service_function": "handling financial transactions and payment processing",
        "dependency_1": "PaymentGateway",
        "dependency_2": "SecurityService"
    }
]

WEB_TEMPLATES = [
    {
        "url": "https://github.com",
        "task_type": "feature_analysis"
    },
    {
        "url": "https://stackoverflow.com",
        "task_type": "structure_analysis"
    }
]

PROJECT_TEMPLATES = [
    {
        "project_path": "./src",
        "task_type": "code_review"
    }
]

def generate_service_tasks():
    """Generate service class tasks."""
    for i, params in enumerate(SERVICE_TEMPLATES):
        task_id = f"service-{i+1:03d}"
        task = {
            "id": task_id,
            "description": f"Generate {params['service_name']} class",
            "type": "cursor",
            "is_cursor_task": True,
            "template_name": "service/service_class_template",
            "params": params,
            "target_output": "typescript_service"
        }
        
        # Save task to file
        filename = f"{task_id}_{int(time.time())}.prompt.json"
        path = os.path.join(OUTPUT_DIR, filename)
        
        with open(path, "w") as f:
            json.dump(task, f, indent=2)
            
        print(f"Generated service task: {path}")

def generate_web_tasks():
    """Generate web analysis tasks."""
    for i, params in enumerate(WEB_TEMPLATES):
        task_id = f"web-{i+1:03d}"
        task = {
            "id": task_id,
            "description": f"Analyze website {params['url']}",
            "type": "cursor",
            "is_cursor_task": True,
            "template_name": "web/web_analysis_template",
            "params": {
                **params,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
            },
            "target_output": "web_analysis"
        }
        
        # Save task to file
        filename = f"{task_id}_{int(time.time())}.prompt.json"
        path = os.path.join(OUTPUT_DIR, filename)
        
        with open(path, "w") as f:
            json.dump(task, f, indent=2)
            
        print(f"Generated web task: {path}")

def generate_project_tasks():
    """Generate project analysis tasks."""
    for i, params in enumerate(PROJECT_TEMPLATES):
        task_id = f"project-{i+1:03d}"
        task = {
            "id": task_id,
            "description": f"Analyze project in {params['project_path']}",
            "type": "cursor",
            "is_cursor_task": True,
            "template_name": "project/project_analysis_template",
            "params": {
                **params,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
            },
            "target_output": "project_analysis"
        }
        
        # Save task to file
        filename = f"{task_id}_{int(time.time())}.prompt.json"
        path = os.path.join(OUTPUT_DIR, filename)
        
        with open(path, "w") as f:
            json.dump(task, f, indent=2)
            
        print(f"Generated project task: {path}")

def main():
    """Main entry point."""
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Generate tasks
    generate_service_tasks()
    generate_web_tasks()
    generate_project_tasks()
    
    print(f"Generated a total of {len(SERVICE_TEMPLATES) + len(WEB_TEMPLATES) + len(PROJECT_TEMPLATES)} tasks")

if __name__ == "__main__":
    main() 