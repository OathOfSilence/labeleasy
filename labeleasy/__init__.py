# -*- coding: utf-8 -*-
"""Labeleasy - YOLO 格式图像标注应用"""

__version__ = "3.0.0"
__appname__ = "Labeleasy"

from .models import Annotation, Keypoint, Template
from .canvas import Canvas
from .dialogs import ConfigDialog
from .app import MainWindow
