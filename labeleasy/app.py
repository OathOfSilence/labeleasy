# -*- coding: utf-8 -*-
"""主窗口"""

import os
import sys
from typing import List, Optional
from copy import deepcopy

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QSplitter, QFrame,
    QStatusBar, QToolBar, QAction, QMessageBox, QFileDialog,
    QShortcut, QTreeWidget, QTreeWidgetItem, QDialog, QComboBox,
    QDialogButtonBox
)
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QKeySequence, QCursor, QIcon

from .models import Template, Annotation, Keypoint
from .canvas import Canvas
from .dialogs import ConfigDialog, SaveConfirmDialog, TemplateEditDialog
from .config import ConfigManager
from .utils import get_image_files, get_label_path, load_annotations, save_annotations
from .constants import KEYPOINT_KEY_MAP, KEYBOARD_LAYOUT
from .config import get_app_dir, get_resource_path


MAX_UNDO_HISTORY = 50


class ClassSelectDialog(QDialog):
    def __init__(self, class_names: List[str], current_class: int = 0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择类别")
        self.setMinimumWidth(250)
        self.selected_class = current_class
        self.setup_ui(class_names, current_class)
    
    def setup_ui(self, class_names: List[str], current_class: int):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("选择目标类别:"))
        
        self.class_combo = QComboBox()
        self.class_combo.addItems(class_names)
        if current_class < len(class_names):
            self.class_combo.setCurrentIndex(current_class)
        layout.addWidget(self.class_combo)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)
    
    def accept(self):
        self.selected_class = self.class_combo.currentIndex()
        super().accept()


