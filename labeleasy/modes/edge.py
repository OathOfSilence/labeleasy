# -*- coding: utf-8 -*-
"""框选边模式（纯目标检测）"""

from typing import Optional, Any, Tuple, List, Dict

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QCursor

from .base import AnnotationMode


class EdgeMode(AnnotationMode):
    """框选边模式 - 用于纯目标检测时跨图对齐边框"""
    
    def __init__(self, canvas):
        super().__init__(canvas)
        self.select_start: Optional[QPoint] = None
        self.select_end: Optional[QPoint] = None
        self.drawing = False
        # 支持多选：List[{'ann_idx': int, 'type': str, 'value': float, 'label': str}]
        self.selected_edges: List[Dict] = []
    
    def enter(self):
        if self.canvas.selected_annotation_idx < 0:
            return
        self.select_start = None
        self.select_end = None
        self.drawing = False
        # 不清空 selected_edges，支持累积选择
    
    def exit(self):
        self.drawing = False
        # 不清空 selected_edges，保持选中状态
    
    def on_mouse_press(self, event) -> bool:
        if event.button() != Qt.MouseButton.LeftButton:
            return False
        
        if self.canvas.selected_annotation_idx < 0:
            return False
        
        screen_pos = event.position().toPoint()
        
        # Ctrl+ 点击：切换单个边的选中状态
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self._toggle_edge_selection(screen_pos)
            return True
        
        # 普通点击：开始框选（清空已有选中，刷新模式）
        self.selected_edges = []
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
        # 绘制框选矩形
        if self.drawing and self.select_start and self.select_end:
            pen = QPen(QColor(255, 165, 0), 2, Qt.PenStyle.DashLine)  # 橙色
            painter.setPen(pen)
            painter.setBrush(QBrush(QColor(255, 165, 0, 30)))
            painter.drawRect(QRect(self.select_start, self.select_end))
        
        # 绘制选中的边（特效）
        self._draw_selected_edges(painter)
    
    def _draw_selected_edges(self, painter: QPainter):
        """绘制选中的边特效"""
        for edge_info in self.selected_edges:
            ann_idx = edge_info['ann_idx']
            if ann_idx >= len(self.canvas.annotations):
                continue
            
            ann = self.canvas.annotations[ann_idx]
            x1, y1, x2, y2 = ann.get_bbox_coords()
            
            edge_type = edge_info['type']
            
            # 根据边类型确定绘制位置
            if edge_type == 'left':
                p1 = self.canvas.img_to_screen(x1, y1)
                p2 = self.canvas.img_to_screen(x1, y2)
            elif edge_type == 'right':
                p1 = self.canvas.img_to_screen(x2, y1)
                p2 = self.canvas.img_to_screen(x2, y2)
            elif edge_type == 'top':
                p1 = self.canvas.img_to_screen(x1, y1)
                p2 = self.canvas.img_to_screen(x2, y1)
            elif edge_type == 'bottom':
                p1 = self.canvas.img_to_screen(x1, y2)
                p2 = self.canvas.img_to_screen(x2, y2)
            else:
                continue
            
            # 绘制高亮边（粗线 + 亮色）
            pen = QPen(QColor(0, 255, 255), 4, Qt.PenStyle.SolidLine)  # 青色粗线
            painter.setPen(pen)
            painter.drawLine(p1, p2)
    
    def _toggle_edge_selection(self, screen_pos: QPoint):
        """Ctrl+ 点击切换边的选中状态"""
        if self.canvas.selected_annotation_idx < 0:
            return
        
        ann_idx = self.canvas.selected_annotation_idx
        ann = self.canvas.annotations[ann_idx]
        x1, y1, x2, y2 = ann.get_bbox_coords()
        
        # 计算四条边的屏幕坐标
        edges = [
            ('left', self.canvas.img_to_screen(x1, y1), self.canvas.img_to_screen(x1, y2)),
            ('right', self.canvas.img_to_screen(x2, y1), self.canvas.img_to_screen(x2, y2)),
            ('top', self.canvas.img_to_screen(x1, y1), self.canvas.img_to_screen(x2, y1)),
            ('bottom', self.canvas.img_to_screen(x1, y2), self.canvas.img_to_screen(x2, y2)),
        ]
        
        # 查找点击的边（距离 < 15 像素）
        for edge_type, p1, p2 in edges:
            dist = self._point_to_line_distance(screen_pos, p1, p2)
            if dist < 15:
                existing_idx = next(
                    (i for i, e in enumerate(self.selected_edges) 
                     if e['ann_idx'] == ann_idx and e['type'] == edge_type),
                    None
                )
                if existing_idx is not None:
                    self.selected_edges.pop(existing_idx)
                else:
                    value = {'left': x1, 'right': x2, 'top': y1, 'bottom': y2}[edge_type]
                    label = {'left': '左边', 'right': '右边', 'top': '上边', 'bottom': '下边'}[edge_type]
                    self.selected_edges.append({
                        'ann_idx': ann_idx,
                        'type': edge_type,
                        'value': value,
                        'label': label
                    })
                self.canvas.update()
                return
    
    def _point_to_line_distance(self, point: QPoint, line_start: QPoint, line_end: QPoint) -> float:
        """计算点到线段的最短距离"""
        dx = line_end.x() - line_start.x()
        dy = line_end.y() - line_start.y()
        
        if dx == 0 and dy == 0:
            return ((point.x() - line_start.x())**2 + (point.y() - line_start.y())**2) ** 0.5
        
        t = max(0, min(1, ((point.x() - line_start.x()) * dx + (point.y() - line_start.y()) * dy) / (dx * dx + dy * dy)))
        proj_x = line_start.x() + t * dx
        proj_y = line_start.y() + t * dy
        
        return ((point.x() - proj_x)**2 + (point.y() - proj_y)**2) ** 0.5
    
    def _finish_selection(self):
        """完成框选，选择所有被框选的边"""
        if not self.select_start or not self.select_end:
            return
        
        if self.canvas.selected_annotation_idx < 0:
            return
        
        ann = self.canvas.annotations[self.canvas.selected_annotation_idx]
        x1, y1, x2, y2 = ann.get_bbox_coords()
        
        sel_rect = QRect(self.select_start, self.select_end).normalized()
        
        # 计算四条边的屏幕坐标
        edges = [
            ('left', self.canvas.img_to_screen(x1, y1), self.canvas.img_to_screen(x1, y2), x1, '左边'),
            ('right', self.canvas.img_to_screen(x2, y1), self.canvas.img_to_screen(x2, y2), x2, '右边'),
            ('top', self.canvas.img_to_screen(x1, y1), self.canvas.img_to_screen(x2, y1), y1, '上边'),
            ('bottom', self.canvas.img_to_screen(x1, y2), self.canvas.img_to_screen(x2, y2), y2, '下边'),
        ]
        
        # 检查每条边是否与框选矩形相交
        for edge_type, p1, p2, value, label in edges:
            # 检查边的两个端点是否在矩形内，或边与矩形相交
            if self._edge_intersects_rect(p1, p2, sel_rect):
                # 检查是否已存在
                if not any(e['ann_idx'] == self.canvas.selected_annotation_idx and e['type'] == edge_type 
                          for e in self.selected_edges):
                    self.selected_edges.append({
                        'ann_idx': self.canvas.selected_annotation_idx,
                        'type': edge_type,
                        'value': value,
                        'label': label
                    })
        
        self.canvas.update()
    
    def _edge_intersects_rect(self, p1: QPoint, p2: QPoint, rect: QRect) -> bool:
        """检查线段是否与矩形相交（或完全在矩形内）"""
        # 如果两个端点都在矩形内，返回 True
        if rect.contains(p1) and rect.contains(p2):
            return True
        
        # 检查线段是否与矩形的四条边相交
        rect_edges = [
            (rect.topLeft(), rect.topRight()),
            (rect.topRight(), rect.bottomRight()),
            (rect.bottomRight(), rect.bottomLeft()),
            (rect.bottomLeft(), rect.topLeft()),
        ]
        
        for re_p1, re_p2 in rect_edges:
            if self._lines_intersect(p1, p2, re_p1, re_p2):
                return True
        
        return False
    
    def _lines_intersect(self, p1: QPoint, p2: QPoint, p3: QPoint, p4: QPoint) -> bool:
        """检查两条线段是否相交"""
        def ccw(a, b, c):
            return (c.y() - a.y()) * (b.x() - a.x()) > (b.y() - a.y()) * (c.x() - a.x())
        
        return (ccw(p1, p3, p4) != ccw(p2, p3, p4)) and (ccw(p1, p2, p3) != ccw(p1, p2, p4))
    
    def copy(self) -> Optional[Any]:
        """复制选中的边"""
        if self.selected_edges:
            return [e.copy() for e in self.selected_edges]
        return None
    
    def paste(self, data: Any) -> Tuple[bool, str]:
        """粘贴边信息"""
        if not data or self.canvas.selected_annotation_idx < 0:
            return (False, "无法粘贴")
        
        success_count = 0
        messages = []
        
        for edge_info in data:
            ann = self.canvas.annotations[self.canvas.selected_annotation_idx]
            x1, y1, x2, y2 = ann.get_bbox_coords()
            
            edge_type = edge_info['type']
            edge_value = edge_info['value']
            
            new_coords = {}
            if edge_type == 'left':
                if edge_value >= x2 - 0.001:
                    messages.append(f"冲突：左边 x={edge_value:.4f} >= 右边")
                    continue
                new_coords = {'x1': edge_value}
            elif edge_type == 'right':
                if edge_value <= x1 + 0.001:
                    messages.append(f"冲突：右边 x={edge_value:.4f} <= 左边")
                    continue
                new_coords = {'x2': edge_value}
            elif edge_type == 'top':
                if edge_value >= y2 - 0.001:
                    messages.append(f"冲突：上边 y={edge_value:.4f} >= 下边")
                    continue
                new_coords = {'y1': edge_value}
            elif edge_type == 'bottom':
                if edge_value <= y1 + 0.001:
                    messages.append(f"冲突：下边 y={edge_value:.4f} <= 上边")
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
            self.canvas.annotation_modified.emit()
            self.canvas.update()
            msg = f"已粘贴 {success_count} 条边"
            if messages:
                msg += f" ({len(messages)} 个冲突)"
            return (True, msg)
        else:
            return (False, "所有边都冲突，粘贴失败")
    
    def get_status_message(self) -> str:
        if self.selected_edges:
            return f"框选边模式：已选中 {len(self.selected_edges)} 条边，Ctrl+ 点击切换，Ctrl+C 复制"
        return "框选边模式：拖动框选边，Ctrl+ 点击切换选中，Ctrl+C 复制，Ctrl+V 粘贴"
    
    def get_cursor(self) -> QCursor:
        return QCursor(Qt.CursorShape.CrossCursor)
