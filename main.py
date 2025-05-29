#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import fnmatch
import datetime
import json
from pathlib import Path
from collections import defaultdict

# Для интерактивного выбора
try:
    import msvcrt  # Windows
    WINDOWS = True
except ImportError:
    import termios, tty, select  # Unix/Linux/Mac
    WINDOWS = False

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

def get_key():
    """Получает нажатую клавишу без Enter (кроссплатформенно)"""
    if WINDOWS:
        # Windows
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
    else:
        # Unix/Linux/Mac
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
                elif full_seq == '\x1b[5':  # Page Up (может потребоваться еще символ)
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

def clear_screen():
    """Очищает экран"""
    os.system('cls' if os.name == 'nt' else 'clear')

def build_file_tree(files, root_path):
    """Строит дерево файлов из списка путей"""
    tree_root = TreeNode(root_path, is_file=False)
    tree_root.expanded = True
    
    # Группируем файлы по директориям
    dir_structure = defaultdict(list)
    
    for file_path in files:
        rel_path = file_path.relative_to(root_path)
        parts = rel_path.parts
        
        # Создаем путь для каждого уровня вложенности
        current_path = root_path
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
    def sort_children(node):
        if not node.is_file:
            node.children.sort(key=lambda x: (x.is_file, x.path.name.lower()))
            for child in node.children:
                sort_children(child)
    
    sort_children(tree_root)
    return tree_root

def apply_saved_selection(tree_root, saved_files, saved_folders, root_path):
    """Применяет сохраненный выбор к дереву файлов"""
    # Преобразуем сохраненные пути в множества для быстрого поиска
    saved_files_set = set(saved_files)
    saved_folders_set = set(saved_folders)
    
    def mark_selected(node):
        if node.is_file:
            # Проверяем файл
            if node.path in saved_files_set:
                node.selected = True
        else:
            # Проверяем папку
            if node.path in saved_folders_set:
                node.set_selected_recursive(True)
            else:
                # Рекурсивно обрабатываем детей
                for child in node.children:
                    mark_selected(child)
    
    mark_selected(tree_root)

def get_visible_nodes(tree_root):
    """Возвращает список видимых узлов для отображения"""
    visible = []
    
    def traverse(node, depth=0):
        if node != tree_root:  # Не показываем корневой узел
            visible.append((node, depth))
        
        if not node.is_file and node.expanded:
            for child in node.children:
                traverse(child, depth + 1)
    
    traverse(tree_root)
    return visible

