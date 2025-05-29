#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import fnmatch
import datetime
import json
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Optional, Tuple
from abc import ABC, abstractmethod

# Для интерактивного выбора
try:
    import msvcrt  # Windows
    WINDOWS = True
except ImportError:
    import termios, tty, select  # Unix/Linux/Mac
    WINDOWS = False


@dataclass
class Config:
    """Конфигурация приложения"""
    interactive: bool = False
    sort_by_time: bool = False
    markdown_format: bool = False
    show_structure: bool = False
    source_dir: Optional[str] = None
    output_file: Optional[str] = None


class TreeNode:
    """Узел дерева файлов/папок"""
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
    """Класс для работы с настройками проекта"""
    
    def __init__(self, root_path):
        self.root_path = Path(root_path).resolve()
        self.settings_dir = self.root_path / ".codecollector"
        self.project_name = self.root_path.name
        self.settings_file = self.settings_dir / f"{self.project_name}.json"
        
    def load_settings(self):
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
    
    def save_settings(self, preferences, selected_files, selected_folders):
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
    
    def filter_existing_paths(self, selected_files, selected_folders):
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


class KeyboardHandler:
    """Обработчик ввода с клавиатуры (кроссплатформенный)"""
    
    @staticmethod
    def get_key():
        """Получает нажатую клавишу без Enter"""
        if WINDOWS:
            return KeyboardHandler._get_key_windows()
        else:
            return KeyboardHandler._get_key_unix()
    
    @staticmethod
    def _get_key_windows():
        """Windows-специфичная обработка клавиш"""
        key = msvcrt.getch()
        if key == b'\xe0' or key == b'\x00':  # Специальные клавиши (стрелки)
            key2 = msvcrt.getch()
            if key2 == b'H' or key2 == b'\x48':  # Стрелка вверх
                return 'UP'
            elif key2 == b'P' or key2 == b'\x50':  # Стрелка вниз
                return 'DOWN'
            elif key2 == b'K' or key2 == b'\x4b':  # Стрелка влево
                return 'LEFT'
            elif key2 == b'M' or key2 == b'\x4d':  # Стрелка вправо
                return 'RIGHT'
        elif key == b' ':  # Пробел
            return 'SPACE'
        elif key == b'\r':  # Enter
            return 'ENTER'
        elif key == b'\x1b':  # Escape
            return 'ESC'
        elif key == b'q' or key == b'Q':
            return 'QUIT'
        elif key == b'a' or key == b'A':
            return 'ALL'
        elif key == b'n' or key == b'N':
            return 'NONE'
        elif key == b'w' or key == b'W':  # W/S как альтернатива стрелкам
            return 'UP'
        elif key == b's' or key == b'S':
            return 'DOWN'
        elif key == b'j':  # J/K как в vim
            return 'DOWN'
        elif key == b'k':
            return 'UP'
        elif key == b'f' or key == b'F':
            return 'FIND'
        elif key == b'+' or key == b'=':
            return 'EXPAND'
        elif key == b'-' or key == b'_':
            return 'COLLAPSE'
        return key.decode('utf-8', errors='ignore')
    
    @staticmethod
    def _get_key_unix():
        """Unix/Linux/Mac обработка клавиш"""
        old_settings = termios.tcgetattr(sys.stdin)
        try:
            tty.setraw(sys.stdin.fileno())
            key = sys.stdin.read(1)
            
            if key == '\x1b':  # ESC последовательность
                # Читаем следующие символы
                next_chars = ''
                try:
                    # Проверяем есть ли еще символы (с таймаутом)
                    if select.select([sys.stdin], [], [], 0.1)[0]:
                        next_chars = sys.stdin.read(2)
                except:
                    pass
                
                full_seq = key + next_chars
                
                if full_seq == '\x1b[A':  # Стрелка вверх
                    return 'UP'
                elif full_seq == '\x1b[B':  # Стрелка вниз
                    return 'DOWN'
                elif full_seq == '\x1b[C':  # Стрелка вправо
                    return 'RIGHT'
                elif full_seq == '\x1b[D':  # Стрелка влево
                    return 'LEFT'
                elif full_seq == '\x1b[5':  # Page Up
                    try:
                        if select.select([sys.stdin], [], [], 0.1)[0]:
                            sys.stdin.read(1)  # Читаем ~
                    except:
                        pass
                    return 'PAGEUP'
                elif full_seq == '\x1b[6':  # Page Down
                    try:
                        if select.select([sys.stdin], [], [], 0.1)[0]:
                            sys.stdin.read(1)  # Читаем ~
                    except:
                        pass
                    return 'PAGEDOWN'
                else:
                    return 'ESC'
            elif key == ' ':  # Пробел
                return 'SPACE'
            elif key == '\r' or key == '\n':  # Enter
                return 'ENTER'
            elif key == 'q' or key == 'Q':
                return 'QUIT'
            elif key == 'a' or key == 'A':
                return 'ALL'
            elif key == 'n' or key == 'N':
                return 'NONE'
            elif key == 'w' or key == 'W':  # WASD альтернатива
                return 'UP'
            elif key == 's' or key == 'S':
                return 'DOWN'
            elif key == 'j':  # Vim-style
                return 'DOWN'
            elif key == 'k':
                return 'UP'
            elif key == 'f' or key == 'F':
                return 'FIND'
            elif key == '+' or key == '=':
                return 'EXPAND'
            elif key == '-' or key == '_':
                return 'COLLAPSE'
            return key
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


