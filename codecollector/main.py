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
from codecollector.writers import MarkdownWriter
from codecollector.utils import KeyboardHandler


class CodeCollectorApp:
    """
    Главный класс приложения CodeCollector
    Координирует работу всех компонентов с упрощенной логикой
    
    Атрибуты:
    - config: Config - конфигурация приложения
    - project_settings: ProjectSettings - настройки проекта
    - collector: CodeCollector - сборщик файлов
    
    Методы:
    - run() -> int: Главный метод запуска приложения
    - _determine_mode(saved_settings) -> str: Определяет режим работы
    - _get_source_directory() -> tuple: Получает исходную директорию
    - _validate_source_path(source_path, show_info) -> bool: Валидирует путь
    - _run_setup_wizard() -> Config: Мастер первоначальной настройки
    - _apply_quick_defaults() -> Config: Настройки для быстрого режима
    - _reset_project_settings(): Сбрасывает настройки проекта
    - _interactive_file_selection(files, root_path) -> List[Path]: Интерактивный выбор
    - _save_user_preferences(selected_files): Сохраняет настройки
    - _write_output(files, root_path): Записывает результат
    """
    
    def __init__(self):
        self.config: Config = None
        self.project_settings: ProjectSettings = None
        self.collector: CodeCollector = None
        
    def run(self) -> int:
        """Запускает приложение с упрощенной логикой"""
        try:
            print("🚀 CodeCollector")
            print("=" * 30)
            
            # 1. КОНФИГУРАЦИЯ
            self.config = ConfigManager.parse_cli_args()
            
            # Определяем рабочую директорию
            source_dir, showed_prompt = self._get_source_directory()
            source_path = Path(source_dir)
            
            if not self._validate_source_path(source_path, not showed_prompt):
                return 1
            
            # Инициализируем настройки проекта
            self.project_settings = ProjectSettings(source_path)
            saved_settings = self.project_settings.load_settings()
            
            # ОПРЕДЕЛЯЕМ РЕЖИМ РАБОТЫ
            mode = self._determine_mode(saved_settings)
            
            if mode == "FORCE_SETUP":
                # codecollector --setup
                self.config = self._run_setup_wizard()
                
            elif mode == "FORCE_QUICK":
                # codecollector --quick
                self.config = self._apply_quick_defaults()
                
            elif mode == "RESET_AND_SETUP":
                # codecollector --reset
                self._reset_project_settings()
                self.config = self._run_setup_wizard()
                
            elif mode == "QUICK_RUN":
                # ЕСТЬ НАСТРОЙКИ - СРАЗУ В ДЕРЕВО!
                self.config = ConfigManager.merge_with_saved_settings(self.config, self.project_settings)
                print(f"🔄 Проект '{saved_settings.get('project_name')}' | ", end="")
                
                # Показываем активные настройки одной строкой
                flags = []
                if self.config.sort_by_time:
                    flags.append("по времени")
                else:
                    flags.append("по имени")
                    
                if saved_settings.get('preferences', {}).get('interactive_mode', True):
                    flags.append("интерактивный")
                    self.config.interactive = True
                else:
                    flags.append("все файлы")
                    self.config.interactive = False
                    
                print(" + ".join(flags))
                
            else:
                # mode == "FIRST_TIME_SETUP"  
                self.config = self._run_setup_wizard()
            
            # 2. СБОР ФАЙЛОВ
            self.collector = CodeCollector(source_path, self.config)
            collected_files = self.collector.scan_and_collect()
            
            if not collected_files:
                print("❌ Нет файлов для обработки!")
                return 0
            
            # 3. ИНТЕРАКТИВНЫЙ ВЫБОР (если включен)
            if self.config.interactive:
                # СРАЗУ В ДЕРЕВО БЕЗ ЛИШНИХ ВОПРОСОВ
                selected_files = self._interactive_file_selection(collected_files, source_path)
                if not selected_files:
                    print("❌ Файлы не выбраны. Операция отменена.")
                    return 0
                collected_files = selected_files
            
            # 4. ЗАПИСЬ РЕЗУЛЬТАТА (жестко collected_files.md)
            self.config.output_file = "collected_files.md"
            self.config.markdown_format = True
            self.config.show_structure = True
            self._write_output(collected_files, source_path)
            
            # 5. СОХРАНЕНИЕ НАСТРОЕК
            self._save_user_preferences(collected_files)
            
            # 6. УСПЕШНОЕ ЗАВЕРШЕНИЕ
            print(f"✅ Готово! → collected_files.md")
            
            # Показываем размер файла
            try:
                file_size = Path("collected_files.md").stat().st_size
                if file_size > 1024 * 1024:
                    size_str = f"{file_size / (1024 * 1024):.1f} MB"
                elif file_size > 1024:
                    size_str = f"{file_size / 1024:.1f} KB"
                else:
                    size_str = f"{file_size} bytes"
                print(f"📊 Размер: {size_str}")
            except:
                pass
            
            return 0
            
        except KeyboardInterrupt:
            print("\n⚠️  Операция прервана")
            return 1
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            if "--debug" in sys.argv:
                import traceback
                traceback.print_exc()
            return 1
    
    def _determine_mode(self, saved_settings) -> str:
        """Определяет режим работы приложения"""
        if '--setup' in sys.argv:
            return "FORCE_SETUP"
        elif '--quick' in sys.argv:
            return "FORCE_QUICK"  
        elif '--reset' in sys.argv:
            return "RESET_AND_SETUP"
        elif saved_settings:
            return "QUICK_RUN"  # ЕСТЬ НАСТРОЙКИ = СРАЗУ РАБОТАТЬ
        else:
            return "FIRST_TIME_SETUP"
    
    def _get_source_directory(self) -> tuple[str, bool]:
        """Получает исходную директорию с флагом показа информации"""
        # Если директория уже указана в CLI
        if self.config.source_dir:
            return self.config.source_dir, False
        
        # Если НЕ удаленный режим, используем текущую директорию
        if not getattr(self.config, 'remote_mode', False):
            current_dir = os.getcwd()
            return current_dir, False
        
        # Только в удаленном режиме спрашиваем директорию
        print("📁 Выбор директории для сканирования")
        source_dir = input("Введите путь к директории (или Enter для текущей): ").strip()
        return (source_dir if source_dir else os.getcwd()), True
    
    def _validate_source_path(self, source_path: Path, show_info: bool = True) -> bool:
        """Валидирует исходный путь"""
        if not source_path.exists():
            print(f"❌ Ошибка: Директория {source_path} не существует!")
            return False
        
        if not source_path.is_dir():
            print(f"❌ Ошибка: {source_path} не является директорией!")
            return False
        
        # Показываем информацию только если нужно
        if show_info:
            print(f"✅ Рабочая директория: {source_path}")
        
        return True
    
    def _run_setup_wizard(self) -> Config:
        """Запускает мастер настройки (только для первого раза или --setup)"""
        print("🔧 Настройка проекта...")
        
        # Сортировка
        print("⏰ Сортировка файлов? [Enter=По времени / Esc=По имени]: ", end="", flush=True)
        key = KeyboardHandler.get_key()
        if key == 'ENTER':
            self.config.sort_by_time = True
            print("✅ ПО ВРЕМЕНИ")
        else:
            self.config.sort_by_time = False
            print("❌ ПО ИМЕНИ")
        
        # Интерактивный режим
        print("🎯 Выбор файлов? [Enter=Интерактивный / Esc=Все файлы]: ", end="", flush=True)
        key = KeyboardHandler.get_key()
        if key == 'ENTER':
            self.config.interactive = True
            print("✅ ИНТЕРАКТИВНЫЙ")
        else:
            self.config.interactive = False
            print("❌ ВСЕ ФАЙЛЫ")
        
        print("💾 Настройки сохранены")
        return self.config
    
    def _apply_quick_defaults(self) -> Config:
        """Применяет быстрые настройки по умолчанию"""
        print("⚡ Быстрый режим - все файлы")
        self.config.sort_by_time = False
        self.config.interactive = False
        self.config.markdown_format = True
        self.config.show_structure = True
        return self.config
    
    def _reset_project_settings(self):
        """Сбрасывает настройки проекта"""
        settings_file = self.project_settings.settings_file
        if settings_file.exists():
            settings_file.unlink()
            print("🗑️  Настройки проекта удалены")
    
    def _interactive_file_selection(self, files: List[Path], root_path: Path) -> List[Path]:
        """Выполняет интерактивный выбор с сохранением контекста"""
        
        # Загружаем сохраненный выбор
        saved_files = []
        saved_folders = []
        
        settings = self.project_settings.load_settings()
        if settings:
            saved_files, saved_folders = self.project_settings.filter_existing_paths(
                settings.get('selected_files', []),
                settings.get('selected_folders', [])
            )
        
        # Подготавливаем информацию о проекте для отображения
        project_info = {
            'name': self.project_settings.project_name,
            'settings': self._get_settings_string()
        }
        
        # Запускаем селектор с контекстом проекта
        selector = InteractiveSelector(files, root_path, saved_files, saved_folders, project_info)
        selected_files = selector.run()
        
        return selected_files
    
    def _get_settings_string(self) -> str:
        """Формирует строку с настройками проекта"""
        flags = []
        if self.config.sort_by_time:
            flags.append("по времени")
        else:
            flags.append("по имени")
        
        if self.config.interactive:
            flags.append("интерактивный")
        else:
            flags.append("все файлы")
        
        return " + ".join(flags)
    
    def _save_user_preferences(self, selected_files: List[Path]):
        """Сохраняет пользовательские предпочтения"""
        # Для простоты пока не реализуем логику определения полностью выбранных папок
        selected_folders_paths = []
        
        preferences = {
            'interactive_mode': self.config.interactive,
            'sort_by_time': self.config.sort_by_time,
            'markdown_format': self.config.markdown_format,
            'show_structure': self.config.show_structure,
        }
        
        self.project_settings.save_settings(preferences, selected_files, selected_folders_paths)
    
    def _write_output(self, files: List[Path], root_path: Path):
        """Записывает результат в выходной файл (всегда Markdown)"""
        writer = MarkdownWriter(root_path, self.config.show_structure)
        writer.write(files, self.config.output_file)


