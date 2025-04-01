"""
Setup script for Dream.OS Intelligence Scanner.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="dream-os-scanner",
    version="0.1.0",
    author="Dream.OS Team",
    description="A comprehensive code analysis and optimization tool for Dream.OS",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dream-os/intelligence-scanner",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "astroid>=2.9.0",  # For AST analysis
        "pylint>=2.12.0",  # For code quality metrics
        "pytest>=7.0.0",   # For test analysis
        "coverage>=6.2",   # For coverage analysis
        "networkx>=2.6.3", # For dependency graph analysis
        "rich>=10.16.0",  # For beautiful CLI output
    ],
    entry_points={
        "console_scripts": [
            "dream-scan=scanner.cli:main",
        ],
    },
    extras_require={
        "dev": [
            "black",
            "isort",
            "mypy",
            "pytest-cov",
            "pytest-mock",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/dream-os/intelligence-scanner/issues",
        "Source": "https://github.com/dream-os/intelligence-scanner",
        "Documentation": "https://dream-os.readthedocs.io",
    },
) 