class GitignoreHandler:
    """Обработчик .gitignore файлов"""
    
    @staticmethod
    def parse_gitignore(gitignore_path):
        """Парсит .gitignore файл и возвращает список паттернов"""
        patterns = []
        
        if not gitignore_path.exists():
            return patterns
        
        try:
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Пропускаем пустые строки и комментарии
                    if not line or line.startswith('#'):
                        continue
                    patterns.append(line)
        except Exception as e:
            print(f"Предупреждение: Не удалось прочитать .gitignore: {e}")
        
        return patterns

    @staticmethod
    def is_ignored_by_gitignore(file_path, root_path, gitignore_patterns):
        """Проверяет, игнорируется ли файл согласно .gitignore"""
        if not gitignore_patterns:
            return False
        
        # Получаем относительный путь от корня проекта
        try:
            rel_path = file_path.relative_to(root_path)
            rel_path_str = str(rel_path).replace('\\', '/')  # Нормализуем для Windows
        except ValueError:
            return False
        
        for pattern in gitignore_patterns:
            # Убираем ведущий слеш если есть
            if pattern.startswith('/'):
                pattern = pattern[1:]
            
            # Проверяем точное совпадение
            if rel_path_str == pattern:
                return True
            
            # Проверяем паттерн как glob
            if fnmatch.fnmatch(rel_path_str, pattern):
                return True
            
            # Проверяем каждую часть пути для паттернов типа "node_modules"
            path_parts = rel_path.parts
            for i in range(len(path_parts)):
                partial_path = '/'.join(path_parts[i:])
                if fnmatch.fnmatch(partial_path, pattern):
                    return True
                
                # Проверяем совпадение с отдельными частями
                if fnmatch.fnmatch(path_parts[i], pattern):
                    return True
            
            # Для директорий - проверяем паттерны с завершающим слешем
            if pattern.endswith('/'):
                dir_pattern = pattern[:-1]
                if any(fnmatch.fnmatch(part, dir_pattern) for part in path_parts):
                    return True
        
        return False