def interactive_tree_selector(files, root_path, sort_by_time=False, saved_files=None, saved_folders=None):
    """Интерактивный выбор файлов с иерархическим деревом"""
    if not files:
        print("Нет файлов для выбора!")
        return []
    
    # Сортируем файлы если нужно
    if sort_by_time:
        files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    else:
        files.sort()
    
    # Строим дерево
    tree_root = build_file_tree(files, root_path)
    
    # Применяем сохраненный выбор если есть
    if saved_files or saved_folders:
        apply_saved_selection(tree_root, saved_files or [], saved_folders or [], root_path)
    
    current_pos = 0
    page_size = 18
    current_page = 0
    search_term = ""
    
    while True:
        clear_screen()
        
        # Получаем видимые узлы
        visible_nodes = get_visible_nodes(tree_root)
        
        if not visible_nodes:
            print("Нет элементов для отображения!")
            input("Нажмите Enter...")
            continue
        
        # Подсчитываем статистику
        all_files = tree_root.get_selected_files()
        total_files = tree_root.get_file_count()
        selected_files = len(all_files)
        
        total_pages = (len(visible_nodes) - 1) // page_size + 1 if visible_nodes else 1
        start_idx = current_page * page_size
        end_idx = min(start_idx + page_size, len(visible_nodes))
        
        sort_info = "по времени (новые ↑)" if sort_by_time else "по имени"
        
        print("╔" + "═" * 80 + "╗")
        print("║" + f"  ВЫБОР ФАЙЛОВ И ПАПОК ({selected_files}/{total_files} файлов выбрано)".ljust(78) + "║")
        print("║" + f"  Страница {current_page + 1}/{total_pages} | Сортировка: {sort_info}".ljust(78) + "║")
        print("╠" + "═" * 80 + "╣")
        print("║" + "  ↑↓ - навигация, SPACE - выбор, →← - развернуть/свернуть".ljust(78) + "║")
        print("║" + "  A/N - всё/ничего, +/- - развернуть/свернуть все, F - поиск, Q - выход".ljust(78) + "║")
        print("╚" + "═" * 80 + "╝")
        print()
        
        if search_term:
            print(f"🔍 Поиск: '{search_term}' (ESC - очистить)")
            print()
        
        # Показываем узлы текущей страницы
        for i in range(start_idx, end_idx):
            if i >= len(visible_nodes):
                break
                
            node, depth = visible_nodes[i]
            cursor = "→" if i == current_pos else " "
            
            # Отступы для показа вложенности
            indent = "  " * depth
            
            if node.is_file:
                # Файл
                checkbox = "☑" if node.selected else "☐"
                icon = "📄"
                
                # Время модификации если нужно
                time_info = ""
                if sort_by_time:
                    try:
                        mtime = node.path.stat().st_mtime
                        import datetime
                        dt = datetime.datetime.fromtimestamp(mtime)
                        time_info = f" [{dt.strftime('%d.%m %H:%M')}]"
                    except:
                        time_info = " [??]"
                
                name = node.get_display_name()
                max_name_len = 50 - len(indent) - (12 if sort_by_time else 0)
                if len(name) > max_name_len:
                    name = name[:max_name_len-3] + "..."
                
                print(f"{cursor} {indent}📄 {checkbox} {name}{time_info}")
            else:
                # Папка
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
        if current_pos < len(visible_nodes):
            current_node, _ = visible_nodes[current_pos]
            rel_path = current_node.path.relative_to(root_path)
            print(f"Текущий: {rel_path}")
        
        # Получаем ввод пользователя
        key = get_key()
        
        if key == 'UP':
            if current_pos > 0:
                current_pos -= 1
                if current_pos < current_page * page_size:
                    current_page = max(0, current_page - 1)
        
        elif key == 'DOWN':
            if current_pos < len(visible_nodes) - 1:
                current_pos += 1
                if current_pos >= (current_page + 1) * page_size:
                    current_page = min(total_pages - 1, current_page + 1)
        
        elif key == 'SPACE':
            if current_pos < len(visible_nodes):
                current_node, _ = visible_nodes[current_pos]
                if current_node.is_file:
                    current_node.selected = not current_node.selected
                else:
                    # Переключаем всю папку
                    state = current_node.get_selection_state()
                    new_state = state != 'all'
                    current_node.set_selected_recursive(new_state)
        
        elif key == 'RIGHT':
            if current_pos < len(visible_nodes):
                current_node, _ = visible_nodes[current_pos]
                if not current_node.is_file:
                    current_node.expanded = True
        
        elif key == 'LEFT':
            if current_pos < len(visible_nodes):
                current_node, _ = visible_nodes[current_pos]
                if not current_node.is_file:
                    current_node.expanded = False
        
        elif key == 'EXPAND':
            # Развернуть все папки
            def expand_all(node):
                if not node.is_file:
                    node.expanded = True
                    for child in node.children:
                        expand_all(child)
            expand_all(tree_root)
        
        elif key == 'COLLAPSE':
            # Свернуть все папки кроме первого уровня
            def collapse_all(node, depth=0):
                if not node.is_file:
                    node.expanded = depth == 0
                    for child in node.children:
                        collapse_all(child, depth + 1)
            collapse_all(tree_root)
        
        elif key == 'ENTER':
            break
        
        elif key == 'QUIT' or key == 'ESC':
            if search_term:
                search_term = ""
            else:
                print("\nОтмена операции.")
                return []
        
        elif key == 'ALL':
            tree_root.set_selected_recursive(True)
        
        elif key == 'NONE':
            tree_root.set_selected_recursive(False)
        
        elif key == 'FIND':
            print("\nВведите поисковый запрос: ", end="", flush=True)
            search_term = input().strip()
    
    return tree_root.get_selected_files()

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

def should_skip_directory(dir_name):
    """Проверяет, нужно ли пропустить директорию"""
    skip_dirs = {'vendor', 'venv', '.git', '.vscode', '__pycache__', 'node_modules'}
    return dir_name in skip_dirs

def should_skip_file(file_path):
    """Проверяет, нужно ли пропустить файл"""
    skip_files = {'.env', '.gitignore', '.DS_Store'}
    skip_extensions = {'.pyc', '.pyo', '.log', '.tmp'}
    
    file_name = file_path.name
    file_ext = file_path.suffix.lower()
    
    return (file_name in skip_files or 
            file_ext in skip_extensions or
            file_name.startswith('.env'))

