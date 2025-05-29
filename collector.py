#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Основной класс для сбора файлов проекта
CodeCollector - сканирование, фильтрация и сортировка файлов
"""

from pathlib import Path
from typing import List
from config import Config
from utils import GitignoreHandler, FileFilters


class CodeCollector:
    """
    Основной класс для сбора файлов проекта
    Сканирует директорию, применяет фильтры (.gitignore, типы файлов), сортирует результат
    
    Атрибуты:
    - root_path: Path - корневой путь проекта
    - config: Config - конфигурация приложения
    - gitignore_patterns: List[str] - паттерны из .gitignore
    
    Методы:
    - scan_and_collect() -> List[Path]: Основной метод сбора файлов
    - _load_gitignore_patterns(): Загружает паттерны из .gitignore
    - _should_include_file(file_path) -> bool: Проверяет включение файла по всем фильтрам
    """
    
    def __init__(self, root_path: Path, config: Config):
        self.root_path = root_path.resolve()
        self.config = config
        self.gitignore_patterns = []
        
    def scan_and_collect(self) -> List[Path]:
        """Сканирует директорию и собирает файлы с учетом фильтров"""
        print(f"Сканирование директории: {self.root_path}")
        
        # Загружаем .gitignore паттерны
        self._load_gitignore_patterns()
        
        # Собираем файлы
        collected_files = []
        for file_path in self.root_path.rglob('*'):
            if self._should_include_file(file_path):
                collected_files.append(file_path)
        
        print(f"Найдено файлов: {len(collected_files)}")
        
        # Сортируем файлы
        if self.config.sort_by_time:
            print("Сортировка по времени изменения (новые сверху)...")
            collected_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        else:
            print("Сортировка по имени файла...")
            collected_files.sort()
        
        return collected_files
    
    def _load_gitignore_patterns(self):
        """Загружает паттерны из .gitignore"""
        main_gitignore = self.root_path / '.gitignore'
        self.gitignore_patterns = GitignoreHandler.parse_gitignore(main_gitignore)
        
        print(f"Загружено паттернов из .gitignore: {len(self.gitignore_patterns)}")
        if self.gitignore_patterns:
            print("Паттерны:", self.gitignore_patterns[:5], "..." if len(self.gitignore_patterns) > 5 else "")
    
    def _should_include_file(self, file_path: Path) -> bool:
        """Проверяет, нужно ли включать файл в коллекцию"""
        # Пропускаем директории
        if file_path.is_dir():
            return False
        
        # Проверяем .gitignore паттерны
        if GitignoreHandler.is_ignored_by_gitignore(file_path, self.root_path, self.gitignore_patterns):
            return False
            
        # Проверяем, не находится ли файл в исключаемой директории
        for parent in file_path.parents:
            if FileFilters.should_skip_directory(parent.name):
                return False
        
        # Пропускаем файлы по маске
        if FileFilters.should_skip_file(file_path):
            return False
            
        # Проверяем, что файл текстовый
        if not FileFilters.is_text_file(file_path):
            return False
            
        # Проверяем, что файл не пустой
        try:
            if file_path.stat().st_size == 0:
                return False
        except OSError:
            return False
            
        return True