# -*- coding: utf-8 -*-
"""对话框组件"""

from typing import Dict, List, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QLineEdit, QPushButton, QComboBox, QFrame, QMessageBox,
    QCheckBox, QDialogButtonBox
)

from .models import Template


class ConfigDialog(QDialog):
    def __init__(self, parent=None, recent_projects: List[Dict] = None):
        super().__init__(parent)
        self.setWindowTitle("Labeleasy - 项目配置")
        self.setMinimumWidth(600)
        self.recent_projects = recent_projects if recent_projects else []
        self.template_data: Optional[Template] = None
        self._initialized_from_recent = False
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        if self.recent_projects:
            recent_group = QFrame()
            recent_layout = QVBoxLayout(recent_group)
            recent_layout.setContentsMargins(0, 0, 0, 0)
            
            recent_label = QLabel("最近项目 (双击打开):")
            recent_layout.addWidget(recent_label)
            
            self.recent_combo = QComboBox()
            for proj in self.recent_projects:
                display_text = f"{proj.get('template', '').split('/')[-1]} - {proj.get('image_dir', '').split('/')[-1]}"
                self.recent_combo.addItem(display_text, proj)
            self.recent_combo.currentIndexChanged.connect(self.on_recent_selected)
            recent_layout.addWidget(self.recent_combo)
            
            open_recent_btn = QPushButton("打开选中项目")
            open_recent_btn.clicked.connect(self.open_recent_project)
            recent_layout.addWidget(open_recent_btn)
            
            layout.addWidget(recent_group)
        
        form_layout = QFormLayout()
        
        self.template_edit = QLineEdit()
        self.template_btn = QPushButton("浏览...")
        self.template_btn.clicked.connect(self.browse_template)
        template_layout = QHBoxLayout()
        template_layout.addWidget(self.template_edit)
        template_layout.addWidget(self.template_btn)
        form_layout.addRow("标注模板:", template_layout)
        
        self.image_dir_edit = QLineEdit()
        self.image_dir_btn = QPushButton("浏览...")
        self.image_dir_btn.clicked.connect(self.browse_image_dir)
        image_layout = QHBoxLayout()
        image_layout.addWidget(self.image_dir_edit)
        image_layout.addWidget(self.image_dir_btn)
        form_layout.addRow("图像目录:", image_layout)
        
        self.label_dir_edit = QLineEdit()
        self.label_dir_btn = QPushButton("浏览...")
        self.label_dir_btn.clicked.connect(self.browse_label_dir)
        label_layout = QHBoxLayout()
        label_layout.addWidget(self.label_dir_edit)
        label_layout.addWidget(self.label_dir_btn)
        form_layout.addRow("标签目录:", label_layout)
        
        layout.addLayout(form_layout)
        
        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("确定")
        self.ok_btn.clicked.connect(self.accept_config)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
    
    def on_recent_selected(self, index):
        if index >= 0 and index < len(self.recent_projects):
            proj = self.recent_projects[index]
            self.template_edit.setText(proj.get('template', ''))
            self.image_dir_edit.setText(proj.get('image_dir', ''))
            self.label_dir_edit.setText(proj.get('label_dir', ''))
            self._initialized_from_recent = True
    
    def open_recent_project(self):
        index = self.recent_combo.currentIndex()
        if index >= 0 and index < len(self.recent_projects):
            proj = self.recent_projects[index]
            self.template_edit.setText(proj.get('template', ''))
            self.image_dir_edit.setText(proj.get('image_dir', ''))
            self.label_dir_edit.setText(proj.get('label_dir', ''))
            self._initialized_from_recent = True
            self.accept_config()
    
    def browse_template(self):
        from PyQt6.QtWidgets import QFileDialog
        filepath, _ = QFileDialog.getOpenFileName(
            self, "选择标注模板", "", "YAML文件 (*.yaml *.yml)"
        )
        if filepath:
            self.template_edit.setText(filepath)
            self._initialized_from_recent = False
    
    def browse_image_dir(self):
        from PyQt6.QtWidgets import QFileDialog
        directory = QFileDialog.getExistingDirectory(self, "选择图像目录")
        if directory:
            self.image_dir_edit.setText(directory)
            self._initialized_from_recent = False
    
    def browse_label_dir(self):
        from PyQt6.QtWidgets import QFileDialog
        directory = QFileDialog.getExistingDirectory(self, "选择标签目录")
        if directory:
            self.label_dir_edit.setText(directory)
            self._initialized_from_recent = False
    
    def accept_config(self):
        import os
        template_path = self.template_edit.text().strip()
        image_dir = self.image_dir_edit.text().strip()
        label_dir = self.label_dir_edit.text().strip()
        
        if not template_path:
            QMessageBox.warning(self, "警告", "请选择标注模板文件")
            return
        if not image_dir:
            QMessageBox.warning(self, "警告", "请选择图像目录")
            return
        if not label_dir:
            QMessageBox.warning(self, "警告", "请选择标签目录")
            return
        
        if not os.path.exists(template_path):
            QMessageBox.warning(self, "警告", f"模板文件不存在: {template_path}")
            return
        if not os.path.isdir(image_dir):
            QMessageBox.warning(self, "警告", f"图像目录不存在: {image_dir}")
            return
        if not os.path.isdir(label_dir):
            QMessageBox.warning(self, "警告", f"标签目录不存在: {label_dir}")
            return
        
        try:
            self.template_data = Template.from_yaml(template_path)
            errors = self.template_data.validate()
            if errors:
                QMessageBox.warning(self, "模板错误", "\n".join(errors))
                return
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载模板失败: {e}")
            return
        
        self.accept()
    
    def get_config(self) -> Dict:
        return {
            'template': self.template_edit.text().strip(),
            'image_dir': self.image_dir_edit.text().strip(),
            'label_dir': self.label_dir_edit.text().strip(),
            'template_data': self.template_data
        }


class SaveConfirmDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("保存确认")
        self.setMinimumWidth(300)
        self.result_code = 0
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        label = QLabel("当前图像已修改，是否保存？\n(A=取消, S=保存, D=不保存)")
        layout.addWidget(label)
        
        btn_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("取消 (A)")
        self.cancel_btn.clicked.connect(self.on_cancel)
        
        self.save_btn = QPushButton("保存 (S)")
        self.save_btn.clicked.connect(self.on_save)
        
        self.discard_btn = QPushButton("不保存 (D)")
        self.discard_btn.clicked.connect(self.on_discard)
        
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.discard_btn)
        
        layout.addLayout(btn_layout)
    
    def keyPressEvent(self, event):
        from PyQt6.QtCore import Qt
        if event.key() == Qt.Key_A:
            self.on_cancel()
        elif event.key() == Qt.Key_S:
            self.on_save()
        elif event.key() == Qt.Key_D:
            self.on_discard()
        else:
            super().keyPressEvent(event)
    
    def on_cancel(self):
        self.result_code = 0
        self.reject()
    
    def on_save(self):
        self.result_code = 1
        self.accept()
    
    def on_discard(self):
        self.result_code = 2
        self.accept()


class TemplateEditDialog(QDialog):
    def __init__(self, template: Template, parent=None):
        super().__init__(parent)
        self.template = template
        self.setWindowTitle("编辑模板")
        self.setMinimumSize(400, 300)
        self.setup_ui()
    
    def setup_ui(self):
        from PyQt6.QtWidgets import QTextEdit
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("类别名称 (每行一个):"))
        self.names_edit = QTextEdit()
        self.names_edit.setPlainText('\n'.join(self.template.names))
        self.names_edit.setMaximumHeight(80)
        layout.addWidget(self.names_edit)
        
        layout.addWidget(QLabel("关键点名称 (每行一个):"))
        self.keypoints_edit = QTextEdit()
        self.keypoints_edit.setPlainText('\n'.join(self.template.keypoints))
        layout.addWidget(self.keypoints_edit)
        
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept_changes)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
    
    def accept_changes(self):
        self.template.names = [n.strip() for n in self.names_edit.toPlainText().split('\n') if n.strip()]
        self.template.keypoints = [k.strip() for k in self.keypoints_edit.toPlainText().split('\n') if k.strip()]
        errors = self.template.validate()
        if errors:
            QMessageBox.warning(self, "模板错误", "\n".join(errors))
            return
        self.accept()