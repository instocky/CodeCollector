#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Setup script для CodeCollector
Установка пакета через pip install
"""

from setuptools import setup, find_packages
from pathlib import Path

# Читаем README для long_description
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# Читаем requirements
def read_requirements():
    """Читает зависимости из requirements.txt"""
    requirements_file = this_directory / "requirements.txt"
    if requirements_file.exists():
        return requirements_file.read_text().strip().split('\n')
    return []

# Основная конфигурация пакета
setup(
    # Основная информация
    name="codecollector",
    version="1.0.0",
    author="CodeCollector Team",
    author_email="info@codecollector.dev",
    description="Инструмент для сбора файлов кода в один документ",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/codecollector",
    
    # Пакеты и модули
    packages=find_packages(),
    include_package_data=True,
    
    # Зависимости
    install_requires=read_requirements(),
    python_requires=">=3.8",
    
    # Консольные команды
    entry_points={
        'console_scripts': [
            'codecollector=codecollector.main:main',
        ],
    },
    
    # Классификаторы PyPI
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Documentation",
        "Topic :: Software Development :: Code Generators",
        "Topic :: Utilities",
        "Environment :: Console",
    ],
    
    # Ключевые слова для поиска
    keywords=[
        "code", "collector", "documentation", "markdown", 
        "source", "files", "aggregator", "developer-tools"
    ],
    
    # Дополнительные метаданные
    project_urls={
        "Bug Reports": "https://github.com/yourusername/codecollector/issues",
        "Source": "https://github.com/yourusername/codecollector",
        "Documentation": "https://github.com/yourusername/codecollector#readme",
    },
    
    # Дополнительные зависимости для разработки
    extras_require={
        'dev': [
            'pytest>=6.0',
            'pytest-cov>=2.0',
            'black>=21.0',
            'flake8>=3.8',
            'mypy>=0.800',
        ],
        'build': [
            'build>=0.7',
            'twine>=3.0',
        ],
    },
    
    # Конфигурация для wheel
    zip_safe=False,
)