class KeypointVisDialog(QDialog):
    def __init__(self, kp_name: str, current_vis: int = 2, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"设置关键点可见性: {kp_name}")
        self.selected_vis = current_vis
        self.setup_ui(current_vis)
    
    def setup_ui(self, current_vis: int):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("选择可见性状态:"))
        
        self.vis_combo = QComboBox()
        self.vis_combo.addItem("0 - 忽略 (不显示)", 0)
        self.vis_combo.addItem("1 - 遮挡", 1)
        self.vis_combo.addItem("2 - 可见", 2)
        self.vis_combo.setCurrentIndex(current_vis)
        layout.addWidget(self.vis_combo)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)
    
    def accept(self):
        self.selected_vis = self.vis_combo.currentData()
        super().accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("labeleasy")
        self.setMinimumSize(1200, 800)
        
        icon_path = get_resource_path("labeleasy/icon.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        self.template: Optional[Template] = None
        self.image_dir: str = ""
        self.label_dir: str = ""
        self.template_path: str = ""
        self.image_files: List[str] = []
        self.current_image_idx: int = -1
        self.annotations: List[Annotation] = []
        self.original_annotations: List[Annotation] = []
        self.modified: bool = False
        self.auto_save: bool = True
        
        self.undo_history: List[List[Annotation]] = []
        self.redo_history: List[List[Annotation]] = []
        
        self.config_manager = ConfigManager()
        
        self.setup_ui()
        self.load_config()
        self.setup_shortcuts()
        
        if not self.show_config_dialog():
            sys.exit(0)
    
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)
        
        self.image_list = QListWidget()
        self.image_list.itemClicked.connect(self.on_image_selected)
        left_layout.addWidget(QLabel("图像列表:"))
        left_layout.addWidget(self.image_list)
        
        self.annotation_tree = QTreeWidget()
        self.annotation_tree.setHeaderLabel("标注列表 (双击修改)")
        self.annotation_tree.itemClicked.connect(self.on_annotation_tree_clicked)
        self.annotation_tree.itemDoubleClicked.connect(self.on_annotation_tree_double_clicked)
        left_layout.addWidget(self.annotation_tree)
        
        left_panel.setMaximumWidth(280)
        splitter.addWidget(left_panel)
        
        self.canvas = Canvas()
        self.canvas.annotation_clicked.connect(self.on_canvas_annotation_clicked)
        self.canvas.keypoint_clicked.connect(self.on_canvas_keypoint_clicked)
        self.canvas.request_save_undo.connect(self.save_undo_state)
        self.canvas.annotation_added.connect(self.on_canvas_annotation_added)
        self.canvas.annotation_modified.connect(self.on_canvas_annotation_modified)
        splitter.addWidget(self.canvas)
        
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(5, 5, 5, 5)
        
        self.keypoint_list = QListWidget()
        self.keypoint_list.itemClicked.connect(self.on_keypoint_selected)
        right_layout.addWidget(QLabel("关键点 (点击或按键盘):"))
        right_layout.addWidget(self.keypoint_list)
        
        right_panel.setMaximumWidth(200)
        splitter.addWidget(right_panel)
        
        self.create_toolbar()
        self.create_status_bar()
        self.create_menu()
    
    def create_toolbar(self):
        toolbar = QToolBar("主工具栏")
        self.addToolBar(toolbar)
        
        toolbar.addAction("上一张", self.prev_image)
        toolbar.addAction("下一张", self.next_image)
        toolbar.addSeparator()
        toolbar.addAction("绘制框", self.start_bbox_drawing)
        toolbar.addAction("选择点", self.start_keypoint_select_mode)
        toolbar.addSeparator()
        toolbar.addAction("保存", self.save_current)
        toolbar.addAction("删除", self.delete_selected)
        toolbar.addSeparator()
        toolbar.addAction("撤销", self.undo)
        toolbar.addAction("重做", self.redo)
        toolbar.addSeparator()
        
        self.auto_save_action = QAction("自动保存", self)
        self.auto_save_action.setCheckable(True)
        self.auto_save_action.setChecked(True)
        self.auto_save_action.triggered.connect(self.toggle_auto_save)
        toolbar.addAction(self.auto_save_action)
    
    def create_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
    
    def create_menu(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("文件")
        file_menu.addAction("打开项目", self.open_project)
        file_menu.addAction("保存", self.save_current)
        file_menu.addAction("另存为...", self.save_as)
        file_menu.addSeparator()
        file_menu.addAction("退出", self.close)
        
        edit_menu = menubar.addMenu("编辑")
        edit_menu.addAction("撤销 (Ctrl+Z)", self.undo)
        edit_menu.addAction("重做 (Ctrl+Shift+Z)", self.redo)
        edit_menu.addSeparator()
        edit_menu.addAction("复制关键点 (Ctrl+C)", self.copy_selected)
        edit_menu.addAction("粘贴关键点 (Ctrl+V)", self.paste_to_selected)
        edit_menu.addAction("删除选中", self.delete_selected)
        
        view_menu = menubar.addMenu("视图")
        view_menu.addAction("放大", self.zoom_in)
        view_menu.addAction("缩小", self.zoom_out)
        view_menu.addAction("重置视图", self.reset_view)
        
        template_menu = menubar.addMenu("模板")
        template_menu.addAction("保存当前模板", self.save_template)
        template_menu.addAction("编辑模板", self.edit_template)
    
    def setup_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key_Left), self, self.prev_image)
        QShortcut(QKeySequence(Qt.Key_Right), self, self.next_image)
        QShortcut(QKeySequence(Qt.Key_Up), self, self.start_bbox_drawing)
        QShortcut(QKeySequence(Qt.Key_Down), self, self.start_keypoint_select_mode)
        QShortcut(QKeySequence(Qt.Key_Escape), self, self.cancel_operation)
        QShortcut(QKeySequence(Qt.CTRL + Qt.Key_S), self, self.save_current)
        QShortcut(QKeySequence(Qt.Key_Delete), self, self.delete_selected)
        QShortcut(QKeySequence(Qt.CTRL + Qt.Key_C), self, self.copy_selected)
        QShortcut(QKeySequence(Qt.CTRL + Qt.Key_V), self, self.paste_to_selected)
        QShortcut(QKeySequence(Qt.CTRL + Qt.Key_Z), self, self.undo)
        QShortcut(QKeySequence(Qt.CTRL + Qt.SHIFT + Qt.Key_Z), self, self.redo)
        
        for key, kp_id in KEYPOINT_KEY_MAP.items():
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(lambda kid=kp_id: self.on_keypoint_shortcut(kid))
    
    def save_undo_state(self):
        state = deepcopy(self.annotations)
        self.undo_history.append(state)
        if len(self.undo_history) > MAX_UNDO_HISTORY:
            self.undo_history.pop(0)
        self.redo_history.clear()
    
    def undo(self):
        if not self.undo_history:
            self.status_bar.showMessage("没有可撤销的操作")
            return
        
        current_state = deepcopy(self.annotations)
        self.redo_history.append(current_state)
        
        prev_state = self.undo_history.pop()
        self.annotations = prev_state
        self.canvas.annotations = self.annotations
        self.canvas.update()
        self.update_annotation_tree()
        
        if self.auto_save:
            self.save_current_annotations()
        
        if self.annotations_equal(self.annotations, self.original_annotations):
            self.modified = False
        else:
            self.modified = True
        
        self.status_bar.showMessage("已撤销")
    
    def redo(self):
        if not self.redo_history:
            self.status_bar.showMessage("没有可重做的操作")
            return
        
        current_state = deepcopy(self.annotations)
        self.undo_history.append(current_state)
        
        next_state = self.redo_history.pop()
        self.annotations = next_state
        self.canvas.annotations = self.annotations
        self.canvas.update()
        self.update_annotation_tree()
        
        if self.auto_save:
            self.save_current_annotations()
        
        if self.annotations_equal(self.annotations, self.original_annotations):
            self.modified = False
        else:
            self.modified = True
        
        self.status_bar.showMessage("已重做")
    
    def annotations_equal(self, a1: List[Annotation], a2: List[Annotation]) -> bool:
        if len(a1) != len(a2):
            return False
        for ann1, ann2 in zip(a1, a2):
            if ann1.class_id != ann2.class_id:
                return False
            if abs(ann1.x_center - ann2.x_center) > 0.0001:
                return False
            if abs(ann1.y_center - ann2.y_center) > 0.0001:
                return False
            if abs(ann1.width - ann2.width) > 0.0001:
                return False
            if abs(ann1.height - ann2.height) > 0.0001:
                return False
            if len(ann1.keypoints) != len(ann2.keypoints):
                return False
            for kp1, kp2 in zip(ann1.keypoints, ann2.keypoints):
                if kp1.vis != kp2.vis:
                    return False
                if kp1.vis > 0:
                    if abs(kp1.x - kp2.x) > 0.0001:
                        return False
                    if abs(kp1.y - kp2.y) > 0.0001:
                        return False
        return True
    
    def load_config(self):
        self.auto_save = self.config_manager.get_auto_save()
        self.auto_save_action.setChecked(self.auto_save)
    
    def save_config(self):
        self.config_manager.set_auto_save(self.auto_save)
        if self.image_files and self.current_image_idx >= 0:
            self.config_manager.set_last_image(
                self.image_files[self.current_image_idx],
                self.image_dir,
                self.label_dir
            )
        self.config_manager.save()
    
    def show_config_dialog(self) -> bool:
        recent_projects = self.config_manager.get_recent_projects()
        dialog = ConfigDialog(self, recent_projects)
        if dialog.exec_() != ConfigDialog.Accepted:
            return False
        
        config = dialog.get_config()
        self.template_path = config['template']
        self.image_dir = config['image_dir']
        self.label_dir = config['label_dir']
        self.template = config['template_data']
        
        self.canvas.set_template(self.template)
        self.load_images()
        self.update_keypoint_list()
        
        self.config_manager.add_recent_project({
            'template': self.template_path,
            'image_dir': self.image_dir,
            'label_dir': self.label_dir
        })
        
        return True
    
    def load_images(self):
        self.image_files = get_image_files(self.image_dir)
        
        self.image_list.clear()
        for f in self.image_files:
            self.image_list.addItem(os.path.basename(f))
        
        if self.image_files:
            last_image = self.config_manager.get_last_image(self.image_dir, self.label_dir)
            start_idx = 0
            if last_image:
                for i, f in enumerate(self.image_files):
                    if f == last_image:
                        start_idx = i
                        break
            self.current_image_idx = start_idx
            self.load_image(start_idx)
    
    def load_image(self, idx: int):
        if idx < 0 or idx >= len(self.image_files):
            return
        
        if self.modified and not self.auto_save:
            dialog = SaveConfirmDialog(self)
            if dialog.exec_() == SaveConfirmDialog.Accepted:
                if dialog.result_code == 1:
                    self.save_current()
                elif dialog.result_code == 0:
                    return
            else:
                return
        
        self.undo_history.clear()
        self.redo_history.clear()
        
        self.current_image_idx = idx
        image_path = self.image_files[idx]
        self.canvas.set_image(image_path)
        self.load_annotations_for_image(image_path)
        
        self.image_list.setCurrentRow(idx)
        self.status_bar.showMessage(f"图像 {idx + 1}/{len(self.image_files)}: {os.path.basename(image_path)}")
        self.modified = False
    
    def load_annotations_for_image(self, image_path: str):
        num_keypoints = len(self.template.keypoints) if self.template else 0
        label_path = get_label_path(image_path, self.label_dir)
        
        self.annotations, warnings_list = load_annotations(label_path, num_keypoints)
        self.original_annotations = deepcopy(self.annotations)
        
        if warnings_list:
            QMessageBox.warning(self, "标签修复警告", "\n".join(warnings_list[:10]))
        
        self.canvas.set_annotations(self.annotations)
        self.update_annotation_tree()
    
    def save_current_annotations(self):
        if self.current_image_idx < 0:
            return
        
        image_path = self.image_files[self.current_image_idx]
        label_path = get_label_path(image_path, self.label_dir)
        save_annotations(label_path, self.annotations)
        self.original_annotations = deepcopy(self.annotations)
        self.modified = False
    
    def update_annotation_tree(self):
        self.annotation_tree.clear()
        
        for idx, ann in enumerate(self.annotations):
            if self.template and ann.class_id < len(self.template.names):
                label = self.template.names[ann.class_id]
            else:
                label = f"class_{ann.class_id}"
            
            kp_count = sum(1 for kp in ann.keypoints if kp.vis > 0)
            item = QTreeWidgetItem([f"[{idx}] {label} ({kp_count}点)"])
            item.setData(0, Qt.UserRole, idx)
            item.setData(0, Qt.UserRole + 1, -1)
            
            if self.template:
                for kp_idx, kp in enumerate(ann.keypoints):
                    if kp.vis > 0 and kp_idx < len(self.template.keypoints):
                        kp_name = self.template.keypoints[kp_idx]
                        vis_str = {0: "忽略", 1: "遮挡", 2: "可见"}.get(kp.vis, "?")
                        shortcut = self.canvas.get_keypoint_shortcut(kp_idx)
                        kp_item = QTreeWidgetItem([f"  [{shortcut}] {kp_name}: {vis_str}"])
                        kp_item.setData(0, Qt.UserRole, idx)
                        kp_item.setData(0, Qt.UserRole + 1, kp_idx)
                        item.addChild(kp_item)
            
            self.annotation_tree.addTopLevelItem(item)
    
    def update_keypoint_list(self):
        self.keypoint_list.clear()
        if not self.template:
            return
        
        kp_idx = 0
        for row in KEYBOARD_LAYOUT:
            for ch in row:
                if kp_idx < len(self.template.keypoints):
                    self.keypoint_list.addItem(f"[{ch}] {self.template.keypoints[kp_idx]}")
                    kp_idx += 1
        
        while kp_idx < len(self.template.keypoints):
            self.keypoint_list.addItem(f"[?] {self.template.keypoints[kp_idx]}")
            kp_idx += 1
    
    def on_image_selected(self, item: QListWidgetItem):
        idx = self.image_list.row(item)
        if idx != self.current_image_idx:
            self.load_image(idx)
    
    def on_annotation_tree_clicked(self, item: QTreeWidgetItem):
        ann_idx = item.data(0, Qt.UserRole)
        kp_idx = item.data(0, Qt.UserRole + 1)
        
        self.canvas.selected_annotation_idx = ann_idx
        self.canvas.selected_keypoint_idx = kp_idx if kp_idx >= 0 else -1
        self.canvas.update()
    
    def on_annotation_tree_double_clicked(self, item: QTreeWidgetItem):
        ann_idx = item.data(0, Qt.UserRole)
        kp_idx = item.data(0, Qt.UserRole + 1)
        
        if ann_idx < 0 or ann_idx >= len(self.annotations):
            return
        
        if kp_idx >= 0:
            if self.template and kp_idx < len(self.template.keypoints):
                kp_name = self.template.keypoints[kp_idx]
                current_vis = self.annotations[ann_idx].keypoints[kp_idx].vis if kp_idx < len(self.annotations[ann_idx].keypoints) else 2
                dialog = KeypointVisDialog(kp_name, current_vis, self)
                if dialog.exec_() == QDialog.Accepted:
                    self.canvas.set_keypoint_vis(kp_idx, dialog.selected_vis)
                    self.annotations = self.canvas.annotations
                    self.update_annotation_tree()
                    if self.auto_save:
                        self.save_current_annotations()
        else:
            if self.template and len(self.template.names) > 1:
                current_class = self.annotations[ann_idx].class_id
                dialog = ClassSelectDialog(self.template.names, current_class, self)
                if dialog.exec_() == QDialog.Accepted:
                    self.canvas.set_annotation_class(dialog.selected_class)
                    self.annotations = self.canvas.annotations
                    self.update_annotation_tree()
                    if self.auto_save:
                        self.save_current_annotations()
    
    def on_keypoint_selected(self, item: QListWidgetItem):
        idx = self.keypoint_list.row(item)
        if self.canvas.selected_annotation_idx >= 0:
            self.canvas.start_keypoint_drawing(idx)
            if self.template and idx < len(self.template.keypoints):
                self.status_bar.showMessage(f"绘制关键点 [{self.canvas.get_keypoint_shortcut(idx)}]: {self.template.keypoints[idx]} - 点击框内位置")
    
    def on_canvas_annotation_clicked(self, idx: int):
        for i in range(self.annotation_tree.topLevelItemCount()):
            item = self.annotation_tree.topLevelItem(i)
            if item.data(0, Qt.UserRole) == idx:
                self.annotation_tree.setCurrentItem(item)
                break
    
    def on_canvas_keypoint_clicked(self, ann_idx: int, kp_idx: int):
        for i in range(self.annotation_tree.topLevelItemCount()):
            item = self.annotation_tree.topLevelItem(i)
            if item.data(0, Qt.UserRole) == ann_idx:
                self.annotation_tree.setCurrentItem(item)
                break
        if self.template and kp_idx < len(self.template.keypoints):
            self.status_bar.showMessage(f"选中关键点: {self.template.keypoints[kp_idx]}")
    
    def on_canvas_annotation_added(self):
        self.annotations = self.canvas.annotations
        
        if self.template and len(self.template.names) > 1:
            dialog = ClassSelectDialog(self.template.names, 0, self)
            if dialog.exec_() == QDialog.Accepted:
                self.canvas.set_annotation_class(dialog.selected_class)
                self.annotations = self.canvas.annotations
        
        self.update_annotation_tree()
        self.modified = True
        if self.auto_save:
            self.save_current_annotations()
    
    def on_canvas_annotation_modified(self):
        self.annotations = self.canvas.annotations
        self.update_annotation_tree()
        self.modified = True
        if self.auto_save:
            self.save_current_annotations()
    
    def on_keypoint_shortcut(self, kp_id: int):
        if self.canvas.selected_annotation_idx < 0:
            return
        if not self.template:
            return
        if kp_id >= len(self.template.keypoints):
            self.status_bar.showMessage(f"关键点索引 {kp_id} 超出范围 (模板共 {len(self.template.keypoints)} 个关键点)")
            return
        
        self.canvas.start_keypoint_drawing(kp_id)
        self.status_bar.showMessage(f"绘制关键点 [{self.canvas.get_keypoint_shortcut(kp_id)}]: {self.template.keypoints[kp_id]} - 点击框内位置")
    
    def prev_image(self):
        if self.current_image_idx > 0:
            self.load_image(self.current_image_idx - 1)
    
    def next_image(self):
        if self.current_image_idx < len(self.image_files) - 1:
            self.load_image(self.current_image_idx + 1)
    
    def start_bbox_drawing(self):
        if self.canvas.drawing_mode == 'keypoint':
            self.canvas.stop_drawing()
        self.canvas.start_bbox_drawing()
        self.status_bar.showMessage("绘制边界框: 拖动鼠标绘制")
    
    def start_keypoint_select_mode(self):
        if self.canvas.selected_annotation_idx < 0:
            self.status_bar.showMessage("请先选择一个标注框")
            return
        self.canvas.start_keypoint_select_mode()
        self.status_bar.showMessage("框选关键点模式: 拖动选择关键点，然后按Ctrl+C复制")
    
    def cancel_operation(self):
        self.canvas.stop_drawing()
        self.status_bar.showMessage("已取消操作")
    
    def save_current(self):
        self.save_current_annotations()
        self.status_bar.showMessage("已保存")
    
    def save_as(self):
        if self.current_image_idx < 0:
            return
        
        filepath, _ = QFileDialog.getSaveFileName(
            self, "保存标签", "", "TXT文件 (*.txt)"
        )
        if filepath:
            save_annotations(filepath, self.annotations)
            self.status_bar.showMessage(f"已保存到: {filepath}")
    
    def delete_selected(self):
        if self.canvas.delete_selected():
            self.annotations = self.canvas.annotations
            self.modified = True
            self.update_annotation_tree()
            if self.auto_save:
                self.save_current_annotations()
    
    def copy_selected(self):
        self.canvas.copy_selected()
        kp_count = len(self.canvas.clipboard_keypoints)
        if kp_count > 0:
            self.status_bar.showMessage(f"已复制 {kp_count} 个关键点")
        else:
            self.status_bar.showMessage("已复制选中框的所有关键点")
    
    def paste_to_selected(self):
        if not self.canvas.clipboard_keypoints:
            self.status_bar.showMessage("剪贴板为空")
            return
        if self.canvas.selected_annotation_idx < 0:
            self.status_bar.showMessage("请先选择目标标注框")
            return
        
        self.save_undo_state()
        self.canvas.paste_keypoints()
        self.annotations = self.canvas.annotations
        self.modified = True
        self.update_annotation_tree()
        if self.auto_save:
            self.save_current_annotations()
        self.status_bar.showMessage("已粘贴关键点")
    
    def toggle_auto_save(self):
        self.auto_save = self.auto_save_action.isChecked()
        self.config_manager.set_auto_save(self.auto_save)
        self.status_bar.showMessage(f"自动保存: {'开启' if self.auto_save else '关闭'}")
    
    def zoom_in(self):
        self.canvas.scale *= 1.2
        self.canvas.update()
    
    def zoom_out(self):
        self.canvas.scale /= 1.2
        self.canvas.update()
    
    def reset_view(self):
        self.canvas.scale = 1.0
        self.canvas.offset = QPoint(0, 0)
        self.canvas.update()
    
    def save_template(self):
        if not self.template:
            return
        
        filepath, _ = QFileDialog.getSaveFileName(
            self, "保存模板", "", "YAML文件 (*.yaml)"
        )
        if filepath:
            self.template.to_yaml(filepath)
            self.status_bar.showMessage(f"模板已保存: {filepath}")
    
    def edit_template(self):
        if not self.template:
            return
        
        dialog = TemplateEditDialog(self.template, self)
        if dialog.exec_() == TemplateEditDialog.Accepted:
            self.update_keypoint_list()
            self.status_bar.showMessage("模板已更新")
    
    def open_project(self):
        if self.show_config_dialog():
            self.status_bar.showMessage("项目已打开")
    
    def closeEvent(self, event):
        if self.modified and not self.auto_save:
            dialog = SaveConfirmDialog(self)
            if dialog.exec_() == SaveConfirmDialog.Accepted:
                if dialog.result_code == 1:
                    self.save_current()
                elif dialog.result_code == 0:
                    event.ignore()
                    return
        
        self.save_config()
        event.accept()