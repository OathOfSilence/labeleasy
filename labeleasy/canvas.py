# -*- coding: utf-8 -*-
"""画布组件"""

from typing import List, Tuple, Optional
from copy import deepcopy

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QPoint, QRect, pyqtSignal
from PyQt5.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QPixmap, QImage,
    QCursor
)
import cv2
import numpy as np

from .models import Annotation, Keypoint, Template
from .constants import SKELETON_COLORS, KEYBOARD_LAYOUT


class Canvas(QWidget):
    annotation_clicked = pyqtSignal(int)
    keypoint_clicked = pyqtSignal(int, int)
    annotation_added = pyqtSignal()
    annotation_modified = pyqtSignal()
    request_save_undo = pyqtSignal()
    
    CORNER_SIZE = 8
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image: Optional[np.ndarray] = None
        self.image_path: Optional[str] = None
        self.annotations: List[Annotation] = []
        self.template: Optional[Template] = None
        self.scale = 1.0
        self.offset = QPoint(0, 0)
        self.drawing = False
        self.drawing_mode: Optional[str] = None
        self.draw_start: Optional[QPoint] = None
        self.draw_end: Optional[QPoint] = None
        self.selected_annotation_idx = -1
        self.selected_keypoint_idx = -1
        self.hover_annotation_idx = -1
        self.hover_keypoint_idx = -1
        self.current_keypoint_id = -1
        self.clipboard_keypoints: List[Tuple[int, Keypoint]] = []
        self.selected_keypoints_for_copy: List[Tuple[int, Keypoint]] = []
        
        self.dragging_corner: Optional[int] = None
        self.drag_start_pos: Optional[QPoint] = None
        self.drag_start_ann: Optional[Annotation] = None
        
        self.keypoint_select_mode = False
        self.kp_select_start: Optional[QPoint] = None
        self.kp_select_end: Optional[QPoint] = None
        self.kp_select_drawing = False
        
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumSize(400, 300)
    
    def set_image(self, image_path: str):
        self.image_path = image_path
        try:
            with open(image_path, 'rb') as f:
                img_data = np.frombuffer(f.read(), dtype=np.uint8)
            self.image = cv2.imdecode(img_data, cv2.IMREAD_COLOR)
            if self.image is not None:
                self.image = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)
        except Exception:
            self.image = None
        self.update()
    
    def set_annotations(self, annotations: List[Annotation]):
        self.annotations = annotations
        self.selected_annotation_idx = -1
        self.selected_keypoint_idx = -1
        if annotations:
            self.selected_annotation_idx = 0
        self.update()
    
    def set_template(self, template: Template):
        self.template = template
        self.update()
    
    def get_keypoint_shortcut(self, kp_idx: int) -> str:
        idx = 0
        for row in KEYBOARD_LAYOUT:
            for ch in row:
                if idx == kp_idx:
                    return ch
                idx += 1
        return "?"
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if self.image is None:
            painter.fillRect(self.rect(), QColor(50, 50, 50))
            painter.setPen(QColor(200, 200, 200))
            painter.drawText(self.rect(), Qt.AlignCenter, "请打开图像")
            return
        
        h, w, c = self.image.shape
        qimg = QImage(self.image.data, w, h, 3 * w, QImage.Format_RGB888)
        scaled_pixmap = QPixmap.fromImage(qimg)
        
        img_rect = self.get_image_rect()
        painter.drawPixmap(img_rect, scaled_pixmap.scaled(
            img_rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        ))
        
        self.draw_annotations(painter, img_rect)
        
        if self.drawing and self.draw_start and self.draw_end:
            self.draw_drawing_shape(painter, img_rect)
        
        if self.kp_select_drawing and self.kp_select_start and self.kp_select_end:
            pen = QPen(QColor(0, 255, 255), 2, Qt.DashLine)
            painter.setPen(pen)
            painter.setBrush(QBrush(QColor(0, 255, 255, 30)))
            painter.drawRect(QRect(self.kp_select_start, self.kp_select_end))
    
    def get_image_rect(self) -> QRect:
        if self.image is None:
            return QRect()
        
        h, w = self.image.shape[:2]
        img_w = int(w * self.scale)
        img_h = int(h * self.scale)
        
        x = self.offset.x() + (self.width() - img_w) // 2
        y = self.offset.y() + (self.height() - img_h) // 2
        
        return QRect(x, y, img_w, img_h)
    
    def img_to_screen(self, x: float, y: float) -> QPoint:
        rect = self.get_image_rect()
        sx = rect.x() + x * rect.width()
        sy = rect.y() + y * rect.height()
        return QPoint(int(sx), int(sy))
    
    def screen_to_img(self, x: int, y: int) -> Tuple[float, float]:
        rect = self.get_image_rect()
        ix = (x - rect.x()) / rect.width() if rect.width() > 0 else 0
        iy = (y - rect.y()) / rect.height() if rect.height() > 0 else 0
        return ix, iy
    
    def draw_annotations(self, painter: QPainter, img_rect: QRect):
        for idx, ann in enumerate(self.annotations):
            self.draw_single_annotation(painter, ann, idx, img_rect)
    
    def draw_single_annotation(self, painter: QPainter, ann: Annotation, 
                                idx: int, img_rect: QRect):
        x1, y1, x2, y2 = ann.get_bbox_coords()
        p1 = self.img_to_screen(x1, y1)
        p2 = self.img_to_screen(x2, y2)
        
        is_selected = idx == self.selected_annotation_idx
        is_hover = idx == self.hover_annotation_idx
        
        if is_selected:
            color = QColor(0, 255, 0)
            pen_width = 3
        elif is_hover:
            color = QColor(255, 255, 0)
            pen_width = 2
        else:
            color = QColor(255, 0, 0)
            pen_width = 2
        
        pen = QPen(color, pen_width)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(QRect(p1, p2))
        
        if is_selected:
            corners = self.get_corner_points(p1, p2)
            painter.setBrush(QBrush(QColor(0, 255, 0)))
            for corner in corners:
                painter.drawRect(QRect(corner.x() - self.CORNER_SIZE//2, 
                                       corner.y() - self.CORNER_SIZE//2,
                                       self.CORNER_SIZE, self.CORNER_SIZE))
        
        if self.template and idx == self.selected_annotation_idx:
            self.draw_skeleton(painter, ann, img_rect)
        
        self.draw_keypoints(painter, ann, idx, img_rect)
        
        if self.template and idx == self.selected_annotation_idx:
            label = self.template.names[ann.class_id] if ann.class_id < len(self.template.names) else str(ann.class_id)
        else:
            label = str(ann.class_id)
        
        painter.setPen(QPen(Qt.white, 1))
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(p1.x() + 2, p1.y() - 5, label)
    
    def get_corner_points(self, p1: QPoint, p2: QPoint) -> List[QPoint]:
        return [
            p1,
            QPoint(p2.x(), p1.y()),
            QPoint(p1.x(), p2.y()),
            p2
        ]
    
    def get_corner_at_pos(self, screen_pos: QPoint, ann_idx: int) -> Optional[int]:
        if ann_idx < 0 or ann_idx >= len(self.annotations):
            return None
        
        ann = self.annotations[ann_idx]
        x1, y1, x2, y2 = ann.get_bbox_coords()
        p1 = self.img_to_screen(x1, y1)
        p2 = self.img_to_screen(x2, y2)
        
        corners = self.get_corner_points(p1, p2)
        for i, corner in enumerate(corners):
            if (corner - screen_pos).manhattanLength() < self.CORNER_SIZE + 5:
                return i
        return None
    
    def draw_skeleton(self, painter: QPainter, ann: Annotation, img_rect: QRect):
        if not self.template:
            return
        
        for group_idx, group in enumerate(self.template.skeleton):
            color = SKELETON_COLORS[group_idx % len(SKELETON_COLORS)]
            pen = QPen(color, 2)
            painter.setPen(pen)
            
            for conn in group:
                if len(conn) >= 2:
                    kp1_idx, kp2_idx = conn[0], conn[1]
                    if kp1_idx < len(ann.keypoints) and kp2_idx < len(ann.keypoints):
                        kp1 = ann.keypoints[kp1_idx]
                        kp2 = ann.keypoints[kp2_idx]
                        if kp1.vis > 0 and kp2.vis > 0:
                            p1 = self.img_to_screen(kp1.x, kp1.y)
                            p2 = self.img_to_screen(kp2.x, kp2.y)
                            painter.drawLine(p1, p2)
    
    def draw_keypoints(self, painter: QPainter, ann: Annotation, 
                        ann_idx: int, img_rect: QRect):
        for kp_idx, kp in enumerate(ann.keypoints):
            if kp.vis == 0:
                continue
            
            pos = self.img_to_screen(kp.x, kp.y)
            
            if kp.vis == 2:
                color = QColor(0, 255, 0)
            else:
                color = QColor(255, 165, 0)
            
            is_selected = ann_idx == self.selected_annotation_idx and kp_idx == self.selected_keypoint_idx
            is_hover = ann_idx == self.hover_annotation_idx and kp_idx == self.hover_keypoint_idx
            is_copy_selected = any(sk[0] == kp_idx for sk in self.selected_keypoints_for_copy)
            
            if is_copy_selected:
                painter.setBrush(QBrush(QColor(0, 255, 255)))
                radius = 8
            elif is_selected:
                painter.setBrush(QBrush(QColor(255, 0, 255)))
                radius = 8
            elif is_hover:
                painter.setBrush(QBrush(QColor(255, 255, 0)))
                radius = 6
            else:
                painter.setBrush(QBrush(color))
                radius = 5
            
            painter.setPen(QPen(Qt.black, 1))
            painter.drawEllipse(pos, radius, radius)
            
            if self.template and ann_idx == self.selected_annotation_idx:
                shortcut = self.get_keypoint_shortcut(kp_idx)
                painter.setPen(QPen(Qt.white, 1))
                font = QFont()
                font.setPointSize(8)
                font.setBold(True)
                painter.setFont(font)
                painter.drawText(pos.x() + 8, pos.y() - 3, f"[{shortcut}]")
    
    def draw_drawing_shape(self, painter: QPainter, img_rect: QRect):
        if self.drawing_mode == 'bbox':
            pen = QPen(QColor(0, 255, 255), 2, Qt.DashLine)
            painter.setPen(pen)
            painter.setBrush(QBrush(QColor(0, 255, 255, 50)))
            painter.drawRect(QRect(self.draw_start, self.draw_end))
        elif self.drawing_mode == 'keypoint':
            pen = QPen(QColor(255, 0, 255), 2)
            painter.setPen(pen)
            painter.setBrush(QBrush(QColor(255, 0, 255, 100)))
            painter.drawEllipse(self.draw_end, 10, 10)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            img_pos = self.screen_to_img(event.x(), event.y())
            screen_pos = event.pos()
            
            if self.keypoint_select_mode and self.selected_annotation_idx >= 0:
                self.kp_select_drawing = True
                self.kp_select_start = screen_pos
                self.kp_select_end = screen_pos
                return
            
            if self.drawing_mode == 'bbox':
                self.drawing = True
                self.draw_start = event.pos()
                self.draw_end = event.pos()
            elif self.drawing_mode == 'keypoint' and self.current_keypoint_id >= 0:
                self.request_save_undo.emit()
                self.add_keypoint_at(img_pos[0], img_pos[1])
            else:
                if self.selected_annotation_idx >= 0:
                    corner = self.get_corner_at_pos(screen_pos, self.selected_annotation_idx)
                    if corner is not None:
                        self.request_save_undo.emit()
                        self.dragging_corner = corner
                        self.drag_start_pos = screen_pos
                        self.drag_start_ann = deepcopy(self.annotations[self.selected_annotation_idx])
                        return
                
                self.handle_click(screen_pos, img_pos)
    
    def mouseMoveEvent(self, event):
        img_pos = self.screen_to_img(event.x(), event.y())
        screen_pos = event.pos()
        
        if self.kp_select_drawing:
            self.kp_select_end = screen_pos
            self.update()
            return
        
        if self.dragging_corner is not None and self.drag_start_ann is not None:
            self.drag_resize_bbox(screen_pos)
            return
        
        self.update_hover(screen_pos, img_pos)
        
        if self.drawing and self.draw_start:
            self.draw_end = event.pos()
            self.update()
        
        if self.selected_annotation_idx >= 0:
            corner = self.get_corner_at_pos(screen_pos, self.selected_annotation_idx)
            if corner is not None:
                if corner in [0, 3]:
                    self.setCursor(QCursor(Qt.SizeFDiagCursor))
                else:
                    self.setCursor(QCursor(Qt.SizeBDiagCursor))
            elif self.annotations[self.selected_annotation_idx].contains_point(img_pos[0], img_pos[1]):
                self.setCursor(QCursor(Qt.ArrowCursor))
            else:
                self.setCursor(QCursor(Qt.ArrowCursor))
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.kp_select_drawing:
                self.kp_select_drawing = False
                self.finish_keypoint_selection()
                self.kp_select_start = None
                self.kp_select_end = None
                return
            
            if self.dragging_corner is not None:
                self.dragging_corner = None
                self.drag_start_pos = None
                self.drag_start_ann = None
                self.annotation_modified.emit()
                return
            
            if self.drawing:
                self.drawing = False
                if self.drawing_mode == 'bbox' and self.draw_start and self.draw_end:
                    self.finish_bbox()
                self.draw_start = None
                self.draw_end = None
                self.update()
    
    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta == 0:
            return
        
        # 以鼠标位置为中心缩放
        mouse_pos = event.position()
        
        # 获取缩放前的图像坐标
        rect = self.get_image_rect()
        mouse_x_in_img = (mouse_pos.x() - rect.x()) / self.scale
        mouse_y_in_img = (mouse_pos.y() - rect.y()) / self.scale
        
        # 应用缩放
        if delta > 0:
            self.scale *= 1.1
        else:
            self.scale /= 1.1
        self.scale = max(0.1, min(10.0, self.scale))
        
        # 调整偏移量，使鼠标位置保持在图像的同一点上
        self.offset.setX(int(mouse_pos.x() - mouse_x_in_img * self.scale))
        self.offset.setY(int(mouse_pos.y() - mouse_y_in_img * self.scale))
        
        self.update()
    
    def drag_resize_bbox(self, screen_pos: QPoint):
        if self.selected_annotation_idx < 0 or self.drag_start_ann is None:
            return
        
        ann = self.annotations[self.selected_annotation_idx]
        rect = self.get_image_rect()
        
        dx = (screen_pos.x() - self.drag_start_pos.x()) / rect.width()
        dy = (screen_pos.y() - self.drag_start_pos.y()) / rect.height()
        
        orig = self.drag_start_ann
        
        x1 = orig.x_center - orig.width / 2
        y1 = orig.y_center - orig.height / 2
        x2 = orig.x_center + orig.width / 2
        y2 = orig.y_center + orig.height / 2
        
        if self.dragging_corner == 0:
            x1 = max(0, min(x2 - 0.01, x1 + dx))
            y1 = max(0, min(y2 - 0.01, y1 + dy))
        elif self.dragging_corner == 1:
            x2 = min(1, max(x1 + 0.01, x2 + dx))
            y1 = max(0, min(y2 - 0.01, y1 + dy))
        elif self.dragging_corner == 2:
            x1 = max(0, min(x2 - 0.01, x1 + dx))
            y2 = min(1, max(y1 + 0.01, y2 + dy))
        elif self.dragging_corner == 3:
            x2 = min(1, max(x1 + 0.01, x2 + dx))
            y2 = min(1, max(y1 + 0.01, y2 + dy))
        
        ann.x_center = (x1 + x2) / 2
        ann.y_center = (y1 + y2) / 2
        ann.width = x2 - x1
        ann.height = y2 - y1
        
        self.update()
    
    def handle_click(self, screen_pos: QPoint, img_pos: Tuple[float, float]):
        for idx, ann in enumerate(self.annotations):
            if ann.contains_point(img_pos[0], img_pos[1]):
                for kp_idx, kp in enumerate(ann.keypoints):
                    kp_screen = self.img_to_screen(kp.x, kp.y)
                    if (kp_screen - screen_pos).manhattanLength() < 10:
                        self.selected_annotation_idx = idx
                        self.selected_keypoint_idx = kp_idx
                        self.keypoint_clicked.emit(idx, kp_idx)
                        self.update()
                        return
                
                self.selected_annotation_idx = idx
                self.selected_keypoint_idx = -1
                self.annotation_clicked.emit(idx)
                self.update()
                return
        
        self.selected_annotation_idx = -1
        self.selected_keypoint_idx = -1
        self.update()
    
    def update_hover(self, screen_pos: QPoint, img_pos: Tuple[float, float]):
        old_hover_ann = self.hover_annotation_idx
        old_hover_kp = self.hover_keypoint_idx
        
        self.hover_annotation_idx = -1
        self.hover_keypoint_idx = -1
        
        for idx, ann in enumerate(self.annotations):
            if ann.contains_point(img_pos[0], img_pos[1]):
                for kp_idx, kp in enumerate(ann.keypoints):
                    kp_screen = self.img_to_screen(kp.x, kp.y)
                    if (kp_screen - screen_pos).manhattanLength() < 10:
                        self.hover_annotation_idx = idx
                        self.hover_keypoint_idx = kp_idx
                        break
                
                if self.hover_keypoint_idx < 0:
                    self.hover_annotation_idx = idx
                break
        
        if (old_hover_ann != self.hover_annotation_idx or 
            old_hover_kp != self.hover_keypoint_idx):
            self.update()
    
    def finish_bbox(self):
        if not self.draw_start or not self.draw_end:
            return
        
        rect = self.get_image_rect()
        x1 = (min(self.draw_start.x(), self.draw_end.x()) - rect.x()) / rect.width()
        y1 = (min(self.draw_start.y(), self.draw_end.y()) - rect.y()) / rect.height()
        x2 = (max(self.draw_start.x(), self.draw_end.x()) - rect.x()) / rect.width()
        y2 = (max(self.draw_start.y(), self.draw_end.y()) - rect.y()) / rect.height()
        
        x1 = max(0, min(1, x1))
        y1 = max(0, min(1, y1))
        x2 = max(0, min(1, x2))
        y2 = max(0, min(1, y2))
        
        if abs(x2 - x1) < 0.01 or abs(y2 - y1) < 0.01:
            return
        
        self.request_save_undo.emit()
        
        x_center = (x1 + x2) / 2
        y_center = (y1 + y2) / 2
        width = x2 - x1
        height = y2 - y1
        
        num_keypoints = len(self.template.keypoints) if self.template else 0
        keypoints = [Keypoint(x=0.5, y=0.5, vis=0) for _ in range(num_keypoints)]
        
        ann = Annotation(
            class_id=0,
            x_center=x_center,
            y_center=y_center,
            width=width,
            height=height,
            keypoints=keypoints
        )
        
        self.annotations.append(ann)
        self.selected_annotation_idx = len(self.annotations) - 1
        self.selected_keypoint_idx = -1
        self.annotation_added.emit()
    
    def add_keypoint_at(self, x: float, y: float):
        if self.selected_annotation_idx < 0:
            return
        if self.current_keypoint_id < 0:
            return
        
        ann = self.annotations[self.selected_annotation_idx]
        
        # 取消关键点必须在框内的限制
        # x = max(ann.x_center - ann.width/2, min(ann.x_center + ann.width/2, x))
        # y = max(ann.y_center - ann.height/2, min(ann.y_center + ann.height/2, y))
        
        while len(ann.keypoints) <= self.current_keypoint_id:
            ann.keypoints.append(Keypoint(x=0.5, y=0.5, vis=0))
        
        ann.keypoints[self.current_keypoint_id] = Keypoint(x=x, y=y, vis=2)
        self.selected_keypoint_idx = self.current_keypoint_id
        self.current_keypoint_id = -1
        self.drawing_mode = None
        self.annotation_modified.emit()
        self.update()
    
    def finish_keypoint_selection(self):
        if not self.kp_select_start or not self.kp_select_end:
            return
        
        if self.selected_annotation_idx < 0:
            return
        
        ann = self.annotations[self.selected_annotation_idx]
        
        sel_rect = QRect(self.kp_select_start, self.kp_select_end).normalized()
        
        self.selected_keypoints_for_copy = []
        for kp_idx, kp in enumerate(ann.keypoints):
            if kp.vis == 0:
                continue
            kp_screen = self.img_to_screen(kp.x, kp.y)
            if sel_rect.contains(kp_screen):
                self.selected_keypoints_for_copy.append((kp_idx, deepcopy(kp)))
        
        self.update()
    
    def copy_selected_keypoints(self):
        if self.selected_keypoints_for_copy:
            self.clipboard_keypoints = deepcopy(self.selected_keypoints_for_copy)
            self.selected_keypoints_for_copy = []
            self.update()
    
    def paste_keypoints(self):
        if not self.clipboard_keypoints:
            return
        if self.selected_annotation_idx < 0:
            return
        
        ann = self.annotations[self.selected_annotation_idx]
        
        for kp_idx, kp in self.clipboard_keypoints:
            while len(ann.keypoints) <= kp_idx:
                ann.keypoints.append(Keypoint(x=0.5, y=0.5, vis=0))
            ann.keypoints[kp_idx] = deepcopy(kp)
        
        self.annotation_modified.emit()
        self.update()
    
    def start_bbox_drawing(self):
        self.drawing_mode = 'bbox'
        self.keypoint_select_mode = False
        self.current_keypoint_id = -1
        self.setCursor(QCursor(Qt.CrossCursor))
    
    def start_keypoint_drawing(self, kp_id: int):
        self.drawing_mode = 'keypoint'
        self.keypoint_select_mode = False
        self.current_keypoint_id = kp_id
        self.setCursor(QCursor(Qt.CrossCursor))
    
    def start_keypoint_select_mode(self):
        self.keypoint_select_mode = True
        self.drawing_mode = None
        self.current_keypoint_id = -1
        self.selected_keypoints_for_copy = []
        self.setCursor(QCursor(Qt.CrossCursor))
    
    def stop_drawing(self):
        self.drawing_mode = None
        self.keypoint_select_mode = False
        self.current_keypoint_id = -1
        self.selected_keypoints_for_copy = []
        self.setCursor(QCursor(Qt.ArrowCursor))
    
    def delete_selected(self) -> bool:
        if self.selected_annotation_idx >= 0:
            self.request_save_undo.emit()
            del self.annotations[self.selected_annotation_idx]
            self.selected_annotation_idx = -1
            self.selected_keypoint_idx = -1
            self.annotation_modified.emit()
            self.update()
            return True
        elif self.selected_keypoint_idx >= 0 and self.selected_annotation_idx >= 0:
            self.request_save_undo.emit()
            ann = self.annotations[self.selected_annotation_idx]
            if self.selected_keypoint_idx < len(ann.keypoints):
                ann.keypoints[self.selected_keypoint_idx].vis = 0
            self.selected_keypoint_idx = -1
            self.annotation_modified.emit()
            self.update()
            return True
        return False
    
    def copy_selected(self):
        if self.selected_keypoints_for_copy:
            self.copy_selected_keypoints()
        elif self.selected_annotation_idx >= 0:
            ann = self.annotations[self.selected_annotation_idx]
            self.clipboard_keypoints = []
            for kp_idx, kp in enumerate(ann.keypoints):
                if kp.vis > 0:
                    self.clipboard_keypoints.append((kp_idx, deepcopy(kp)))
    
    def paste_to_selected(self):
        if not self.clipboard_keypoints:
            return
        if self.selected_annotation_idx < 0:
            return
        
        self.request_save_undo.emit()
        ann = self.annotations[self.selected_annotation_idx]
        
        for kp_idx, kp in self.clipboard_keypoints:
            while len(ann.keypoints) <= kp_idx:
                ann.keypoints.append(Keypoint(x=0.5, y=0.5, vis=0))
            ann.keypoints[kp_idx] = deepcopy(kp)
        
        self.annotation_modified.emit()
        self.update()
    
    def set_annotation_class(self, class_id: int):
        if self.selected_annotation_idx >= 0:
            self.annotations[self.selected_annotation_idx].class_id = class_id
            self.update()
    
    def set_keypoint_vis(self, kp_idx: int, vis: int):
        if self.selected_annotation_idx >= 0:
            self.request_save_undo.emit()
            ann = self.annotations[self.selected_annotation_idx]
            if kp_idx < len(ann.keypoints):
                ann.keypoints[kp_idx].vis = vis
                self.annotation_modified.emit()
                self.update()