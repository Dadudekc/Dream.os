from setuptools import setup, find_packages

setup(
    name="code_quality_dashboard",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pytest>=7.0.0",
    ],
    author="Dream.OS Team",
    description="A real-time code quality monitoring dashboard",
    python_requires=">=3.8",
) 