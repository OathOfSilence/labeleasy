# -*- coding: utf-8 -*-
"""标注模式基类"""

from typing import Optional, Any, Dict, List, Tuple
from abc import ABC, abstractmethod

from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QPainter


class AnnotationMode(ABC):
    """标注模式基类"""
    
    def __init__(self, canvas):
        self.canvas = canvas
    
    @property
    def name(self) -> str:
        """模式名称"""
        return self.__class__.__name__
    
    def enter(self):
        """进入模式时调用"""
        pass
    
    def exit(self):
        """离开模式时调用"""
        pass
    
    @abstractmethod
    def on_mouse_press(self, event) -> bool:
        """处理鼠标按下事件
        Returns: True 表示已处理，False 表示继续传递
        """
        pass
    
    @abstractmethod
    def on_mouse_move(self, event) -> bool:
        """处理鼠标移动事件
        Returns: True 表示已处理，False 表示继续传递
        """
        pass
    
    @abstractmethod
    def on_mouse_release(self, event) -> bool:
        """处理鼠标释放事件
        Returns: True 表示已处理，False 表示继续传递
        """
        pass
    
    @abstractmethod
    def draw_overlay(self, painter: QPainter, img_rect: QRect):
        """绘制模式覆盖层"""
        pass
    
    def copy(self) -> Optional[Any]:
        """复制当前选中内容
        Returns: 复制的数据
        """
        return None
    
    def paste(self, data: Any) -> Tuple[bool, str]:
        """粘贴数据
        Returns: (success, message)
        """
        return (False, "不支持粘贴")
    
    def get_status_message(self) -> str:
        """获取状态栏提示信息"""
        return ""
    
    def get_cursor(self):
        """获取鼠标光标样式"""
        from PySide6.QtGui import QCursor
        from PySide6.QtCore import Qt
        return QCursor(Qt.CursorShape.ArrowCursor)
