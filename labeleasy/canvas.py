# -*- coding: utf-8 -*-
"""画布组件 - 核心渲染和事件分发"""

from typing import List, Tuple, Optional, Any
from copy import deepcopy

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QPoint, QRect, Signal
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QPixmap, QImage, QCursor
)
import cv2
import numpy as np

from .models import Annotation, Keypoint, Template
from .constants import SKELETON_COLORS, KEYBOARD_LAYOUT
from .modes import AnnotationMode, KeypointMode, EdgeMode, BboxDrawingMode


class Canvas(QWidget):
    """画布组件 - 负责图像渲染和标注绘制"""
    
    annotation_clicked = Signal(int)
    keypoint_clicked = Signal(int, int)
    annotation_added = Signal()
    annotation_modified = Signal()
    request_save_undo = Signal()
    
    CORNER_SIZE = 8
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 核心数据
        self.image: Optional[np.ndarray] = None
        self.image_path: Optional[str] = None
        self.annotations: List[Annotation] = []
        self.template: Optional[Template] = None
        self.scale = 1.0
        self.offset = QPoint(0, 0)
        
        # 选中状态
        self.selected_annotation_idx = -1
        self.selected_keypoint_idx = -1
        self.hover_annotation_idx = -1
        self.hover_keypoint_idx = -1
        
        # 模式管理
        self.current_mode: Optional[AnnotationMode] = None
        self.modes = {
            'keypoint': KeypointMode(self),
            'edge': EdgeMode(self),
            'drawing': BboxDrawingMode(self),
        }
        
        # 关键点绘制模式（有关键点模板时使用）
        self.drawing_keypoint: bool = False
        self.current_keypoint_id: int = -1
        
        # 拖动状态
        self.dragging_corner: Optional[int] = None
        self.drag_start_pos: Optional[QPoint] = None
        self.drag_start_ann: Optional[Annotation] = None
        self.dragging_keypoint_idx: Optional[int] = None
        self.drag_keypoint_start_pos: Optional[QPoint] = None
        
        # 全局剪贴板（跨模式）
        self.clipboard: Any = None
        
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(400, 300)
    
    # ========== 模式管理 ==========
    
    def set_mode(self, mode_name: str):
        """切换到指定模式"""
        if self.current_mode:
            self.current_mode.exit()
        
        self.current_mode = self.modes.get(mode_name)
        if self.current_mode:
            self.current_mode.enter()
            self.setCursor(self.current_mode.get_cursor())
    
    def pop_mode(self):
        """返回上一个模式（或普通模式）"""
        if self.current_mode:
            self.current_mode.exit()
        
        self.current_mode = None
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
    
    def stop_all_modes(self):
        """停止所有模式"""
        if self.current_mode:
            self.current_mode.exit()
            self.current_mode = None
        self.drawing_keypoint = False
        self.current_keypoint_id = -1
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
    
    def start_keypoint_drawing(self, kp_id: int):
        """进入关键点绘制模式"""
        self.drawing_keypoint = True
        self.current_keypoint_id = kp_id
        # 退出其他模式
        if self.current_mode:
            self.current_mode.exit()
            self.current_mode = None
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
    
    def add_keypoint_at(self, x: float, y: float):
        """在指定位置添加关键点"""
        if self.selected_annotation_idx < 0:
            return
        if self.current_keypoint_id < 0:
            return
        
        ann = self.annotations[self.selected_annotation_idx]
        
        while len(ann.keypoints) <= self.current_keypoint_id:
            ann.keypoints.append(Keypoint(x=0.5, y=0.5, vis=0))
        
        ann.keypoints[self.current_keypoint_id] = Keypoint(x=x, y=y, vis=2)
        self.selected_keypoint_idx = self.current_keypoint_id
        self.current_keypoint_id = -1
        self.drawing_keypoint = False
        self.annotation_modified.emit()
        self.update()
    
    # ========== 图像操作 ==========
    
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
        self.selected_annotation_idx = 0 if annotations else -1
        self.selected_keypoint_idx = -1
        self.update()
    
    def set_template(self, template: Template):
        self.template = template
        self.update()
    
    def fit_to_window(self):
        """调整缩放使图像适应窗口"""
        if self.image is None:
            return
        
        h, w = self.image.shape[:2]
        view_w, view_h = self.width(), self.height()
        
        if view_w <= 0 or view_h <= 0:
            return
        
        if w <= view_w and h <= view_h:
            self.scale = 1.0
        else:
            self.scale = min(view_w / w, view_h / h)
        
        self.offset.setX(0)
        self.offset.setY(0)
        self.update()
    
    # ========== 坐标转换 ==========
    
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
        return (ix, iy)
    
    # ========== 事件处理 ==========
    
    def mousePressEvent(self, event):
        # 关键点绘制模式
        if self.drawing_keypoint and self.current_keypoint_id >= 0:
            if event.button() == Qt.MouseButton.LeftButton:
                img_pos = self.screen_to_img(event.position().x(), event.position().y())
                self.request_save_undo.emit()
                self.add_keypoint_at(img_pos[0], img_pos[1])
            return
        
        # 优先交给当前模式处理
        if self.current_mode:
            if self.current_mode.on_mouse_press(event):
                return
        
        # 模式未处理：检查拖动关键点
        if event.button() == Qt.MouseButton.LeftButton:
            screen_pos = event.position().toPoint()
            if self.selected_annotation_idx >= 0:
                # 检查是否点击在关键点上（用于拖动）
                kp_idx = self._get_keypoint_at_pos(screen_pos)
                if kp_idx is not None:
                    self.request_save_undo.emit()
                    self.dragging_keypoint_idx = kp_idx
                    self.drag_keypoint_start_pos = screen_pos
                    return
                
                # 检查是否点击角点（用于调整框大小）
                corner = self._get_corner_at_pos(screen_pos, self.selected_annotation_idx)
                if corner is not None:
                    self.request_save_undo.emit()
                    self.dragging_corner = corner
                    self.drag_start_pos = screen_pos
                    self.drag_start_ann = deepcopy(self.annotations[self.selected_annotation_idx])
                    return
        
        # 普通点击：选择标注框
        self._handle_click(event)
    
    def mouseMoveEvent(self, event):
        # 优先交给当前模式处理
        if self.current_mode:
            if self.current_mode.on_mouse_move(event):
                return
        
        # 拖动角点
        if self.dragging_corner is not None:
            self._drag_resize_bbox(event.position().toPoint())
            return
        
        # 拖动关键点
        if self.dragging_keypoint_idx is not None:
            self._drag_keypoint(event.position().toPoint())
            return
        
        # 更新悬停状态
        screen_pos = event.position().toPoint()
        img_pos = self.screen_to_img(screen_pos.x(), screen_pos.y())
        self._update_hover(screen_pos, img_pos)
    
    def mouseReleaseEvent(self, event):
        # 优先交给当前模式处理
        if self.current_mode:
            if self.current_mode.on_mouse_release(event):
                return
        
        if event.button() == Qt.MouseButton.LeftButton:
            # 释放拖动
            if self.dragging_corner is not None:
                self.dragging_corner = None
                self.drag_start_pos = None
                self.drag_start_ann = None
                self.annotation_modified.emit()
                return
            
            if self.dragging_keypoint_idx is not None:
                self.dragging_keypoint_idx = None
                self.drag_keypoint_start_pos = None
                self.annotation_modified.emit()
                return
    
    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta == 0 or self.image is None:
            return
        
        mouse_pos = event.position().toPoint()
        img_x, img_y = self.screen_to_img(mouse_pos.x(), mouse_pos.y())
        
        if delta > 0:
            self.scale *= 1.1
        else:
            self.scale /= 1.1
        self.scale = max(0.2, min(5.0, self.scale))
        
        h, w = self.image.shape[:2]
        img_w = w * self.scale
        img_h = h * self.scale
        
        new_offset_x = mouse_pos.x() - img_x * img_w - (self.width() - img_w) / 2
        new_offset_y = mouse_pos.y() - img_y * img_h - (self.height() - img_h) / 2
        
        self.offset.setX(int(new_offset_x))
        self.offset.setY(int(new_offset_y))
        self.update()
    
    # ========== 绘制 ==========
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if self.image is None:
            painter.fillRect(self.rect(), QColor(50, 50, 50))
            painter.setPen(QColor(200, 200, 200))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "请打开图像")
            return
        
        h, w, c = self.image.shape
        qimg = QImage(self.image.data, w, h, 3 * w, QImage.Format.Format_RGB888)
        scaled_pixmap = QPixmap.fromImage(qimg)
        
        img_rect = self.get_image_rect()
        painter.drawPixmap(img_rect, scaled_pixmap.scaled(
            img_rect.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        ))
        
        self._draw_annotations(painter, img_rect)
        
        # 当前模式覆盖层
        if self.current_mode:
            self.current_mode.draw_overlay(painter, img_rect)
        
        # 关键点绘制模式指示器
        if self.drawing_keypoint and self.current_keypoint_id >= 0:
            # 获取当前鼠标位置
            cursor_pos = self.mapFromGlobal(self.cursor().pos())
            pen = QPen(QColor(255, 0, 255), 2)
            painter.setPen(pen)
            painter.setBrush(QBrush(QColor(255, 0, 255, 100)))
            painter.drawEllipse(cursor_pos, 10, 10)
            
            # 显示当前关键点名称
            if self.template and self.current_keypoint_id < len(self.template.keypoints):
                kp_name = self.template.keypoints[self.current_keypoint_id]
                shortcut = self.get_keypoint_shortcut(self.current_keypoint_id)
                painter.setPen(QPen(Qt.GlobalColor.white, 1))
                font = QFont()
                font.setPointSize(10)
                font.setBold(True)
                painter.setFont(font)
                painter.drawText(cursor_pos.x() + 15, cursor_pos.y() - 5, f"[{shortcut}] {kp_name}")
    
    def _draw_annotations(self, painter: QPainter, img_rect: QRect):
        for idx, ann in enumerate(self.annotations):
            self._draw_annotation(painter, ann, idx, img_rect)
    
    def _draw_annotation(self, painter: QPainter, ann: Annotation, idx: int, img_rect: QRect):
        x1, y1, x2, y2 = ann.get_bbox_coords()
        p1 = self.img_to_screen(x1, y1)
        p2 = self.img_to_screen(x2, y2)
        
        is_selected = idx == self.selected_annotation_idx
        is_hover = idx == self.hover_annotation_idx
        
        if is_selected:
            color, width = QColor(0, 255, 0), 3
        elif is_hover:
            color, width = QColor(255, 255, 0), 2
        else:
            color, width = QColor(255, 0, 0), 2
        
        pen = QPen(color, width)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRect(p1, p2))
        
        # 选中时绘制角点
        if is_selected:
            self._draw_corners(painter, p1, p2)
        
        # 骨架连线
        if self.template and idx == self.selected_annotation_idx:
            self._draw_skeleton(painter, ann, img_rect)
        
        # 关键点
        self._draw_keypoints(painter, ann, idx, img_rect)
        
        # 标签
        label = self.template.names[ann.class_id] if (self.template and ann.class_id < len(self.template.names)) else str(ann.class_id)
        painter.setPen(QPen(Qt.GlobalColor.white, 1))
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(p1.x() + 2, p1.y() - 5, label)
    
    def _draw_corners(self, painter: QPainter, p1: QPoint, p2: QPoint):
        corners = self._get_corner_points(p1, p2)
        painter.setBrush(QBrush(QColor(0, 255, 0)))
        for corner in corners:
            painter.drawRect(QRect(corner.x() - self.CORNER_SIZE//2, corner.y() - self.CORNER_SIZE//2, self.CORNER_SIZE, self.CORNER_SIZE))
    
    def _draw_skeleton(self, painter: QPainter, ann: Annotation, img_rect: QRect):
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
                        kp1, kp2 = ann.keypoints[kp1_idx], ann.keypoints[kp2_idx]
                        if kp1.vis > 0 and kp2.vis > 0:
                            p1 = self.img_to_screen(kp1.x, kp1.y)
                            p2 = self.img_to_screen(kp2.x, kp2.y)
                            painter.drawLine(p1, p2)
    
    def _draw_keypoints(self, painter: QPainter, ann: Annotation, ann_idx: int, img_rect: QRect):
        for kp_idx, kp in enumerate(ann.keypoints):
            if kp.vis == 0:
                continue
            
            pos = self.img_to_screen(kp.x, kp.y)
            color = QColor(0, 255, 0) if kp.vis == 2 else QColor(255, 165, 0)
            
            is_selected = ann_idx == self.selected_annotation_idx and kp_idx == self.selected_keypoint_idx
            is_hover = ann_idx == self.hover_annotation_idx and kp_idx == self.hover_keypoint_idx
            
            # 检查是否被框选选中（用于复制）
            is_copy_selected = False
            if self.current_mode and hasattr(self.current_mode, 'selected_for_copy'):
                is_copy_selected = any(sk[0] == kp_idx for sk in self.current_mode.selected_for_copy)
            
            if is_copy_selected:
                # 框选选中的关键点：青色，大尺寸
                brush, radius = QBrush(QColor(0, 255, 255)), 9
            elif is_selected:
                brush, radius = QBrush(QColor(255, 0, 255)), 8
            elif is_hover:
                brush, radius = QBrush(QColor(255, 255, 0)), 6
            else:
                brush, radius = QBrush(color), 5
            
            painter.setPen(QPen(Qt.GlobalColor.black, 1))
            painter.setBrush(brush)
            painter.drawEllipse(pos, radius, radius)
            
            if self.template and ann_idx == self.selected_annotation_idx:
                shortcut = self.get_keypoint_shortcut(kp_idx)
                painter.setPen(QPen(Qt.GlobalColor.white, 1))
                font = QFont()
                font.setPointSize(8)
                font.setBold(True)
                painter.setFont(font)
                painter.drawText(pos.x() + 8, pos.y() - 3, f"[{shortcut}]")
    
    # ========== 辅助方法 ==========
    
    def _get_corner_points(self, p1: QPoint, p2: QPoint) -> List[QPoint]:
        return [p1, QPoint(p2.x(), p1.y()), QPoint(p1.x(), p2.y()), p2]
    
    def _get_corner_at_pos(self, screen_pos: QPoint, ann_idx: int) -> Optional[int]:
        if ann_idx < 0 or ann_idx >= len(self.annotations):
            return None
        
        ann = self.annotations[ann_idx]
        x1, y1, x2, y2 = ann.get_bbox_coords()
        p1 = self.img_to_screen(x1, y1)
        p2 = self.img_to_screen(x2, y2)
        corners = self._get_corner_points(p1, p2)
        
        for i, corner in enumerate(corners):
            if (corner - screen_pos).manhattanLength() < self.CORNER_SIZE + 5:
                return i
        return None
    
    def _get_keypoint_at_pos(self, screen_pos: QPoint) -> Optional[int]:
        """获取鼠标位置下的关键点索引（用于拖动）"""
        if self.selected_annotation_idx < 0:
            return None
        if not self.template:
            return None
        
        ann = self.annotations[self.selected_annotation_idx]
        
        for kp_idx, kp in enumerate(ann.keypoints):
            if kp.vis == 0:
                continue
            kp_screen = self.img_to_screen(kp.x, kp.y)
            dx = screen_pos.x() - kp_screen.x()
            dy = screen_pos.y() - kp_screen.y()
            if dx * dx + dy * dy <= 100:  # 10 像素范围
                return kp_idx
        
        return None
    
    def _handle_click(self, event):
        """处理普通点击：选择标注框或关键点"""
        img_pos = self.screen_to_img(event.position().x(), event.position().y())
        screen_pos = event.position().toPoint()
        
        for idx, ann in enumerate(self.annotations):
            if ann.contains_point(img_pos[0], img_pos[1]):
                # 检查是否点击关键点
                for kp_idx, kp in enumerate(ann.keypoints):
                    kp_screen = self.img_to_screen(kp.x, kp.y)
                    if (kp_screen - screen_pos).manhattanLength() < 10:
                        self.selected_annotation_idx = idx
                        self.selected_keypoint_idx = kp_idx
                        self.keypoint_clicked.emit(idx, kp_idx)
                        self.update()
                        return
                
                # 点击标注框
                self.selected_annotation_idx = idx
                self.selected_keypoint_idx = -1
                self.annotation_clicked.emit(idx)
                self.update()
                return
        
        # 点击空白
        self.selected_annotation_idx = -1
        self.selected_keypoint_idx = -1
        self.update()
    
    def _update_hover(self, screen_pos: QPoint, img_pos: Tuple[float, float]):
        old_ann, old_kp = self.hover_annotation_idx, self.hover_keypoint_idx
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
        
        if old_ann != self.hover_annotation_idx or old_kp != self.hover_keypoint_idx:
            self.update()
    
    def _drag_resize_bbox(self, screen_pos: QPoint):
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
            x1, y1 = max(0, min(x2 - 0.01, x1 + dx)), max(0, min(y2 - 0.01, y1 + dy))
        elif self.dragging_corner == 1:
            x2, y1 = min(1, max(x1 + 0.01, x2 + dx)), max(0, min(y2 - 0.01, y1 + dy))
        elif self.dragging_corner == 2:
            x1, y2 = max(0, min(x2 - 0.01, x1 + dx)), min(1, max(y1 + 0.01, y2 + dy))
        elif self.dragging_corner == 3:
            x2, y2 = min(1, max(x1 + 0.01, x2 + dx)), min(1, max(y1 + 0.01, y2 + dy))
        
        ann.x_center, ann.y_center = (x1 + x2) / 2, (y1 + y2) / 2
        ann.width, ann.height = x2 - x1, y2 - y1
        self.update()
    
    def _drag_keypoint(self, screen_pos: QPoint):
        if self.dragging_keypoint_idx is None or self.selected_annotation_idx < 0:
            return
        
        ann = self.annotations[self.selected_annotation_idx]
        if self.dragging_keypoint_idx >= len(ann.keypoints):
            return
        
        img_x, img_y = self.screen_to_img(screen_pos.x(), screen_pos.y())
        img_x, img_y = max(0, min(1, img_x)), max(0, min(1, img_y))
        
        kp = ann.keypoints[self.dragging_keypoint_idx]
        kp.x, kp.y, kp.vis = img_x, img_y, 2
        self.update()
    
    # ========== 工具方法 ==========
    
    def get_keypoint_shortcut(self, kp_idx: int) -> str:
        idx = 0
        for row in KEYBOARD_LAYOUT:
            for ch in row:
                if idx == kp_idx:
                    return ch
                idx += 1
        return "?"
    
    def copy(self):
        """复制当前选中内容"""
        if self.current_mode:
            data = self.current_mode.copy()
            if data:
                self.clipboard = data
    
    def paste(self) -> Tuple[bool, str]:
        """粘贴内容"""
        if not self.clipboard:
            return (False, "剪贴板为空")
        if self.selected_annotation_idx < 0:
            return (False, "请先选择目标标注框")
        
        # 根据剪贴板数据类型判断粘贴方式
        if isinstance(self.clipboard, list) and len(self.clipboard) > 0:
            first_item = self.clipboard[0]
            if isinstance(first_item, tuple) and len(first_item) == 2:
                # 关键点数据：List[Tuple[int, Keypoint]]
                return self._paste_keypoints(self.clipboard)
            elif isinstance(first_item, dict):
                # 边数据：List[Dict]
                return self._paste_edges(self.clipboard)
        
        return (False, "无法识别剪贴板数据格式")
    
    def _paste_keypoints(self, data: Any) -> Tuple[bool, str]:
        """粘贴关键点"""
        if not data or self.selected_annotation_idx < 0:
            return (False, "无法粘贴")
        
        self.request_save_undo.emit()
        ann = self.annotations[self.selected_annotation_idx]
        
        count = 0
        for kp_idx, kp in data:
            while len(ann.keypoints) <= kp_idx:
                ann.keypoints.append(Keypoint(x=0.5, y=0.5, vis=0))
            ann.keypoints[kp_idx] = deepcopy(kp)
            count += 1
        
        self.annotation_modified.emit()
        self.update()
        return (True, f"已粘贴 {count} 个关键点")
    
    def _paste_edges(self, data: Any) -> Tuple[bool, str]:
        """粘贴边"""
        if not data or self.selected_annotation_idx < 0:
            return (False, "无法粘贴")
        
        success_count = 0
        messages = []
        
        for edge_info in data:
            ann = self.annotations[self.selected_annotation_idx]
            x1, y1, x2, y2 = ann.get_bbox_coords()
            
            edge_type = edge_info['type']
            edge_value = edge_info['value']
            
            new_coords = {}
            if edge_type == 'left':
                if edge_value >= x2 - 0.001:
                    messages.append(f"冲突：左边 >= 右边")
                    continue
                new_coords = {'x1': edge_value}
            elif edge_type == 'right':
                if edge_value <= x1 + 0.001:
                    messages.append(f"冲突：右边 <= 左边")
                    continue
                new_coords = {'x2': edge_value}
            elif edge_type == 'top':
                if edge_value >= y2 - 0.001:
                    messages.append(f"冲突：上边 >= 下边")
                    continue
                new_coords = {'y1': edge_value}
            elif edge_type == 'bottom':
                if edge_value <= y1 + 0.001:
                    messages.append(f"冲突：下边 <= 上边")
                    continue
                new_coords = {'y2': edge_value}
            
            if new_coords:
                x1 = new_coords.get('x1', x1)
                y1 = new_coords.get('y1', y1)
                x2 = new_coords.get('x2', x2)
                y2 = new_coords.get('y2', y2)
                ann.x_center = (x1 + x2) / 2
                ann.y_center = (y1 + y2) / 2
                ann.width = x2 - x1
                ann.height = y2 - y1
                success_count += 1
        
        if success_count > 0:
            self.annotation_modified.emit()
            self.update()
            msg = f"已粘贴 {success_count} 条边"
            if messages:
                msg += f" ({len(messages)} 个冲突)"
            return (True, msg)
        else:
            return (False, "所有边都冲突，粘贴失败")
    
    def set_annotation_class(self, class_id: int):
        """设置选中标注框的类别"""
        if self.selected_annotation_idx >= 0 and self.selected_annotation_idx < len(self.annotations):
            self.annotations[self.selected_annotation_idx].class_id = class_id
            self.update()
    
    def delete_selected(self) -> bool:
        """删除选中的标注或关键点"""
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