def show_help():
    """Показывает справку по использованию"""
    help_text = """
🚀 CodeCollector - Инструмент для сбора файлов кода в один документ

ИСПОЛЬЗОВАНИЕ:
  codecollector [ОПЦИИ] [ДИРЕКТОРИЯ]

ОПЦИИ:
  -r, --remote         Удаленный режим: спросить директорию для сканирования
  --setup              Принудительная настройка проекта заново
  --quick              Быстрый режим: все файлы без интерактивного выбора
  --reset              Сбросить настройки проекта и настроить заново
  
  --help, -h           Показать эту справку
  --debug              Включить отладочный режим

РЕЖИМЫ РАБОТЫ:
  По умолчанию: использует текущую директорию и сохраненные настройки
  С флагом -r: спрашивает какую директорию сканировать (удаленная работа)

ПРИМЕРЫ:
  codecollector                           # Текущая директория + сохраненные настройки
  codecollector --setup                  # Заново настроить проект
  codecollector --quick                  # Быстрый сбор всех файлов
  codecollector --reset                  # Сбросить и настроить заново
  codecollector -r                       # Спросить директорию для сканирования

ИНТЕРАКТИВНЫЙ РЕЖИМ:
  ↑↓ - навигация по дереву файлов
  SPACE - выбрать/снять выбор файла или папки
  →← - развернуть/свернуть папку
  A/N - выбрать всё/ничего
  +/- - развернуть/свернуть все папки
  R - сбросить весь выбор
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

ФОРМАТ ВЫВОДА:
  • Всегда: collected_files.md в Markdown формате
  • Подсветка синтаксиса для всех популярных языков
  • Структура проекта в виде дерева
  • Заголовки с путями к файлам
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