class FileFilters:
    """Класс для фильтрации файлов"""
    
    SKIP_DIRS = {'vendor', 'venv', '.git', '.vscode', '__pycache__', 'node_modules'}
    SKIP_FILES = {'.env', '.gitignore', '.DS_Store'}
    SKIP_EXTENSIONS = {'.pyc', '.pyo', '.log', '.tmp'}
    TEXT_EXTENSIONS = {
        '.py', '.php', '.js', '.html', '.css', '.sql', '.txt', '.md', 
        '.json', '.xml', '.yml', '.yaml', '.ini', '.conf', '.sh', 
        '.bat', '.dockerfile', '.gitignore', '.htaccess', '.vue', 
        '.ts', '.jsx', '.tsx', '.scss', '.less', '.go', '.java', 
        '.c', '.cpp', '.h', '.rb', '.pl', '.rs'
    }
    
    @classmethod
    def should_skip_directory(cls, dir_name):
        """Проверяет, нужно ли пропустить директорию"""
        return dir_name in cls.SKIP_DIRS

    @classmethod
    def should_skip_file(cls, file_path):
        """Проверяет, нужно ли пропустить файл"""
        file_name = file_path.name
        file_ext = file_path.suffix.lower()
        
        return (file_name in cls.SKIP_FILES or 
                file_ext in cls.SKIP_EXTENSIONS or
                file_name.startswith('.env'))

    @classmethod
    def is_text_file(cls, file_path):
        """Проверяет, является ли файл текстовым"""
        # Проверяем расширение
        if file_path.suffix.lower() in cls.TEXT_EXTENSIONS:
            return True
        
        # Проверяем файлы без расширения (возможно конфиги)
        if not file_path.suffix:
            try:
                with open(file_path, 'rb') as f:
                    chunk = f.read(1024)
                    # Проверяем, есть ли нулевые байты (признак бинарного файла)
                    return b'\x00' not in chunk
            except:
                return False
        
        return False


class CodeCollector:
    """Основной класс для сбора файлов проекта"""
    
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


