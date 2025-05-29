#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CodeCollector - Инструмент для сбора файлов кода в один документ
Главный модуль приложения и точка входа
"""

import os
import sys
from pathlib import Path
from typing import List

# Импорты модулей приложения
from codecollector.config import Config, ConfigManager
from codecollector.models import ProjectSettings
from codecollector.collector import CodeCollector
from codecollector.selector import InteractiveSelector
from codecollector.writers import MarkdownWriter, TextWriter


class CodeCollectorApp:
    """
    Главный класс приложения CodeCollector
    Координирует работу всех компонентов: конфигурацию, сбор файлов, интерактивный выбор, вывод
    
    Атрибуты:
    - config: Config - конфигурация приложения
    - project_settings: ProjectSettings - настройки проекта
    - collector: CodeCollector - сборщик файлов
    
    Методы:
    - run() -> int: Главный метод запуска приложения, возвращает код выхода
    - _get_source_directory() -> str: Получает исходную директорию
    - _validate_source_path(source_path) -> bool: Валидирует исходный путь
    - _interactive_file_selection(files, root_path) -> List[Path]: Интерактивный выбор
    - _save_user_preferences(selected_files): Сохраняет настройки пользователя
    - _write_output(files, root_path): Записывает результат в файл
    """
    
    def __init__(self):
        self.config: Config = None
        self.project_settings: ProjectSettings = None
        self.collector: CodeCollector = None
        
    def run(self) -> int:
        """Запускает приложение"""
        try:
            print("🚀 CodeCollector - Сборщик файлов кода")
            print("=" * 50)
            
            # 1. КОНФИГУРАЦИЯ
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
            print()
            
            # 2. СБОР ФАЙЛОВ
            # Инициализируем коллектор
            self.collector = CodeCollector(source_path, self.config)
            
            # Собираем файлы
            collected_files = self.collector.scan_and_collect()
            
            if not collected_files:
                print("❌ Нет файлов для обработки!")
                return 0
            
            print()
            
            # 3. ИНТЕРАКТИВНЫЙ ВЫБОР (если нужно)
            if self.config.interactive:
                selected_files = self._interactive_file_selection(collected_files, source_path)
                if not selected_files:
                    print("❌ Файлы не выбраны. Операция отменена.")
                    return 0
                collected_files = selected_files
                
                # Сохраняем настройки
                self._save_user_preferences(collected_files)
                print()
            
            # 4. ЗАПИСЬ РЕЗУЛЬТАТА
            print(f"📝 Обработка {len(collected_files)} файлов...")
            self._write_output(collected_files, source_path)
            
            # 5. УСПЕШНОЕ ЗАВЕРШЕНИЕ
            format_info = "Markdown" if self.config.markdown_format else "текстовом"
            structure_info = " со структурой" if self.config.show_structure else ""
            print(f"\n✅ Готово! Результат сохранен в {format_info} формате{structure_info}:")
            print(f"📄 {self.config.output_file}")
            
            # Показываем размер файла
            try:
                file_size = Path(self.config.output_file).stat().st_size
                if file_size > 1024 * 1024:
                    size_str = f"{file_size / (1024 * 1024):.1f} MB"
                elif file_size > 1024:
                    size_str = f"{file_size / 1024:.1f} KB"
                else:
                    size_str = f"{file_size} bytes"
                print(f"📊 Размер файла: {size_str}")
            except:
                pass
            
            return 0
            
        except KeyboardInterrupt:
            print("\n⚠️  Операция прервана пользователем")
            return 1
        except Exception as e:
            print(f"❌ Критическая ошибка: {e}")
            if "--debug" in sys.argv:
                import traceback
                traceback.print_exc()
            return 1
    
    def _get_source_directory(self) -> str:
        """Получает исходную директорию"""
        if self.config.source_dir:
            return self.config.source_dir
        
        print("📁 Выбор директории для сканирования")
        source_dir = input("Введите путь к директории (или Enter для текущей): ").strip()
        return source_dir if source_dir else os.getcwd()
    
    def _validate_source_path(self, source_path: Path) -> bool:
        """Валидирует исходный путь"""
        if not source_path.exists():
            print(f"❌ Ошибка: Директория {source_path} не существует!")
            return False
        
        if not source_path.is_dir():
            print(f"❌ Ошибка: {source_path} не является директорией!")
            return False
        
        print(f"✅ Рабочая директория: {source_path}")
        return True
    
    def _interactive_file_selection(self, files: List[Path], root_path: Path) -> List[Path]:
        """Выполняет интерактивный выбор файлов"""
        print("🎯 Интерактивный выбор файлов")
        
        # Загружаем сохраненный выбор
        saved_files = []
        saved_folders = []
        
        settings = self.project_settings.load_settings()
        if settings:
            saved_files, saved_folders = self.project_settings.filter_existing_paths(
                settings.get('selected_files', []),
                settings.get('selected_folders', [])
            )
            if saved_files or saved_folders:
                print(f"📋 Восстановлен предыдущий выбор: {len(saved_files)} файлов")
        
        # Запускаем интерактивный селектор
        selector = InteractiveSelector(files, root_path, saved_files, saved_folders)
        selected_files = selector.run()
        
        if selected_files:
            print(f"✅ Выбрано файлов для обработки: {len(selected_files)}")
        
        return selected_files
    
    def _save_user_preferences(self, selected_files: List[Path]):
        """Сохраняет пользовательские предпочтения"""
        # Для простоты пока не реализуем логику определения полностью выбранных папок
        # Это можно добавить позже для оптимизации
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


def show_help():
    """Показывает справку по использованию"""
    help_text = """
