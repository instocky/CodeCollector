#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Очищенная версия collector.py без лишнего вывода
"""

from pathlib import Path
from typing import List
from codecollector.config import Config
from codecollector.utils import GitignoreHandler, FileFilters


class CodeCollector:
    """
    Основной класс для сбора файлов проекта
    Сканирует директорию, применяет фильтры, сортирует результат
    """
    
    def __init__(self, root_path: Path, config: Config):
        self.root_path = root_path.resolve()
        self.config = config
        self.gitignore_patterns = []
        
    def scan_and_collect(self) -> List[Path]:
        """Сканирует директорию и собирает файлы с учетом фильтров"""
        # Загружаем .gitignore паттерны БЕЗ ВЫВОДА
        self._load_gitignore_patterns()
        
        # Собираем файлы БЕЗ ВЫВОДА
        collected_files = []
        for file_path in self.root_path.rglob('*'):
            if self._should_include_file(file_path):
                collected_files.append(file_path)
        
        # Сортируем файлы БЕЗ ВЫВОДА
        if self.config.sort_by_time:
            collected_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        else:
            collected_files.sort()
        
        return collected_files
    
    def _load_gitignore_patterns(self):
        """Загружает паттерны из .gitignore БЕЗ ВЫВОДА"""
        main_gitignore = self.root_path / '.gitignore'
        self.gitignore_patterns = GitignoreHandler.parse_gitignore(main_gitignore)
    
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

# Альтернатива - минимальный вывод только для debug режима
class CodeCollectorWithDebug:
    """Версия с опциональным debug выводом"""
    
    def scan_and_collect(self) -> List[Path]:
        """Сканирует директорию и собирает файлы"""
        debug = "--debug" in sys.argv
        
        if debug:
            print(f"Сканирование директории: {self.root_path}")
        
        # Загружаем .gitignore паттерны
        self._load_gitignore_patterns()
        if debug and self.gitignore_patterns:
            print(f"Загружено паттернов из .gitignore: {len(self.gitignore_patterns)}")
        
        # Собираем файлы
        collected_files = []
        for file_path in self.root_path.rglob('*'):
            if self._should_include_file(file_path):
                collected_files.append(file_path)
        
        if debug:
            print(f"Найдено файлов: {len(collected_files)}")
        
        # Сортируем файлы
        if self.config.sort_by_time:
            if debug:
                print("Сортировка по времени изменения (новые сверху)...")
            collected_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        else:
            if debug:
                print("Сортировка по имени файла...")
            collected_files.sort()
        
        return collected_files