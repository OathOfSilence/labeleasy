# -*- coding: utf-8 -*-
"""常量定义"""

from pathlib import Path
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

CONFIG_FILE = Path.home() / '.labeleasy' / 'config.json'
MAX_RECENT_PROJECTS = 20
SUPPORTED_IMAGE_FORMATS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}

KEYPOINT_KEY_MAP = {
    Qt.Key_Q: 0, Qt.Key_W: 1, Qt.Key_E: 2, Qt.Key_R: 3, Qt.Key_T: 4,
    Qt.Key_Y: 5, Qt.Key_U: 6, Qt.Key_I: 7, Qt.Key_O: 8, Qt.Key_P: 9,
    Qt.Key_A: 10, Qt.Key_S: 11, Qt.Key_D: 12, Qt.Key_F: 13, Qt.Key_G: 14,
    Qt.Key_H: 15, Qt.Key_J: 16, Qt.Key_K: 17, Qt.Key_L: 18,
    Qt.Key_Z: 19, Qt.Key_X: 20, Qt.Key_C: 21, Qt.Key_V: 22, Qt.Key_B: 23,
    Qt.Key_N: 24, Qt.Key_M: 25
}

SKELETON_COLORS = [
    QColor(255, 0, 0), QColor(0, 255, 0), QColor(0, 0, 255),
    QColor(255, 255, 0), QColor(255, 0, 255), QColor(0, 255, 255),
    QColor(255, 128, 0), QColor(128, 0, 255), QColor(0, 128, 255),
    QColor(255, 0, 128), QColor(128, 255, 0), QColor(0, 255, 128)
]

KEYBOARD_LAYOUT = [
    ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
    ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L'],
    ['Z', 'X', 'C', 'V', 'B', 'N', 'M']
]