🚀 CodeCollector - Инструмент для сбора файлов кода в один документ

ИСПОЛЬЗОВАНИЕ:
  codecollector [ОПЦИИ] [ДИРЕКТОРИЯ] [ВЫХОДНОЙ_ФАЙЛ]

ОПЦИИ:
  -i, --interactive     Интерактивный выбор файлов через древовидный интерфейс
  -t, --time           Сортировать файлы по времени изменения (новые сверху)
  -m, --markdown       Использовать Markdown формат с подсветкой синтаксиса
  -s, --structure      Включить структуру проекта в вывод (только с -m)
  
  --no-time            Отключить сортировку по времени (сортировать по имени)
  --no-markdown        Использовать простой текстовый формат
  --no-structure       Не включать структуру проекта
  
  --help, -h           Показать эту справку
  --debug              Включить отладочный режим

ПРИМЕРЫ:
  codecollector                           # Базовый запуск
  codecollector -i -m -s                 # Интерактивный выбор, Markdown со структурой
  codecollector -t ./src output.md       # Сортировка по времени, указанная папка
  codecollector --no-markdown -i         # Текстовый формат, интерактивный выбор

ИНТЕРАКТИВНЫЙ РЕЖИМ:
  ↑↓ - навигация по дереву файлов
  SPACE - выбрать/снять выбор файла или папки
  →← - развернуть/свернуть папку
  A/N - выбрать всё/ничего
  +/- - развернуть/свернуть все папки
  F - поиск (в разработке)
  Q/ESC - выход
  ENTER - подтвердить выбор

НАСТРОЙКИ ПРОЕКТА:
  Настройки сохраняются в .codecollector/<имя_проекта>.json
  Включают предпочтения пользователя и последний выбор файлов
  Автоматически добавляется в .gitignore

ФИЛЬТРАЦИЯ:
  • Учитывает .gitignore файлы
  • Пропускает системные папки (node_modules, __pycache__, .git и т.д.)
  • Обрабатывает только текстовые файлы кода
  • Игнорирует пустые файлы и бинарные данные

ФОРМАТЫ ВЫВОДА:
  • Текстовый: простой формат для максимальной совместимости
  • Markdown: богатый формат с подсветкой синтаксиса и структурой проекта
"""
    print(help_text)


def main():
    """Главная функция - точка входа в приложение"""
    # Проверяем запрос справки
    if any(arg in sys.argv for arg in ['--help', '-h', 'help']):
        show_help()
        return 0
    
    # Запускаем приложение
    app = CodeCollectorApp()
    return app.run()


if __name__ == "__main__":
    sys.exit(main())