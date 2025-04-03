from setuptools import setup, find_packages

setup(
    name="chat_mate",
    version="0.1.0",
    description="AI-Powered Community Management",
    author="Victor",
    packages=find_packages(include=["chat_mate", "chat_mate.*", "tests", "tests.*"]),
    python_requires=">=3.6",
    install_requires=[
        "PyQt5",
        "requests",
        "apscheduler",
        "pylint",
        "pytest",
        "pytest-asyncio",
        "pytest-qt",
        "jinja2",
        "discord.py",
        "selenium",
        "undetected-chromedriver",
        "setuptools",
        "webdriver-manager",
        "matplotlib"
    ],
) 
