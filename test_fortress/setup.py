#!/usr/bin/env python3
"""
Test Fortress Setup Script

Installation and package configuration for Test Fortress.
"""

from setuptools import setup, find_packages

with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='test-fortress',
    version='1.0.0',
    description='Comprehensive testing framework for Dream.OS subsystems',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Dream.OS Team',
    author_email='team@dream-os.ai',
    url='https://github.com/dream-os/test-fortress',
    packages=find_packages(exclude=['tests*']),
    entry_points={
        'console_scripts': [
            'test-fortress=test_fortress.cli:main',
        ],
    },
    install_requires=[
        'pytest>=7.4.3',
        'pytest-cov>=4.1.0',
        'pytest-xdist>=3.3.1',
        'pytest-timeout>=2.1.0',
        'pytest-randomly>=3.15.0',
        'mutmut>=2.4.3',
        'hypothesis>=6.82.6',
        'coverage>=7.3.2',
        'mypy>=1.6.1',
        'pyright>=1.1.332',
        'black>=23.10.0',
        'flake8>=6.1.0',
        'isort>=5.12.0',
        'pydantic>=2.4.2',
        'typing-extensions>=4.8.0',
        'python-json-logger>=2.0.7'
    ],
    extras_require={
        'dev': [
            'pytest-watch>=4.2.0',
            'pytest-sugar>=0.9.7',
            'pytest-clarity>=1.0.1',
            'pytest-html>=3.2.0'
        ]
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Software Development :: Testing',
        'Topic :: Software Development :: Quality Assurance'
    ],
    python_requires='>=3.8',
    include_package_data=True,
    zip_safe=False
) 