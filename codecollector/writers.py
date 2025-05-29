#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Классы для записи результатов в различных форматах
OutputWriter - абстрактный базовый класс
MarkdownWriter - вывод в Markdown формате с подсветкой синтаксиса
TextWriter - простой текстовый вывод
"""

import datetime
from pathlib import Path
from typing import List, Dict
from abc import ABC, abstractmethod


class OutputWriter(ABC):
    """
    Абстрактный класс для записи результатов
    Базовый класс для всех форматтеров вывода
    
    Атрибуты:
    - root_path: Path - корневой путь проекта
    
    Методы:
    - write(files, output_file): Абстрактный метод записи файлов
    - _read_file_content(file_path) -> str: Читает содержимое файла с обработкой кодировок
    """
    
    def __init__(self, root_path: Path):
        self.root_path = root_path
    
    @abstractmethod
    def write(self, files: List[Path], output_file: str):
        """Записывает файлы в выходной файл"""
        pass
    
    def _read_file_content(self, file_path: Path) -> str:
        """Читает содержимое файла с обработкой кодировок"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Пытаемся прочитать в другой кодировке
            try:
                with open(file_path, 'r', encoding='cp1251') as f:
                    return f.read()
            except Exception:
                return "[Ошибка чтения файла: неподдерживаемая кодировка]\n"
        except Exception as e:
            return f"[Ошибка чтения файла: {e}]\n"


