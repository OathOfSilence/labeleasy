# -*- coding: utf-8 -*-
"""关键点标注模式"""

from typing import Optional, List, Tuple, Any
from copy import deepcopy

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QCursor

from .base import AnnotationMode
from ..models import Keypoint


class KeypointMode(AnnotationMode):
    """关键点标注模式"""
    
    def __init__(self, canvas):
        super().__init__(canvas)
        self.select_start: Optional[QPoint] = None
        self.select_end: Optional[QPoint] = None
        self.drawing = False
        self.selected_for_copy: List[Tuple[int, Keypoint]] = []
    
    def enter(self):
        self.select_start = None
        self.select_end = None
        self.drawing = False
        self.selected_for_copy = []
    
    def exit(self):
        self.drawing = False
    
    def on_mouse_press(self, event) -> bool:
        if event.button() != Qt.MouseButton.LeftButton:
            return False
        
        screen_pos = event.position().toPoint()
        
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self._toggle_selection(screen_pos)
            return True
        else:
            self.drawing = True
            self.select_start = screen_pos
            self.select_end = screen_pos
            return True
    
    def on_mouse_move(self, event) -> bool:
        if self.drawing:
            self.select_end = event.position().toPoint()
            self.canvas.update()
            return True
        return False
    
    def on_mouse_release(self, event) -> bool:
        if event.button() != Qt.MouseButton.LeftButton:
            return False
        
        if self.drawing:
            self.drawing = False
            self._finish_selection()
            self.select_start = None
            self.select_end = None
            return True
        return False
    
    def draw_overlay(self, painter: QPainter, img_rect: QRect):
        if self.drawing and self.select_start and self.select_end:
            pen = QPen(QColor(0, 255, 255), 2, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(QBrush(QColor(0, 255, 255, 30)))
            painter.drawRect(QRect(self.select_start, self.select_end))
    
    def _toggle_selection(self, screen_pos: QPoint):
        """Ctrl+ 点击切换关键点选中状态"""
        if self.canvas.selected_annotation_idx < 0:
            return
        
        ann = self.canvas.annotations[self.canvas.selected_annotation_idx]
        
        for kp_idx, kp in enumerate(ann.keypoints):
            if kp.vis == 0:
                continue
            kp_screen = self.canvas.img_to_screen(kp.x, kp.y)
            if (kp_screen - screen_pos).manhattanLength() < 10:
                existing_idx = next(
                    (i for i, (idx, _) in enumerate(self.selected_for_copy) if idx == kp_idx),
                    None
                )
                if existing_idx is not None:
                    self.selected_for_copy.pop(existing_idx)
                else:
                    self.selected_for_copy.append((kp_idx, deepcopy(kp)))
                self.canvas.update()
                return
    
    def _finish_selection(self):
        """完成框选"""
        if not self.select_start or not self.select_end:
            return
        
        if self.canvas.selected_annotation_idx < 0:
            return
        
        ann = self.canvas.annotations[self.canvas.selected_annotation_idx]
        sel_rect = QRect(self.select_start, self.select_end).normalized()
        
        self.selected_for_copy = []
        for kp_idx, kp in enumerate(ann.keypoints):
            if kp.vis == 0:
                continue
            kp_screen = self.canvas.img_to_screen(kp.x, kp.y)
            if sel_rect.contains(kp_screen):
                self.selected_for_copy.append((kp_idx, deepcopy(kp)))
        
        self.canvas.update()
    
    def copy(self) -> Optional[Any]:
        """复制选中的关键点"""
        if self.selected_for_copy:
            result = deepcopy(self.selected_for_copy)
            self.selected_for_copy = []
            return result
        return None
    
    def paste(self, data: Any) -> Tuple[bool, str]:
        """粘贴关键点"""
        if not data or self.canvas.selected_annotation_idx < 0:
            return (False, "无法粘贴")
        
        self.canvas.request_save_undo.emit()
        ann = self.canvas.annotations[self.canvas.selected_annotation_idx]
        
        for kp_idx, kp in data:
            while len(ann.keypoints) <= kp_idx:
                ann.keypoints.append(Keypoint(x=0.5, y=0.5, vis=0))
            ann.keypoints[kp_idx] = deepcopy(kp)
        
        self.canvas.annotation_modified.emit()
        self.canvas.update()
        return (True, f"已粘贴 {len(data)} 个关键点")
    
    def get_status_message(self) -> str:
        return "框选关键点模式：拖动选择关键点，Ctrl+ 点击切换选中，Ctrl+C 复制"
    
    def get_cursor(self) -> QCursor:
        return QCursor(Qt.CursorShape.CrossCursor)
