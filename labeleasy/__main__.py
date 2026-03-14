# -*- coding: utf-8 -*-
"""应用入口"""

import sys
from PySide6.QtWidgets import QApplication
from labeleasy.app import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()