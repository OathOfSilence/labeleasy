# -*- coding: utf-8 -*-
"""常量定义"""

from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

CONFIG_FILE = Path.home() / '.labeleasy' / 'config.json'
MAX_RECENT_PROJECTS = 20
SUPPORTED_IMAGE_FORMATS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}

KEYPOINT_KEY_MAP = {
    # 数字键 (0-9)
    Qt.Key.Key_1: 0, Qt.Key.Key_2: 1, Qt.Key.Key_3: 2, Qt.Key.Key_4: 3, Qt.Key.Key_5: 4,
    Qt.Key.Key_6: 5, Qt.Key.Key_7: 6, Qt.Key.Key_8: 7, Qt.Key.Key_9: 8, Qt.Key.Key_0: 9,
    # 符号键 (10-16)
    Qt.Key.Key_Minus: 10, Qt.Key.Key_Equal: 11, Qt.Key.Key_BracketLeft: 12, Qt.Key.Key_BracketRight: 13,
    Qt.Key.Key_Backslash: 14, Qt.Key.Key_Semicolon: 15, Qt.Key.Key_Apostrophe: 16,
    # 字母键 QWERTY (17-26)
    Qt.Key.Key_Q: 17, Qt.Key.Key_W: 18, Qt.Key.Key_E: 19, Qt.Key.Key_R: 20, Qt.Key.Key_T: 21,
    Qt.Key.Key_Y: 22, Qt.Key.Key_U: 23, Qt.Key.Key_I: 24, Qt.Key.Key_O: 25, Qt.Key.Key_P: 26,
    # 字母键 ASDF (27-35)
    Qt.Key.Key_A: 27, Qt.Key.Key_S: 28, Qt.Key.Key_D: 29, Qt.Key.Key_F: 30, Qt.Key.Key_G: 31,
    Qt.Key.Key_H: 32, Qt.Key.Key_J: 33, Qt.Key.Key_K: 34, Qt.Key.Key_L: 35,
    # 字母键 ZXCV + 符号 (36-45)
    Qt.Key.Key_Z: 36, Qt.Key.Key_X: 37, Qt.Key.Key_C: 38, Qt.Key.Key_V: 39, Qt.Key.Key_B: 40,
    Qt.Key.Key_N: 41, Qt.Key.Key_M: 42, Qt.Key.Key_Comma: 43, Qt.Key.Key_Period: 44, Qt.Key.Key_Slash: 45
}

SKELETON_COLORS = [
    QColor(255, 0, 0), QColor(0, 255, 0), QColor(0, 0, 255),
    QColor(255, 255, 0), QColor(255, 0, 255), QColor(0, 255, 255),
    QColor(255, 128, 0), QColor(128, 0, 255), QColor(0, 128, 255),
    QColor(255, 0, 128), QColor(128, 255, 0), QColor(0, 255, 128)
]

KEYBOARD_LAYOUT = [
    ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
    ['-', '=', '[', ']', '\\', ';', "'"],
    ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
    ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L'],
    ['Z', 'X', 'C', 'V', 'B', 'N', 'M', ',', '.', '/']
]