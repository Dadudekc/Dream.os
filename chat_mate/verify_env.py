#!/usr/bin/env python3
"""
Environment verification script to check if all required dependencies for the GUI application
are installed correctly.
"""

def verify_imports():
    """Verify that all required libraries can be imported successfully."""
    try:
        # Core GUI Dependencies
        print("\nChecking Core GUI Dependencies...")
        import PyQt5
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import QT_VERSION_STR
        import qasync
        import asyncqt
        print("✅ Core GUI Dependencies OK")
        print(f"   PyQt5 Version: {PyQt5.QtCore.QT_VERSION_STR}")
        
        # Web and API
        print("\nChecking Web and API Dependencies...")
        import fastapi
        import pydantic
        import starlette
        import uvicorn
        print("✅ Web and API Dependencies OK")
        print(f"   FastAPI Version: {fastapi.__version__}")
        print(f"   Pydantic Version: {pydantic.__version__}")
        
        # AI and ML
        print("\nChecking AI and ML Dependencies...")
        import langchain
        import openai
        import chromadb
        import torch
        import transformers
        import sentence_transformers
        print("✅ AI and ML Dependencies OK")
        print(f"   LangChain Version: {langchain.__version__}")
        print(f"   OpenAI Version: {openai.__version__}")
        print(f"   PyTorch Version: {torch.__version__}")
        
        # Database
        print("\nChecking Database Dependencies...")
        import sqlalchemy
        import alembic
        import psycopg2
        print("✅ Database Dependencies OK")
        print(f"   SQLAlchemy Version: {sqlalchemy.__version__}")
        
        # Discord Integration
        print("\nChecking Discord Integration...")
        import discord
        import aiohttp
        print("✅ Discord Integration OK")
        print(f"   Discord.py Version: {discord.__version__}")
        
        # Data Processing
        print("\nChecking Data Processing Libraries...")
        import numpy
        import pandas
        import scipy
        import sklearn
        print("✅ Data Processing Libraries OK")
        print(f"   NumPy Version: {numpy.__version__}")
        print(f"   Pandas Version: {pandas.__version__}")
        
        # Utilities
        print("\nChecking Utility Libraries...")
        import yaml
        import dotenv
        import colorlog
        import apscheduler
        import bs4
        import httpx
        import requests
        print("✅ Utility Libraries OK")
        
        print("\n🎉 All dependencies verified successfully!")
        return True
        
    except ImportError as e:
        print(f"\n❌ Import Error: {str(e)}")
        print("Please install the missing package using:")
        print(f"pip install {str(e).split()[-1]}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected Error: {str(e)}")
        return False

def verify_gui():
    """Verify that the GUI application can be initialized."""
    try:
        print("\nAttempting to initialize QApplication...")
        import sys
        from PyQt5.QtWidgets import QApplication
        
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        print("✅ QApplication initialized successfully")
        return True
        
    except Exception as e:
        print(f"\n❌ GUI Initialization Error: {str(e)}")
        return False

if __name__ == "__main__":
    if verify_imports() and verify_gui():
        print("\n✅ Environment is ready to run the GUI application!")
        print("You can now run: python -m interfaces.pyqt.DreamOsMainWindow")
    else:
        print("\n❌ Please fix the above errors before running the GUI application.") 