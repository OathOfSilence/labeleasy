# -*- coding: utf-8 -*-
"""Lableasy - YOLO格式图像标注应用"""

__version__ = "0.1.0"
__appname__ = "Lableasy"

from .models import Annotation, Keypoint, Template
from .canvas import Canvas
from .dialogs import ConfigDialog
from .app import MainWindow