class InteractiveSelector:
    """Интерактивный селектор файлов с деревом"""
    
    def __init__(self, files: List[Path], root_path: Path, saved_files=None, saved_folders=None):
        self.files = files
        self.root_path = root_path
        self.tree_root = self._build_file_tree()
        self.current_pos = 0
        self.page_size = 18
        self.current_page = 0
        self.search_term = ""
        
        # Применяем сохраненный выбор если есть
        if saved_files or saved_folders:
            self._apply_saved_selection(saved_files or [], saved_folders or [])
    
    def run(self) -> List[Path]:
        """Запускает интерактивный выбор"""
        if not self.files:
            print("Нет файлов для выбора!")
            return []
        
        print("\nЗапуск интерактивного выбора файлов...")
        input("Нажмите Enter для продолжения...")
        
        while True:
            self._display_tree()
            key = KeyboardHandler.get_key()
            
            if not self._handle_key(key):
                break
        
        return self.tree_root.get_selected_files()
    
    def _build_file_tree(self) -> TreeNode:
        """Строит дерево файлов из списка путей"""
        tree_root = TreeNode(self.root_path, is_file=False)
        tree_root.expanded = True
        
        for file_path in self.files:
            rel_path = file_path.relative_to(self.root_path)
            parts = rel_path.parts
            
            # Создаем путь для каждого уровня вложенности
            current_path = self.root_path
            current_node = tree_root
            
            # Проходим по всем частям пути кроме файла
            for i, part in enumerate(parts[:-1]):
                current_path = current_path / part
                
                # Ищем существующую папку среди детей
                existing_dir = None
                for child in current_node.children:
                    if not child.is_file and child.path.name == part:
                        existing_dir = child
                        break
                
                if existing_dir is None:
                    # Создаем новую папку
                    dir_node = TreeNode(current_path, is_file=False, parent=current_node)
                    current_node.children.append(dir_node)
                    current_node = dir_node
                else:
                    current_node = existing_dir
            
            # Добавляем файл
            file_node = TreeNode(file_path, is_file=True, parent=current_node)
            current_node.children.append(file_node)
        
        # Сортируем детей: папки сначала, потом файлы
        self._sort_tree_children(tree_root)
        return tree_root
    
    def _sort_tree_children(self, node):
        """Сортирует детей узла рекурсивно"""
        if not node.is_file:
            node.children.sort(key=lambda x: (x.is_file, x.path.name.lower()))
            for child in node.children:
                self._sort_tree_children(child)
    
    def _apply_saved_selection(self, saved_files, saved_folders):
        """Применяет сохраненный выбор к дереву файлов"""
        saved_files_set = set(saved_files)
        saved_folders_set = set(saved_folders)
        
        def mark_selected(node):
            if node.is_file:
                if node.path in saved_files_set:
                    node.selected = True
            else:
                if node.path in saved_folders_set:
                    node.set_selected_recursive(True)
                else:
                    for child in node.children:
                        mark_selected(child)
        
        mark_selected(self.tree_root)
    
    def _get_visible_nodes(self) -> List[Tuple[TreeNode, int]]:
        """Возвращает список видимых узлов для отображения"""
        visible = []
        
        def traverse(node, depth=0):
            if node != self.tree_root:  # Не показываем корневой узел
                visible.append((node, depth))
            
            if not node.is_file and node.expanded:
                for child in node.children:
                    traverse(child, depth + 1)
        
        traverse(self.tree_root)
        return visible
    
    def _display_tree(self):
        """Отображает дерево файлов"""
        os.system('cls' if os.name == 'nt' else 'clear')
        
        visible_nodes = self._get_visible_nodes()
        
        if not visible_nodes:
            print("Нет элементов для отображения!")
            input("Нажмите Enter...")
            return
        
        # Подсчитываем статистику
        all_files = self.tree_root.get_selected_files()
        total_files = self.tree_root.get_file_count()
        selected_files = len(all_files)
        
        total_pages = (len(visible_nodes) - 1) // self.page_size + 1 if visible_nodes else 1
        start_idx = self.current_page * self.page_size
        end_idx = min(start_idx + self.page_size, len(visible_nodes))
        
        # Заголовок
        print("╔" + "═" * 80 + "╗")
        print("║" + f"  ВЫБОР ФАЙЛОВ И ПАПОК ({selected_files}/{total_files} файлов выбрано)".ljust(78) + "║")
        print("║" + f"  Страница {self.current_page + 1}/{total_pages}".ljust(78) + "║")
        print("╠" + "═" * 80 + "╣")
        print("║" + "  ↑↓ - навигация, SPACE - выбор, →← - развернуть/свернуть".ljust(78) + "║")
        print("║" + "  A/N - всё/ничего, +/- - развернуть/свернуть все, F - поиск, Q - выход".ljust(78) + "║")
        print("╚" + "═" * 80 + "╝")
        print()
        
        if self.search_term:
            print(f"🔍 Поиск: '{self.search_term}' (ESC - очистить)")
            print()
        
        # Показываем узлы текущей страницы
        for i in range(start_idx, end_idx):
            if i >= len(visible_nodes):
                break
                
            node, depth = visible_nodes[i]
            cursor = "→" if i == self.current_pos else " "
            indent = "  " * depth
            
            if node.is_file:
                checkbox = "☑" if node.selected else "☐"
                name = node.get_display_name()
                max_name_len = 50 - len(indent)
                if len(name) > max_name_len:
                    name = name[:max_name_len-3] + "..."
                
                print(f"{cursor} {indent}📄 {checkbox} {name}")
            else:
                state = node.get_selection_state()
                if state == 'all':
                    checkbox = "☑"
                elif state == 'partial':
                    checkbox = "◑"
                else:
                    checkbox = "☐"
                
                expand_icon = "▼" if node.expanded else "▶"
                file_count = node.get_file_count()
                
                name = node.get_display_name()
                max_name_len = 35 - len(indent)
                if len(name) > max_name_len:
                    name = name[:max_name_len-3] + "..."
                
                print(f"{cursor} {indent}📁 {checkbox} {expand_icon} {name}/ ({file_count} файлов)")
        
        # Статистика внизу
        print(f"\nВыбрано: {selected_files} файлов")
        if self.current_pos < len(visible_nodes):
            current_node, _ = visible_nodes[self.current_pos]
            rel_path = current_node.path.relative_to(self.root_path)
            print(f"Текущий: {rel_path}")
    
    def _handle_key(self, key: str) -> bool:
        """Обрабатывает нажатие клавиши. Возвращает True для продолжения, False для выхода"""
        visible_nodes = self._get_visible_nodes()
        total_pages = (len(visible_nodes) - 1) // self.page_size + 1 if visible_nodes else 1
        
        if key == 'UP':
            if self.current_pos > 0:
                self.current_pos -= 1
                if self.current_pos < self.current_page * self.page_size:
                    self.current_page = max(0, self.current_page - 1)
        
        elif key == 'DOWN':
            if self.current_pos < len(visible_nodes) - 1:
                self.current_pos += 1
                if self.current_pos >= (self.current_page + 1) * self.page_size:
                    self.current_page = min(total_pages - 1, self.current_page + 1)
        
        elif key == 'SPACE':
            if self.current_pos < len(visible_nodes):
                current_node, _ = visible_nodes[self.current_pos]
                if current_node.is_file:
                    current_node.selected = not current_node.selected
                else:
                    # Переключаем всю папку
                    state = current_node.get_selection_state()
                    new_state = state != 'all'
                    current_node.set_selected_recursive(new_state)
        
        elif key == 'RIGHT':
            if self.current_pos < len(visible_nodes):
                current_node, _ = visible_nodes[self.current_pos]
                if not current_node.is_file:
                    current_node.expanded = True
        
        elif key == 'LEFT':
            if self.current_pos < len(visible_nodes):
                current_node, _ = visible_nodes[self.current_pos]
                if not current_node.is_file:
                    current_node.expanded = False
        
        elif key == 'EXPAND':
            # Развернуть все папки
            self._expand_all(self.tree_root)
        
        elif key == 'COLLAPSE':
            # Свернуть все папки кроме первого уровня
            self._collapse_all(self.tree_root)
        
        elif key == 'ENTER':
            return False  # Завершить выбор
        
        elif key == 'QUIT':
            print("\nОтмена операции.")
            self.tree_root.set_selected_recursive(False)  # Сбрасываем выбор
            return False
        
        elif key == 'ESC':
            if self.search_term:
                self.search_term = ""
            else:
                print("\nОтмена операции.")
                self.tree_root.set_selected_recursive(False)
                return False
        
        elif key == 'ALL':
            self.tree_root.set_selected_recursive(True)
        
        elif key == 'NONE':
            self.tree_root.set_selected_recursive(False)
        
        elif key == 'FIND':
            print("\nВведите поисковый запрос: ", end="", flush=True)
            self.search_term = input().strip()
        
        return True  # Продолжить работу
    
    def _expand_all(self, node: TreeNode):
        """Развернуть все папки рекурсивно"""
        if not node.is_file:
            node.expanded = True
            for child in node.children:
                self._expand_all(child)
    
    def _collapse_all(self, node: TreeNode, depth: int = 0):
        """Свернуть все папки кроме первого уровня"""
        if not node.is_file:
            node.expanded = depth == 0
            for child in node.children:
                self._collapse_all(child, depth + 1)