def is_text_file(file_path):
    """Проверяет, является ли файл текстовым"""
    text_extensions = {
        '.py', '.php', '.js', '.html', '.css', '.sql', '.txt', '.md', 
        '.json', '.xml', '.yml', '.yaml', '.ini', '.conf', '.sh', 
        '.bat', '.dockerfile', '.gitignore', '.htaccess', '.vue', 
        '.ts', '.jsx', '.tsx', '.scss', '.less', '.go', '.java', 
        '.c', '.cpp', '.h', '.rb', '.pl', '.rs'
    }
    
    # Проверяем расширение
    if file_path.suffix.lower() in text_extensions:
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

def collect_files(root_dir, output_file, interactive=False, sort_by_time=False, markdown_format=False, show_structure=False, project_settings=None):
    """Собирает все файлы в один текстовый файл"""
    root_path = Path(root_dir).resolve()
    collected_files = []
    
    print(f"Сканирование директории: {root_path}")
    
    # Читаем .gitignore файлы
    gitignore_patterns = []
    
    # Основной .gitignore в корне проекта
    main_gitignore = root_path / '.gitignore'
    gitignore_patterns.extend(parse_gitignore(main_gitignore))
    
    # Можно добавить поддержку .gitignore в подпапках, но обычно используется только корневой
    print(f"Загружено паттернов из .gitignore: {len(gitignore_patterns)}")
    if gitignore_patterns:
        print("Паттерны:", gitignore_patterns[:5], "..." if len(gitignore_patterns) > 5 else "")
    
    # Рекурсивно обходим все файлы
    for file_path in root_path.rglob('*'):
        # Пропускаем директории
        if file_path.is_dir():
            continue
        
        # Проверяем .gitignore паттерны
        if is_ignored_by_gitignore(file_path, root_path, gitignore_patterns):
            continue
            
        # Проверяем, не находится ли файл в исключаемой директории
        skip_dir = False
        for parent in file_path.parents:
            if should_skip_directory(parent.name):
                skip_dir = True
                break
        
        if skip_dir:
            continue
            
        # Пропускаем файлы по маске
        if should_skip_file(file_path):
            continue
            
        # Проверяем, что файл текстовый
        if not is_text_file(file_path):
            continue
            
        # Проверяем, что файл не пустой
        try:
            if file_path.stat().st_size == 0:
                continue
        except OSError:
            continue
            
        collected_files.append(file_path)
    
    print(f"Найдено файлов: {len(collected_files)}")
    
    # Сортировка файлов
    if sort_by_time:
        print("Сортировка по времени изменения (новые сверху)...")
        collected_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    else:
        print("Сортировка по имени файла...")
        collected_files.sort()
    
    # Загружаем сохраненные настройки если есть
    saved_files = []
    saved_folders = []
    if project_settings:
        settings = project_settings.load_settings()
        if settings:
            # Фильтруем существующие пути
            saved_files, saved_folders = project_settings.filter_existing_paths(
                settings.get('selected_files', []),
                settings.get('selected_folders', [])
            )
    
    # Интерактивный выбор файлов если нужно
    if interactive and collected_files:
        print("\nЗапуск интерактивного выбора файлов...")
        input("Нажмите Enter для продолжения...")
        selected_files = interactive_tree_selector(
            collected_files, root_path, sort_by_time, saved_files, saved_folders
        )
        if not selected_files:
            print("Файлы не выбраны. Операция отменена.")
            return
        collected_files = selected_files
        print(f"\nВыбрано файлов для обработки: {len(collected_files)}")
        
        # Сохраняем выбор пользователя
        if project_settings:
            # Определяем выбранные папки (папки где выбраны ВСЕ файлы)
            selected_folders_paths = []
            # Для простоты пока не реализуем логику определения полностью выбранных папок
            # Это можно добавить позже для оптимизации
            
            preferences = {
                'markdown_format': markdown_format,
                'show_structure': show_structure,
                'sort_by_time': sort_by_time,
                'default_output': output_file
            }
            
            project_settings.save_settings(preferences, collected_files, selected_folders_paths)
    
    if not collected_files:
        print("Нет файлов для обработки!")
        return
    
    # Записываем все в выходной файл
    write_output_file(collected_files, root_path, output_file, markdown_format, show_structure)

