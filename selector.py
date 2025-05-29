#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Интерактивный селектор файлов с древовидным интерфейсом
InteractiveSelector - UI для выбора файлов и папок в виде дерева
"""

import os
from pathlib import Path
from typing import List, Tuple, Optional
from models import TreeNode
from utils import KeyboardHandler


class InteractiveSelector:
    """
    Интерактивный селектор файлов с деревом
    Строит дерево файлов, отображает в консоли, обрабатывает навигацию и выбор
    
    Атрибуты:
    - files: List[Path] - список всех файлов для выбора
    - root_path: Path - корневой путь проекта
    - tree_root: TreeNode - корень дерева файлов
    - current_pos: int - текущая позиция курсора
    - page_size: int - размер страницы (файлов на экране)
    - current_page: int - текущая страница
    - search_term: str - поисковый запрос
    
    Методы:
    - run() -> List[Path]: Запускает интерактивный выбор, возвращает выбранные файлы
    - _build_file_tree() -> TreeNode: Строит дерево из списка файлов
    - _apply_saved_selection(saved_files, saved_folders): Применяет сохраненный выбор
    - _get_visible_nodes() -> List[Tuple[TreeNode, int]]: Возвращает видимые узлы для отображения
    - _display_tree(): Отображает дерево в консоли
    - _handle_key(key) -> bool: Обрабатывает нажатия клавиш
    - _sort_tree_children(node): Сортирует детей узла рекурсивно
    - _expand_all(node): Развернуть все папки
    - _collapse_all(node, depth): Свернуть все папки кроме первого уровня
    """
    
    def __init__(self, files: List[Path], root_path: Path, saved_files: Optional[List[Path]] = None, saved_folders: Optional[List[Path]] = None):
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
    
    def _sort_tree_children(self, node: TreeNode):
        """Сортирует детей узла рекурсивно"""
        if not node.is_file:
            node.children.sort(key=lambda x: (x.is_file, x.path.name.lower()))
            for child in node.children:
                self._sort_tree_children(child)
    
    def _apply_saved_selection(self, saved_files: List[Path], saved_folders: List[Path]):
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