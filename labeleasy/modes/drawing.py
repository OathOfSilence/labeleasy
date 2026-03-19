# -*- coding: utf-8 -*-
"""绘制边界框模式"""

from typing import Optional, Tuple

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QCursor

from .base import AnnotationMode
from ..models import Annotation, Keypoint


class BboxDrawingMode(AnnotationMode):
    """绘制边界框模式"""
    
    def __init__(self, canvas):
        super().__init__(canvas)
        self.draw_start: Optional[QPoint] = None
        self.draw_end: Optional[QPoint] = None
        self.pending_class_id: int = -1  # 预设类别（无关键点模式）
    
    def enter(self):
        self.draw_start = None
        self.draw_end = None
        # pending_class_id 保持，在绘制完成后使用
    
    def exit(self):
        self.pending_class_id = -1
    
    def set_pending_class(self, class_id: int):
        """设置预设类别（无关键点模式）"""
        self.pending_class_id = class_id
    
    def on_mouse_press(self, event) -> bool:
        if event.button() != Qt.MouseButton.LeftButton:
            return False
        
        self.draw_start = event.position().toPoint()
        self.draw_end = event.position().toPoint()
        return True
    
    def on_mouse_move(self, event) -> bool:
        self.draw_end = event.position().toPoint()
        self.canvas.update()
        return True
    
    def on_mouse_release(self, event) -> bool:
        if event.button() != Qt.MouseButton.LeftButton:
            return False
        
        self._finish_drawing()
        self.draw_start = None
        self.draw_end = None
        # 绘制完成后退出模式，返回普通模式
        self.canvas.pop_mode()
        return True
    
    def draw_overlay(self, painter: QPainter, img_rect: QRect):
        if self.draw_start and self.draw_end:
            pen = QPen(QColor(0, 255, 255), 2, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(QBrush(QColor(0, 255, 255, 50)))
            painter.drawRect(QRect(self.draw_start, self.draw_end))
    
    def _finish_drawing(self):
        """完成绘制，创建标注框"""
        if not self.draw_start or not self.draw_end:
            self.pending_class_id = -1
            return
        
        rect = self.canvas.get_image_rect()
        x1 = (min(self.draw_start.x(), self.draw_end.x()) - rect.x()) / rect.width()
        y1 = (min(self.draw_start.y(), self.draw_end.y()) - rect.y()) / rect.height()
        x2 = (max(self.draw_start.x(), self.draw_end.x()) - rect.x()) / rect.width()
        y2 = (max(self.draw_start.y(), self.draw_end.y()) - rect.y()) / rect.height()
        
        x1 = max(0, min(1, x1))
        y1 = max(0, min(1, y1))
        x2 = max(0, min(1, x2))
        y2 = max(0, min(1, y2))
        
        if abs(x2 - x1) < 0.01 or abs(y2 - y1) < 0.01:
            self.pending_class_id = -1
            return
        
        self.canvas.request_save_undo.emit()
        
        # 使用预设类别或默认 0
        # 注意：不在这里重置 pending_class_id，让 on_canvas_annotation_added 能判断是否预设了类别
        class_id = self.pending_class_id if self.pending_class_id >= 0 else 0
        
        num_keypoints = len(self.canvas.template.keypoints) if self.canvas.template else 0
        keypoints = [Keypoint(x=0.5, y=0.5, vis=0) for _ in range(num_keypoints)]
        
        ann = Annotation(
            class_id=class_id,
            x_center=(x1 + x2) / 2,
            y_center=(y1 + y2) / 2,
            width=x2 - x1,
            height=y2 - y1,
            keypoints=keypoints
        )
        
        self.canvas.annotations.append(ann)
        self.canvas.selected_annotation_idx = len(self.canvas.annotations) - 1
        self.canvas.selected_keypoint_idx = -1
        self.canvas.annotation_added.emit()
        
        # 在 emit 之后重置
        self.pending_class_id = -1
    
    def get_status_message(self) -> str:
        if self.pending_class_id >= 0 and self.canvas.template:
            class_name = self.canvas.template.names[self.pending_class_id] if self.pending_class_id < len(self.canvas.template.names) else "?"
            return f"绘制检测框：{class_name} - 拖动鼠标绘制"
        return "绘制边界框：拖动鼠标绘制"
    
    def get_cursor(self) -> QCursor:
        return QCursor(Qt.CursorShape.CrossCursor)
