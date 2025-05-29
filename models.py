#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модели данных для CodeCollector
TreeNode - узел дерева файлов, ProjectSettings - настройки проекта
"""

import json
import datetime
from pathlib import Path
from typing import List, Optional


class TreeNode:
    """
    Узел дерева файлов/папок для интерактивного выбора
    
    Атрибуты:
    - path: Path - путь к файлу/папке
    - is_file: bool - является ли файлом
    - parent: TreeNode - родительский узел
    - children: List[TreeNode] - дочерние узлы (только для папок)
    - selected: bool - выбран ли узел
    - expanded: bool - развернут ли узел (для папок)
    - visible: bool - видим ли узел
    
    Методы:
    - get_selection_state() -> str: Возвращает 'all'/'none'/'partial'
    - set_selected_recursive(selected): Устанавливает выбор рекурсивно
    - get_display_name() -> str: Возвращает отображаемое имя
    - get_file_count() -> int: Подсчитывает файлы в ветке
    - get_selected_files() -> List[Path]: Возвращает выбранные файлы
    """
    
    def __init__(self, path, is_file=True, parent=None):
        self.path = path
        self.is_file = is_file
        self.parent = parent
        self.children = [] if not is_file else None
        self.selected = False
        self.expanded = not is_file  # Файлы всегда "развернуты"
        self.visible = True
        
    def get_selection_state(self):
        """Возвращает состояние выбора: 'all', 'none', 'partial'"""
        if self.is_file:
            return 'all' if self.selected else 'none'
        
        if not self.children:
            return 'none'
            
        selected_count = sum(1 for child in self.children 
                           if child.get_selection_state() in ['all', 'partial'])
        
        if selected_count == 0:
            return 'none'
        elif selected_count == len(self.children):
            return 'all'
        else:
            return 'partial'
    
    def set_selected_recursive(self, selected):
        """Устанавливает выбор рекурсивно"""
        if self.is_file:
            self.selected = selected
        else:
            for child in self.children:
                child.set_selected_recursive(selected)
    
    def get_display_name(self):
        """Возвращает отображаемое имя"""
        if self.parent is None:
            return str(self.path.name) if self.path.name else str(self.path)
        return self.path.name
    
    def get_file_count(self):
        """Возвращает количество файлов в папке"""
        if self.is_file:
            return 1
        return sum(child.get_file_count() for child in self.children)
    
    def get_selected_files(self):
        """Возвращает список выбранных файлов"""
        if self.is_file:
            return [self.path] if self.selected else []
        
        result = []
        for child in self.children:
            result.extend(child.get_selected_files())
        return result


class ProjectSettings:
    """
    Класс для работы с настройками проекта
    Сохраняет/загружает настройки в .codecollector/проект.json
    
    Атрибуты:
    - root_path: Path - корневой путь проекта
    - settings_dir: Path - директория настроек (.codecollector)
    - project_name: str - имя проекта
    - settings_file: Path - файл настроек
    
    Методы:
    - load_settings() -> Optional[dict]: Загружает настройки проекта
    - save_settings(preferences, selected_files, selected_folders): Сохраняет настройки
    - filter_existing_paths(files, folders) -> Tuple: Фильтрует существующие пути
    - _update_gitignore(): Добавляет .codecollector в .gitignore
    """
    
    def __init__(self, root_path):
        self.root_path = Path(root_path).resolve()
        self.settings_dir = self.root_path / ".codecollector"
        self.project_name = self.root_path.name
        self.settings_file = self.settings_dir / f"{self.project_name}.json"
        
    def load_settings(self) -> Optional[dict]:
        """Загружает настройки проекта"""
        if not self.settings_file.exists():
            return None
            
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                
            # Проверяем актуальность пути
            if settings.get('full_path') != str(self.root_path):
                return None
                
            return settings
        except (json.JSONDecodeError, OSError) as e:
            print(f"⚠️  Предупреждение: Не удалось загрузить настройки проекта: {e}")
            return None
    
    def save_settings(self, preferences: dict, selected_files: List[Path], selected_folders: List[Path]):
        """Сохраняет настройки проекта"""
        try:
            # Создаем папку если не существует
            self.settings_dir.mkdir(exist_ok=True)
            
            # Конвертируем пути в относительные строки
            selected_files_rel = []
            selected_folders_rel = []
            
            for file_path in selected_files:
                try:
                    rel_path = file_path.relative_to(self.root_path)
                    selected_files_rel.append(str(rel_path).replace('\\', '/'))
                except ValueError:
                    continue
            
            for folder_path in selected_folders:
                try:
                    rel_path = folder_path.relative_to(self.root_path)
                    selected_folders_rel.append(str(rel_path).replace('\\', '/'))
                except ValueError:
                    continue
            
            settings = {
                "project_name": self.project_name,
                "full_path": str(self.root_path),
                "last_updated": datetime.datetime.now().isoformat(),
                "preferences": preferences,
                "selected_files": selected_files_rel,
                "selected_folders": selected_folders_rel
            }
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
                
            print("💾 Настройки проекта сохранены")
            
            # Добавляем в .gitignore если нужно
            self._update_gitignore()
            
        except Exception as e:
            print(f"⚠️  Предупреждение: Не удалось сохранить настройки: {e}")
    
    def _update_gitignore(self):
        """Добавляет .codecollector в .gitignore если нужно"""
        gitignore_path = self.root_path / '.gitignore'
        gitignore_entry = '.codecollector/'
        
        try:
            # Читаем существующий .gitignore
            existing_lines = []
            if gitignore_path.exists():
                with open(gitignore_path, 'r', encoding='utf-8') as f:
                    existing_lines = f.read().splitlines()
            
            # Проверяем, есть ли уже запись
            if gitignore_entry not in existing_lines and '.codecollector' not in existing_lines:
                with open(gitignore_path, 'a', encoding='utf-8') as f:
                    if existing_lines and not existing_lines[-1].strip():
                        f.write(f"{gitignore_entry}\n")
                    else:
                        f.write(f"\n{gitignore_entry}\n")
                        
        except Exception:
            pass  # Игнорируем ошибки с .gitignore
    
    def filter_existing_paths(self, selected_files: List[str], selected_folders: List[str]) -> tuple:
        """Фильтрует существующие пути из сохраненных настроек"""
        existing_files = []
        existing_folders = []
        
        # Проверяем файлы
        for rel_path_str in selected_files:
            abs_path = self.root_path / rel_path_str
            if abs_path.exists() and abs_path.is_file():
                existing_files.append(abs_path)
        
        # Проверяем папки
        for rel_path_str in selected_folders:
            abs_path = self.root_path / rel_path_str
            if abs_path.exists() and abs_path.is_dir():
                existing_folders.append(abs_path)
        
        return existing_files, existing_folders