#!/bin/bash
# Dreamscape Context Update - Linux/Mac Shell Script
# This script checks if a context update is due and sends it to ChatGPT

echo "Checking for scheduled Dreamscape context updates..."
python scripts/check_context_updates.py --config config/dreamscape_config.yaml

if [ $? -ne 0 ]; then
    echo "Error: Context update failed with code $?"
else
    echo "Context update check completed successfully."
fi 