def write_output_file(files, root_path, output_file, markdown_format=False, show_structure=False):
    """Записывает файлы в выходной файл в указанном формате"""
    with open(output_file, 'w', encoding='utf-8') as out_f:
        if markdown_format:
            # Заголовок для markdown
            project_name = root_path.name
            out_f.write(f"# CodeCollector - {project_name}\n\n")
            out_f.write(f"**Собрано файлов:** {len(files)}  \n")
            out_f.write(f"**Дата сбора:** {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')}  \n")
            out_f.write(f"**Путь:** `{root_path}`\n\n")
            
            # Структура проекта если нужно
            if show_structure:
                out_f.write("## 📁 Структура проекта\n\n")
                structure = generate_project_structure(files, root_path)
                out_f.write("```\n")
                out_f.write(structure)
                out_f.write("```\n\n")
            
            out_f.write("---\n\n")
            out_f.write("## 📄 Содержимое файлов\n\n")
        
        for file_path in sorted(files):
            try:
                # Получаем относительный путь
                rel_path = file_path.relative_to(root_path)
                
                if markdown_format:
                    # Markdown формат
                    out_f.write(f"### `{rel_path}`\n\n")
                    
                    # Определяем язык для подсветки синтаксиса
                    extension = file_path.suffix.lower()
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
                    
                    lang = language_map.get(extension, '')
                    out_f.write(f"```{lang}\n")
                else:
                    # Обычный текстовый формат
                    out_f.write(f"# {rel_path}\n")
                
                # Записываем содержимое файла
                try:
                    with open(file_path, 'r', encoding='utf-8') as in_f:
                        content = in_f.read()
                        out_f.write(content)
                except UnicodeDecodeError:
                    # Пытаемся прочитать в другой кодировке
                    try:
                        with open(file_path, 'r', encoding='cp1251') as in_f:
                            content = in_f.read()
                            out_f.write(content)
                    except:
                        error_msg = "[Ошибка чтения файла: неподдерживаемая кодировка]"
                        out_f.write(error_msg + "\n")
                
                if markdown_format:
                    out_f.write("\n```\n\n")
                else:
                    out_f.write("\n\n")
                
                print(f"Обработан: {rel_path}")
                
            except Exception as e:
                print(f"Ошибка при обработке {file_path}: {e}")
                continue

def generate_project_structure(files, root_path):
    """Генерирует древовидную структуру проекта"""
    # Группируем файлы по папкам
    structure = {}
    
    for file_path in files:
        rel_path = file_path.relative_to(root_path)
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
    def build_tree_text(node_dict, prefix="", is_last=True):
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
                children_text = build_tree_text(info['_children'], next_prefix, is_last_item)
                result.extend(children_text)
        
        return result
    
    tree_lines = [f"{root_path.name}/"]
    tree_lines.extend(build_tree_text(structure['_children'] if '_children' in structure else structure))
    
    return "\n".join(tree_lines)

def parse_arguments():
    """Парсит аргументы командной строки с поддержкой негативных флагов"""
    args = {
        'interactive': False,
        'sort_by_time': False,
        'markdown_format': False,
        'show_structure': False,
        'source_dir': None,
        'output_file': None
    }
    
    # Обрабатываем аргументы
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        
        if arg in ['-i', '--interactive']:
            args['interactive'] = True
        elif arg in ['-t', '--time', '--sort-time']:
            args['sort_by_time'] = True
        elif arg in ['--no-time']:
            args['sort_by_time'] = False
        elif arg in ['-m', '--markdown']:
            args['markdown_format'] = True
        elif arg in ['--no-markdown']:
            args['markdown_format'] = False
        elif arg in ['-s', '--structure']:
            args['show_structure'] = True
        elif arg in ['--no-structure']:
            args['show_structure'] = False
        elif not arg.startswith('-'):
            # Позиционные аргументы
            if args['source_dir'] is None:
                args['source_dir'] = arg
            elif args['output_file'] is None:
                args['output_file'] = arg
        
        i += 1
    
    return args

def show_applied_flags(preferences, from_settings=False):
    """Показывает применяемые флаги"""
    flags = []
    
    if preferences.get('sort_by_time', False):
        flags.append('-t')
    if preferences.get('markdown_format', False):
        flags.append('-m')
    if preferences.get('show_structure', False):
        flags.append('-s')
    
    if flags:
        flag_str = ' '.join(flags)
        source = "сохраненные настройки" if from_settings else "CLI аргументы"
        print(f"📋 Применяемые флаги: {flag_str} ({source})")
    else:
        print("📋 Используются настройки по умолчанию")

