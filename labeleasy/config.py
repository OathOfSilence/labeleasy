# -*- coding: utf-8 -*-
"""配置管理"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from PyQt5.QtCore import QSettings


def get_app_dir() -> Path:
    """获取应用目录（可执行文件所在目录）"""
    if getattr(sys, 'frozen', False):
        return Path(os.path.dirname(sys.executable))
    else:
        return Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ConfigManager:
    def __init__(self):
        self.config_file = get_app_dir() / 'config.json'
        self.settings = QSettings('labeleasy', 'labeleasy')
        self._config: Dict[str, Any] = {}
        self.load()
    
    def load(self) -> Dict[str, Any]:
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
            except Exception:
                self._config = {}
        return self._config
    
    def save(self):
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self._config, f, ensure_ascii=False, indent=2)
    
    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any):
        self._config[key] = value
    
    def get_recent_projects(self) -> List[Dict]:
        return self._config.get('recent_projects', [])
    
    def add_recent_project(self, project: Dict, max_count: int = 20):
        projects = self.get_recent_projects()
        
        for i, p in enumerate(projects):
            if (p.get('template') == project.get('template') and
                p.get('image_dir') == project.get('image_dir') and
                p.get('label_dir') == project.get('label_dir')):
                projects.pop(i)
                break
        
        projects.insert(0, project)
        projects = projects[:max_count]
        self._config['recent_projects'] = projects
    
    def get_auto_save(self) -> bool:
        return self._config.get('auto_save', True)
    
    def set_auto_save(self, value: bool):
        self._config['auto_save'] = value
    
    def get_last_image(self) -> Optional[str]:
        return self._config.get('last_image')
    
    def set_last_image(self, path: str):
        self._config['last_image'] = path