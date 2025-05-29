#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import fnmatch
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

def interactive_tree_selector(files, root_path, sort_by_time=False):
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

def collect_files(root_dir, output_file):
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
            
def collect_files(root_dir, output_file, interactive=False, sort_by_time=False):
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
    
    # Интерактивный выбор файлов если нужно
    if interactive and collected_files:
        print("\nЗапуск интерактивного выбора файлов...")
        input("Нажмите Enter для продолжения...")
        selected_files = interactive_tree_selector(collected_files, root_path, sort_by_time)
        if not selected_files:
            print("Файлы не выбраны. Операция отменена.")
            return
        collected_files = selected_files
        print(f"\nВыбрано файлов для обработки: {len(collected_files)}")
    
    if not collected_files:
        print("Нет файлов для обработки!")
        return
    
    # Записываем все в выходной файл
    with open(output_file, 'w', encoding='utf-8') as out_f:
        for file_path in sorted(collected_files):
            try:
                # Получаем относительный путь
                rel_path = file_path.relative_to(root_path)
                
                # Записываем заголовок
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
                        out_f.write(f"[Ошибка чтения файла: неподдерживаемая кодировка]\n")
                
                # Добавляем разделитель между файлами
                out_f.write("\n\n")
                
                print(f"Обработан: {rel_path}")
                
            except Exception as e:
                print(f"Ошибка при обработке {file_path}: {e}")
                continue

def main():
    """Главная функция"""
    interactive_mode = False
    sort_by_time = False
    
    # Проверяем аргументы командной строки
    args_to_remove = []
    
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg in ['-i', '--interactive']:
            interactive_mode = True
            args_to_remove.append(i)
        elif arg in ['-t', '--time', '--sort-time']:
            sort_by_time = True
            args_to_remove.append(i)
    
    # Удаляем обработанные флаги
    for i in reversed(args_to_remove):
        sys.argv.pop(i)
    
    if len(sys.argv) > 1:
        source_dir = sys.argv[1]
    else:
        source_dir = input("Введите путь к директории для сканирования (или Enter для текущей): ").strip()
        if not source_dir:
            source_dir = "."
    
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    else:
        output_file = input("Введите имя выходного файла (по умолчанию 'collected_files.txt'): ").strip()
        if not output_file:
            output_file = "collected_files.txt"
    
    # Спрашиваем про интерактивный режим если не указан в аргументах
    if not interactive_mode:
        choice = input("Использовать интерактивный выбор файлов? (y/N): ").strip().lower()
        interactive_mode = choice in ['y', 'yes', 'д', 'да']
    
    # Спрашиваем про сортировку если не указана в аргументах
    if not sort_by_time:
        choice = input("Сортировать по времени изменения (новые сверху)? (y/N): ").strip().lower()
        sort_by_time = choice in ['y', 'yes', 'д', 'да']
    
    source_path = Path(source_dir)
    
    if not source_path.exists():
        print(f"Ошибка: Директория {source_dir} не существует!")
        return 1
    
    if not source_path.is_dir():
        print(f"Ошибка: {source_dir} не является директорией!")
        return 1
    
    try:
        collect_files(source_dir, output_file, interactive_mode, sort_by_time)
        print(f"\nГотово! Результат сохранен в: {output_file}")
        return 0
    except Exception as e:
        print(f"Ошибка: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())