class OutputWriter(ABC):
    """Абстрактный класс для записи результатов"""
    
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
            except:
                return "[Ошибка чтения файла: неподдерживаемая кодировка]\n"


class MarkdownWriter(OutputWriter):
    """Записывает файлы в Markdown формате"""
    
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
            '.sql': 'sql',
            '.json': 'json',
            '.xml': 'xml',
            '.yml': 'yaml',
            '.yaml': 'yaml',
            '.md': 'markdown',
            '.sh': 'bash',
            '.bat': 'batch',
            '.dockerfile': 'dockerfile',
            '.go': 'go',
            '.java': 'java',
            '.c': 'c',
            '.cpp': 'cpp',
            '.rb': 'ruby',
            '.rs': 'rust'
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
    """Записывает файлы в обычном текстовом формате"""
    
    def write(self, files: List[Path], output_file: str):
        """Записывает файлы в текстовом формате"""
        with open(output_file, 'w', encoding='utf-8') as out_f:
            for file_path in sorted(files):
                try:
                    rel_path = file_path.relative_to(self.root_path)
                    out_f.write(f"# {rel_path}\n")
                    
                    content = self._read_file_content(file_path)
                    out_f.write(content)
                    out_f.write("\n\n")
                    
                    print(f"Обработан: {rel_path}")
                    
                except Exception as e:
                    print(f"Ошибка при обработке {file_path}: {e}")
                    continue


class ConfigManager:
    """Менеджер конфигурации приложения"""
    
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