class MarkdownWriter(OutputWriter):
    """
    Записывает файлы в Markdown формате
    Создает красивый документ с заголовками, подсветкой синтаксиса и структурой проекта
    
    Атрибуты:
    - show_structure: bool - включать ли структуру проекта
    
    Методы:
    - write(files, output_file): Записывает в Markdown формате
    - _write_header(out_f, files): Записывает заголовок документа
    - _write_structure(out_f, files): Записывает структуру проекта как дерево
    - _write_files(out_f, files): Записывает содержимое файлов с подсветкой
    - _get_language_for_extension(extension) -> str: Определяет язык для подсветки
    - _generate_project_structure(files) -> str: Генерирует древовидную структуру
    - _build_tree_text(node_dict, prefix, is_last) -> List[str]: Строит текстовое дерево
    """
    
    def __init__(self, root_path: Path, show_structure: bool = False):
        super().__init__(root_path)
        self.show_structure = show_structure
    
    def write(self, files: List[Path], output_file: str):
        """Записывает файлы в Markdown формате"""
        with open(output_file, 'w', encoding='utf-8') as out_f:
            self._write_header(out_f, files)
            
            if self.show_structure:
                self._write_structure(out_f, files)
            
            out_f.write("---\n\n")
            out_f.write("## 📄 Содержимое файлов\n\n")
            
            self._write_files(out_f, files)
    
    def _write_header(self, out_f, files: List[Path]):
        """Записывает заголовок Markdown"""
        project_name = self.root_path.name
        out_f.write(f"# CodeCollector - {project_name}\n\n")
        out_f.write(f"**Собрано файлов:** {len(files)}  \n")
        out_f.write(f"**Дата сбора:** {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')}  \n")
        out_f.write(f"**Путь:** `{self.root_path}`\n\n")
    
    def _write_structure(self, out_f, files: List[Path]):
        """Записывает структуру проекта"""
        out_f.write("## 📁 Структура проекта\n\n")
        structure = self._generate_project_structure(files)
        out_f.write("```\n")
        out_f.write(structure)
        out_f.write("```\n\n")
    
    def _write_files(self, out_f, files: List[Path]):
        """Записывает содержимое файлов"""
        for file_path in sorted(files):
            try:
                rel_path = file_path.relative_to(self.root_path)
                out_f.write(f"### `{rel_path}`\n\n")
                
                # Определяем язык для подсветки синтаксиса
                lang = self._get_language_for_extension(file_path.suffix.lower())
                out_f.write(f"```{lang}\n")
                
                content = self._read_file_content(file_path)
                out_f.write(content)
                
                out_f.write("\n```\n\n")
                print(f"Обработан: {rel_path}")
                
            except Exception as e:
                print(f"Ошибка при обработке {file_path}: {e}")
                continue
    
    def _get_language_for_extension(self, extension: str) -> str:
        """Возвращает язык для подсветки синтаксиса по расширению файла"""
        language_map = {
            '.py': 'python',
            '.php': 'php', 
            '.js': 'javascript',
            '.jsx': 'jsx',
            '.ts': 'typescript',
            '.tsx': 'tsx',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.sass': 'sass',
            '.less': 'less',
            '.sql': 'sql',
            '.json': 'json',
            '.xml': 'xml',
            '.yml': 'yaml',
            '.yaml': 'yaml',
            '.toml': 'toml',
            '.ini': 'ini',
            '.conf': 'apache',
            '.md': 'markdown',
            '.sh': 'bash',
            '.bash': 'bash',
            '.zsh': 'bash',
            '.fish': 'fish',
            '.bat': 'batch',
            '.cmd': 'batch',
            '.ps1': 'powershell',
            '.dockerfile': 'dockerfile',
            '.go': 'go',
            '.java': 'java',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.c': 'c',
            '.cpp': 'cpp',
            '.cxx': 'cpp',
            '.cc': 'cpp',
            '.h': 'c',
            '.hpp': 'cpp',
            '.cs': 'csharp',
            '.vb': 'vbnet',
            '.rb': 'ruby',
            '.rs': 'rust',
            '.swift': 'swift',
            '.dart': 'dart',
            '.lua': 'lua',
            '.perl': 'perl',
            '.pl': 'perl',
            '.r': 'r',
            '.matlab': 'matlab',
            '.vim': 'vim',
            '.vue': 'vue',
            '.svelte': 'svelte',
            '.astro': 'astro'
        }
        return language_map.get(extension, '')
    
    def _generate_project_structure(self, files: List[Path]) -> str:
        """Генерирует древовидную структуру проекта"""
        # Группируем файлы по папкам
        structure = {}
        
        for file_path in files:
            rel_path = file_path.relative_to(self.root_path)
            parts = rel_path.parts
            
            current = structure
            # Проходим по всем частям пути
            for i, part in enumerate(parts):
                if part not in current:
                    is_file = i == len(parts) - 1
                    current[part] = {
                        '_is_file': is_file,
                        '_path': file_path if is_file else None
                    }
                    if not is_file:
                        current[part]['_children'] = {}
                
                if not current[part]['_is_file']:
                    current = current[part]['_children']
        
        # Генерируем текстовое представление
        tree_lines = [f"{self.root_path.name}/"]
        if structure:
            tree_lines.extend(self._build_tree_text(structure))
        
        return "\n".join(tree_lines)
    
    def _build_tree_text(self, node_dict: dict, prefix: str = "", is_last: bool = True) -> List[str]:
        """Строит текстовое представление дерева"""
        result = []
        items = sorted(node_dict.items(), key=lambda x: (x[1]['_is_file'], x[0].lower()))
        
        for i, (name, info) in enumerate(items):
            is_last_item = i == len(items) - 1
            current_prefix = "└── " if is_last_item else "├── "
            
            if info['_is_file']:
                result.append(f"{prefix}{current_prefix}{name}")
            else:
                result.append(f"{prefix}{current_prefix}{name}/")
                # Рекурсивно добавляем детей
                next_prefix = prefix + ("    " if is_last_item else "│   ")
                children_text = self._build_tree_text(info['_children'], next_prefix, is_last_item)
                result.extend(children_text)
        
        return result


class TextWriter(OutputWriter):
    """
    Записывает файлы в обычном текстовом формате
    Простой формат без разметки для максимальной совместимости
    
    Методы:
    - write(files, output_file): Записывает в простом текстовом формате
    """
    
    def write(self, files: List[Path], output_file: str):
        """Записывает файлы в текстовом формате"""
        with open(output_file, 'w', encoding='utf-8') as out_f:
            # Простой заголовок
            project_name = self.root_path.name
            out_f.write(f"CodeCollector - {project_name}\n")
            out_f.write(f"Собрано файлов: {len(files)}\n")
            out_f.write(f"Дата сбора: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")
            out_f.write(f"Путь: {self.root_path}\n")
            out_f.write("=" * 80 + "\n\n")
            
            # Записываем файлы
            for file_path in sorted(files):
                try:
                    rel_path = file_path.relative_to(self.root_path)
                    out_f.write(f"# {rel_path}\n")
                    out_f.write("-" * 40 + "\n")
                    
                    content = self._read_file_content(file_path)
                    out_f.write(content)
                    out_f.write("\n\n")
                    
                    print(f"Обработан: {rel_path}")
                    
                except Exception as e:
                    print(f"Ошибка при обработке {file_path}: {e}")
                    continue