#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CodeCollector - Инструмент для сбора файлов кода в один документ

Пакет для сканирования проектов, фильтрации файлов и создания
единого документа с кодом в Markdown или текстовом формате.

Основные компоненты:
- CodeCollector: основной класс сборщика
- InteractiveSelector: интерактивный выбор файлов
- Config: управление конфигурацией
- OutputWriter: запись результатов в различных форматах

Использование:
    from codecollector import CodeCollectorApp
    app = CodeCollectorApp()
    app.run()

Или через CLI:
    codecollector --help
"""

__version__ = "1.0.0"
__author__ = "CodeCollector Team"
__email__ = "info@codecollector.dev"
__license__ = "MIT"

# Импорты основных классов для удобного использования
from .main import CodeCollectorApp, main
from .collector import CodeCollector
from .config import Config, ConfigManager
from .models import TreeNode, ProjectSettings
from .selector import InteractiveSelector
from .writers import MarkdownWriter, TextWriter, OutputWriter

# Экспортируемые символы
__all__ = [
    # Основные классы
    'CodeCollectorApp',
    'CodeCollector',
    'Config',
    'ConfigManager',
    
    # Модели данных
    'TreeNode',
    'ProjectSettings',
    
    # Интерактивный выбор
    'InteractiveSelector',
    
    # Писатели вывода
    'MarkdownWriter',
    'TextWriter',
    'OutputWriter',
    
    # Главная функция
    'main',
    
    # Метаданные
    '__version__',
    '__author__',
    '__email__',
    '__license__',
]

# Информация о пакете
def get_version():
    """Возвращает версию пакета"""
    return __version__

def get_package_info():
    """Возвращает информацию о пакете"""
    return {
        'name': 'codecollector',
        'version': __version__,
        'author': __author__,
        'email': __email__,
        'license': __license__,
        'description': 'Инструмент для сбора файлов кода в один документ'
    }