class CodeCollectorApp:
    """Главный класс приложения"""
    
    def __init__(self):
        self.config = None
        self.project_settings = None
        self.collector = None
        
    def run(self) -> int:
        """Запускает приложение"""
        try:
            # Парсим CLI аргументы
            self.config = ConfigManager.parse_cli_args()
            
            # Определяем рабочую директорию
            source_dir = self._get_source_directory()
            source_path = Path(source_dir)
            
            if not self._validate_source_path(source_path):
                return 1
            
            # Инициализируем настройки проекта
            self.project_settings = ProjectSettings(source_path)
            
            # Объединяем конфигурацию с сохраненными настройками
            saved_settings_exist = self.project_settings.load_settings() is not None
            self.config = ConfigManager.merge_with_saved_settings(self.config, self.project_settings)
            
            # Интерактивная настройка недостающих параметров
            self.config = ConfigManager.interactive_config_setup(self.config, saved_settings_exist)
            
            # Показываем применяемую конфигурацию
            ConfigManager.show_applied_config(self.config, saved_settings_exist)
            
            # Инициализируем коллектор
            self.collector = CodeCollector(source_path, self.config)
            
            # Собираем файлы
            collected_files = self.collector.scan_and_collect()
            
            if not collected_files:
                print("Нет файлов для обработки!")
                return 0
            
            # Интерактивный выбор если нужно
            if self.config.interactive:
                selected_files = self._interactive_file_selection(collected_files, source_path)
                if not selected_files:
                    print("Файлы не выбраны. Операция отменена.")
                    return 0
                collected_files = selected_files
                
                # Сохраняем настройки
                self._save_user_preferences(collected_files)
            
            # Записываем результат
            self._write_output(collected_files, source_path)
            
            # Успешное завершение
            format_info = "Markdown" if self.config.markdown_format else "текстовом"
            structure_info = " со структурой" if self.config.show_structure else ""
            print(f"\nГотово! Результат сохранен в {format_info} формате{structure_info}: {self.config.output_file}")
            
            return 0
            
        except Exception as e:
            print(f"Ошибка: {e}")
            return 1
    
    def _get_source_directory(self) -> str:
        """Получает исходную директорию"""
        if self.config.source_dir:
            return self.config.source_dir
        
        source_dir = input("Введите путь к директории для сканирования (или Enter для текущей): ").strip()
        return source_dir if source_dir else os.getcwd()
    
    def _validate_source_path(self, source_path: Path) -> bool:
        """Валидирует исходный путь"""
        if not source_path.exists():
            print(f"Ошибка: Директория {source_path} не существует!")
            return False
        
        if not source_path.is_dir():
            print(f"Ошибка: {source_path} не является директорией!")
            return False
        
        return True
    
    def _interactive_file_selection(self, files: List[Path], root_path: Path) -> List[Path]:
        """Выполняет интерактивный выбор файлов"""
        # Загружаем сохраненный выбор
        saved_files = []
        saved_folders = []
        
        settings = self.project_settings.load_settings()
        if settings:
            saved_files, saved_folders = self.project_settings.filter_existing_paths(
                settings.get('selected_files', []),
                settings.get('selected_folders', [])
            )
        
        # Запускаем интерактивный селектор
        selector = InteractiveSelector(files, root_path, saved_files, saved_folders)
        selected_files = selector.run()
        
        if selected_files:
            print(f"\nВыбрано файлов для обработки: {len(selected_files)}")
        
        return selected_files
    
    def _save_user_preferences(self, selected_files: List[Path]):
        """Сохраняет пользовательские предпочтения"""
        # Для простоты пока не реализуем логику определения полностью выбранных папок
        selected_folders_paths = []
        
        preferences = {
            'markdown_format': self.config.markdown_format,
            'show_structure': self.config.show_structure,
            'sort_by_time': self.config.sort_by_time,
            'default_output': self.config.output_file
        }
        
        self.project_settings.save_settings(preferences, selected_files, selected_folders_paths)
    
    def _write_output(self, files: List[Path], root_path: Path):
        """Записывает результат в выходной файл"""
        if self.config.markdown_format:
            writer = MarkdownWriter(root_path, self.config.show_structure)
        else:
            writer = TextWriter(root_path)
        
        writer.write(files, self.config.output_file)


def main():
    """Главная функция"""
    app = CodeCollectorApp()
    return app.run()


if __name__ == "__main__":
    sys.exit(main())