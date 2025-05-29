#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Утилиты для CodeCollector
Независимые классы для обработки ввода, фильтрации файлов и .gitignore
"""

import os
import sys
import fnmatch
from pathlib import Path

# Импорты для кроссплатформенного ввода
try:
    import msvcrt  # Windows
    WINDOWS = True
except ImportError:
    import termios, tty, select  # Unix/Linux/Mac
    WINDOWS = False


class KeyboardHandler:
    """
    Обработчик ввода с клавиатуры (кроссплатформенный)
    
    Методы:
    - get_key() -> str: Получает нажатую клавишу без Enter
    - _get_key_windows() -> str: Windows-специфичная обработка
    - _get_key_unix() -> str: Unix/Linux/Mac обработка
    """
    
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
    """
    Обработчик .gitignore файлов
    
    Методы:
    - parse_gitignore(gitignore_path) -> List[str]: Парсит .gitignore в список паттернов
    - is_ignored_by_gitignore(file_path, root_path, patterns) -> bool: Проверяет игнорирование файла
    """
    
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
    """
    Класс для фильтрации файлов по типам и паттернам
    
    Константы:
    - SKIP_DIRS: набор директорий для пропуска
    - SKIP_FILES: набор файлов для пропуска  
    - SKIP_EXTENSIONS: набор расширений для пропуска
    - TEXT_EXTENSIONS: набор текстовых расширений
    
    Методы:
    - should_skip_directory(dir_name) -> bool: Проверка пропуска директории
    - should_skip_file(file_path) -> bool: Проверка пропуска файла
    - is_text_file(file_path) -> bool: Проверка текстового файла
    """
    
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