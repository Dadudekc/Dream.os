from setuptools import setup, find_packages

setup(
    name="chat_mate",
    version="0.1.0",
    description="AI-Powered Community Management",
    author="Victor",
    packages=find_packages(include=['config', 'config.*', 'core', 'core.*', 'interfaces', 'interfaces.*']),
    python_requires=">=3.6",
    install_requires=[
        "PyQt5",
        "requests",
        "apscheduler",
    ],
) 