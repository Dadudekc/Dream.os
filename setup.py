"""Setup script for Dream.OS."""
from setuptools import setup, find_packages

setup(
    name="chat_mate",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        'PyQt5>=5.15.9',
        'PyQtChart>=5.15.7',
        'requests>=2.31.0',
        'pytest>=7.0.0',
        'pyyaml>=6.0.0',
    ],
    author="Dream.OS Team",
    author_email="info@dreamos.ai",
    description="AI Content Generation Studio",
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    url="https://github.com/dreamos/chat_mate",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
) 
