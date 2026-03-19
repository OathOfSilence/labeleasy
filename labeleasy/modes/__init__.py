# -*- coding: utf-8 -*-
"""标注模式模块"""

from .base import AnnotationMode
from .keypoint import KeypointMode
from .edge import EdgeMode
from .drawing import BboxDrawingMode

__all__ = ['AnnotationMode', 'KeypointMode', 'EdgeMode', 'BboxDrawingMode']