def main():
    """Главная функция"""
    # Парсим CLI аргументы
    cli_args = parse_arguments()
    
    # Определяем рабочую директорию
    if cli_args['source_dir']:
        source_dir = cli_args['source_dir']
    else:
        source_dir = input("Введите путь к директории для сканирования (или Enter для текущей): ").strip()
        if not source_dir:
            source_dir = "."
    
    source_path = Path(source_dir)
    
    if not source_path.exists():
        print(f"Ошибка: Директория {source_dir} не существует!")
        return 1
    
    if not source_path.is_dir():
        print(f"Ошибка: {source_dir} не является директорией!")
        return 1
    
    # Инициализируем настройки проекта
    project_settings = ProjectSettings(source_path)
    
    # Загружаем сохраненные настройки
    saved_settings = project_settings.load_settings()
    saved_preferences = {}
    
    if saved_settings:
        saved_preferences = saved_settings.get('preferences', {})
        print(f"🔄 Загружены настройки проекта '{saved_settings.get('project_name', 'Unknown')}'")
    
    # Объединяем настройки: CLI флаги > сохраненные настройки > defaults
    final_preferences = {
        'interactive': cli_args['interactive'],  # interactive не сохраняется
        'sort_by_time': cli_args['sort_by_time'] if 'sort_by_time' in sys.argv else saved_preferences.get('sort_by_time', False),
        'markdown_format': cli_args['markdown_format'] if any(arg in sys.argv for arg in ['-m', '--markdown', '--no-markdown']) else saved_preferences.get('markdown_format', False),
        'show_structure': cli_args['show_structure'] if any(arg in sys.argv for arg in ['-s', '--structure', '--no-structure']) else saved_preferences.get('show_structure', False)
    }
    
    # Определяем выходной файл
    if cli_args['output_file']:
        output_file = cli_args['output_file']
    else:
        # Используем сохраненное имя файла или спрашиваем у пользователя
        default_output = saved_preferences.get('default_output')
        if not default_output:
            default_ext = ".md" if final_preferences['markdown_format'] else ".txt"
            default_output = f"collected_files{default_ext}"
        
        output_file = input(f"Введите имя выходного файла (по умолчанию '{default_output}'): ").strip()
        if not output_file:
            output_file = default_output
    
    # Показываем применяемые флаги
    show_applied_flags(final_preferences, bool(saved_settings))
    
    # Спрашиваем про недостающие опции если они не были указаны
    if not final_preferences['interactive'] and '--interactive' not in sys.argv and '-i' not in sys.argv:
        choice = input("Использовать интерактивный выбор файлов? (y/N): ").strip().lower()
        final_preferences['interactive'] = choice in ['y', 'yes', 'д', 'да']
    
    # Если флаги не были указаны в CLI и нет сохраненных настроек, спрашиваем
    if not saved_settings:
        if 'sort_by_time' not in [arg.replace('--', '').replace('-', '_') for arg in sys.argv]:
            choice = input("Сортировать по времени изменения (новые сверху)? (y/N): ").strip().lower()
            final_preferences['sort_by_time'] = choice in ['y', 'yes', 'д', 'да']
        
        if not any(arg in sys.argv for arg in ['-m', '--markdown', '--no-markdown']):
            choice = input("Использовать Markdown формат? (y/N): ").strip().lower()
            final_preferences['markdown_format'] = choice in ['y', 'yes', 'д', 'да']
            
            if final_preferences['markdown_format'] and not any(arg in sys.argv for arg in ['-s', '--structure', '--no-structure']):
                choice = input("Включить структуру проекта? (y/N): ").strip().lower()
                final_preferences['show_structure'] = choice in ['y', 'yes', 'д', 'да']
    
    try:
        collect_files(
            source_dir, 
            output_file, 
            final_preferences['interactive'], 
            final_preferences['sort_by_time'], 
            final_preferences['markdown_format'], 
            final_preferences['show_structure'],
            project_settings
        )
        
        format_info = "Markdown" if final_preferences['markdown_format'] else "текстовом"
        structure_info = " со структурой" if final_preferences['show_structure'] else ""
        print(f"\nГотово! Результат сохранен в {format_info} формате{structure_info}: {output_file}")
        return 0
        
    except Exception as e:
        print(f"Ошибка: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())