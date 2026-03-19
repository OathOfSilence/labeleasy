# -*- coding: utf-8 -*-
"""数据模型"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import yaml


@dataclass
class Keypoint:
    x: float
    y: float
    vis: int
    
    def to_list(self) -> List[float]:
        return [self.x, self.y, self.vis]
    
    @classmethod
    def from_list(cls, data: List[float]) -> 'Keypoint':
        return cls(x=data[0], y=data[1], vis=int(data[2]))


@dataclass
class Annotation:
    class_id: int
    x_center: float
    y_center: float
    width: float
    height: float
    keypoints: List[Keypoint] = field(default_factory=list)
    selected: bool = False
    
    def to_yolo_line(self) -> str:
        parts = [self.class_id, self.x_center, self.y_center, self.width, self.height]
        for kp in self.keypoints:
            parts.extend(kp.to_list())
        return ' '.join(map(str, parts))
    
    @classmethod
    def from_yolo_line(cls, line: str, num_keypoints: int = 0) -> 'Annotation':
        parts = line.strip().split()
        class_id = int(float(parts[0]))
        x_center = float(parts[1])
        y_center = float(parts[2])
        width = float(parts[3])
        height = float(parts[4])
        
        keypoints = []
        kp_data = parts[5:] if len(parts) > 5 else []
        for i in range(0, len(kp_data), 3):
            if i + 2 < len(kp_data):
                keypoints.append(Keypoint(
                    x=float(kp_data[i]),
                    y=float(kp_data[i + 1]),
                    vis=int(float(kp_data[i + 2]))
                ))
        
        while len(keypoints) < num_keypoints:
            keypoints.append(Keypoint(x=0.5, y=0.5, vis=0))
        
        return cls(class_id=class_id, x_center=x_center, y_center=y_center,
                   width=width, height=height, keypoints=keypoints)
    
    def contains_point(self, x: float, y: float) -> bool:
        x1 = self.x_center - self.width / 2
        y1 = self.y_center - self.height / 2
        x2 = self.x_center + self.width / 2
        y2 = self.y_center + self.height / 2
        return x1 <= x <= x2 and y1 <= y <= y2
    
    def get_bbox_coords(self) -> Tuple[float, float, float, float]:
        return (
            self.x_center - self.width / 2,
            self.y_center - self.height / 2,
            self.x_center + self.width / 2,
            self.y_center + self.height / 2
        )


@dataclass
class Template:
    names: List[str]
    keypoints: List[str]
    skeleton: List[List[List[int]]]
    
    @classmethod
    def from_yaml(cls, filepath: str) -> 'Template':
        with open(filepath, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return cls(
            names=data.get('names', []),
            keypoints=data.get('keypoints', []),
            skeleton=data.get('skeleton', [])
        )
    
    def to_yaml(self, filepath: str):
        data = {
            'names': self.names,
            'keypoints': self.keypoints,
            'skeleton': self.skeleton
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
    
    def validate(self) -> List[str]:
        errors = []
        if not self.names:
            errors.append("names 列表不能为空")
        # 允许 keypoints 为空（纯目标检测模式）
        if self.keypoints:
            for group in self.skeleton:
                for conn in group:
                    if len(conn) != 2:
                        errors.append(f"骨架连接格式错误：{conn}")
                    elif conn[0] >= len(self.keypoints) or conn[1] >= len(self.keypoints):
                        errors.append(f"骨架连接索引超出范围：{conn}")
        return errors
    
    def has_keypoints(self) -> bool:
        """判断模板是否包含关键点"""
        return len(self.keypoints) > 0
