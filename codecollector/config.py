#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Управление конфигурацией для CodeCollector
Config - структура настроек, ConfigManager - парсинг и управление
"""

import sys
from dataclasses import dataclass
from typing import Optional
from codecollector.models import ProjectSettings


@dataclass
class Config:
    """
    Структура конфигурации приложения
    
    Атрибуты:
    - interactive: bool - использовать интерактивный выбор файлов
    - sort_by_time: bool - сортировать по времени изменения
    - markdown_format: bool - использовать Markdown формат вывода
    - show_structure: bool - показывать структуру проекта
    - source_dir: Optional[str] - исходная директория для сканирования
    - output_file: Optional[str] - выходной файл
    """
    interactive: bool = False
    sort_by_time: bool = False
    markdown_format: bool = False
    show_structure: bool = False
    remote_mode: bool = False  # НОВОЕ ПОЛЕ
    source_dir: Optional[str] = None
    output_file: Optional[str] = None


class ConfigManager:
    """
    Менеджер конфигурации приложения
    Парсит CLI аргументы, объединяет с сохраненными настройками, интерактивная настройка
    
    Методы:
    - parse_cli_args() -> Config: Парсит аргументы командной строки
    - merge_with_saved_settings(config, project_settings) -> Config: Объединяет с сохраненными
    - interactive_config_setup(config, saved_settings_exist) -> Config: Интерактивная настройка
    - show_applied_config(config, from_settings): Показывает применяемые флаги
    """
    
    @staticmethod
    def parse_cli_args() -> Config:
        """Парсит аргументы командной строки"""
        config = Config()
        
        i = 1
        while i < len(sys.argv):
            arg = sys.argv[i]
            
            if arg in ['-i', '--interactive']:
                config.interactive = True
            elif arg in ['-t', '--time', '--sort-time']:
                config.sort_by_time = True
            elif arg in ['--no-time']:
                config.sort_by_time = False
            elif arg in ['-m', '--markdown']:
                config.markdown_format = True
            elif arg in ['--no-markdown']:
                config.markdown_format = False
            elif arg in ['-s', '--structure']:
                config.show_structure = True
            elif arg in ['--no-structure']:
                config.show_structure = False
            elif arg in ['-r', '--remote']:  # НОВЫЙ ФЛАГ
                config.remote_mode = True
            elif not arg.startswith('-'):
                # Позиционные аргументы
                if config.source_dir is None:
                    config.source_dir = arg
                elif config.output_file is None:
                    config.output_file = arg
            
            i += 1
        
        return config
    
    @staticmethod
    def merge_with_saved_settings(config: Config, project_settings: ProjectSettings) -> Config:
        """Объединяет CLI конфигурацию с сохраненными настройками"""
        saved_settings = project_settings.load_settings()
        
        if not saved_settings:
            return config
        
        saved_preferences = saved_settings.get('preferences', {})
        print(f"🔄 Загружены настройки проекта '{saved_settings.get('project_name', 'Unknown')}'")
        
        # CLI флаги имеют приоритет над сохраненными настройками
        if not any(arg in sys.argv for arg in ['-t', '--time', '--sort-time', '--no-time']):
            config.sort_by_time = saved_preferences.get('sort_by_time', config.sort_by_time)
        
        if not any(arg in sys.argv for arg in ['-m', '--markdown', '--no-markdown']):
            config.markdown_format = saved_preferences.get('markdown_format', config.markdown_format)
        
        if not any(arg in sys.argv for arg in ['-s', '--structure', '--no-structure']):
            config.show_structure = saved_preferences.get('show_structure', config.show_structure)
        
        # Используем сохраненное имя файла если не задано
        if not config.output_file:
            config.output_file = saved_preferences.get('default_output')
        
        return config
    
    @staticmethod
    def interactive_config_setup(config: Config, saved_settings_exist: bool = False) -> Config:
        """Интерактивная настройка конфигурации"""
        # Определяем выходной файл
        if not config.output_file:
            default_ext = ".md" if config.markdown_format else ".txt"
            default_output = f"collected_files{default_ext}"
            
            output_file = input(f"Введите имя выходного файла (по умолчанию '{default_output}'): ").strip()
            config.output_file = output_file if output_file else default_output
        
        # Спрашиваем про интерактивный режим если не указан
        if not config.interactive and '--interactive' not in sys.argv and '-i' not in sys.argv:
            choice = input("Использовать интерактивный выбор файлов? (y/N): ").strip().lower()
            config.interactive = choice in ['y', 'yes', 'д', 'да']
        
        # Если нет сохраненных настроек, спрашиваем про остальные опции
        if not saved_settings_exist:
            if not any(arg in sys.argv for arg in ['-t', '--time', '--sort-time', '--no-time']):
                choice = input("Сортировать по времени изменения (новые сверху)? (y/N): ").strip().lower()
                config.sort_by_time = choice in ['y', 'yes', 'д', 'да']
            
            if not any(arg in sys.argv for arg in ['-m', '--markdown', '--no-markdown']):
                choice = input("Использовать Markdown формат? (y/N): ").strip().lower()
                config.markdown_format = choice in ['y', 'yes', 'д', 'да']
                
                if config.markdown_format and not any(arg in sys.argv for arg in ['-s', '--structure', '--no-structure']):
                    choice = input("Включить структуру проекта? (y/N): ").strip().lower()
                    config.show_structure = choice in ['y', 'yes', 'д', 'да']
        
        return config
    
    @staticmethod
    def show_applied_config(config: Config, from_settings: bool = False):
        """Показывает применяемую конфигурацию"""
        flags = []
        
        if config.sort_by_time:
            flags.append('-t')
        if config.markdown_format:
            flags.append('-m')
        if config.show_structure:
            flags.append('-s')
        
        if flags:
            flag_str = ' '.join(flags)
            source = "сохраненные настройки" if from_settings else "CLI аргументы"
            print(f"📋 Применяемые флаги: {flag_str} ({source})")
        else:
            print("📋 Используются настройки по умолчанию")