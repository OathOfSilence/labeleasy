# -*- coding: utf-8 -*-
"""工具函数"""

import os
from typing import List, Tuple, Optional

from .models import Annotation, Keypoint
from .constants import SUPPORTED_IMAGE_FORMATS


def get_image_files(directory: str) -> List[str]:
    if not directory or not os.path.isdir(directory):
        return []
    
    files = []
    for f in sorted(os.listdir(directory)):
        ext = os.path.splitext(f)[1].lower()
        if ext in SUPPORTED_IMAGE_FORMATS:
            files.append(os.path.join(directory, f))
    return files


def get_label_path(image_path: str, label_dir: str) -> str:
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    return os.path.join(label_dir, base_name + '.txt')


def parse_yolo_line(line: str, num_keypoints: int, line_num: int) -> Tuple[Optional[Annotation], List[str]]:
    warnings_list = []
    parts = line.strip().split()
    
    if len(parts) < 5:
        warnings_list.append(f"行 {line_num}: 数据不足")
        return None, warnings_list
    
    try:
        class_id = int(float(parts[0]))
        if class_id != float(parts[0]):
            warnings_list.append(f"行 {line_num}: class_id不是整数，已修正")
    except ValueError:
        warnings_list.append(f"行 {line_num}: class_id格式错误")
        class_id = 0
    
    x_center = float(parts[1])
    y_center = float(parts[2])
    width = float(parts[3])
    height = float(parts[4])
    
    if not (0 <= x_center <= 1):
        x_center = max(0, min(1, x_center))
        warnings_list.append(f"行 {line_num}: x_center超出范围，已截断")
    if not (0 <= y_center <= 1):
        y_center = max(0, min(1, y_center))
        warnings_list.append(f"行 {line_num}: y_center超出范围，已截断")
    if not (0 <= width <= 1):
        width = max(0, min(1, width))
        warnings_list.append(f"行 {line_num}: width超出范围，已截断")
    if not (0 <= height <= 1):
        height = max(0, min(1, height))
        warnings_list.append(f"行 {line_num}: height超出范围，已截断")
    
    keypoints = []
    kp_data = parts[5:] if len(parts) > 5 else []
    
    for i in range(0, len(kp_data), 3):
        if i + 2 < len(kp_data):
            kp_x = float(kp_data[i])
            kp_y = float(kp_data[i + 1])
            kp_vis = int(float(kp_data[i + 2]))
            
            if not (0 <= kp_x <= 1):
                kp_x = max(0, min(1, kp_x))
                warnings_list.append(f"行 {line_num}: 关键点x超出范围，已截断")
            if not (0 <= kp_y <= 1):
                kp_y = max(0, min(1, kp_y))
                warnings_list.append(f"行 {line_num}: 关键点y超出范围，已截断")
            if kp_vis not in [0, 1, 2]:
                kp_vis = 2
                warnings_list.append(f"行 {line_num}: 关键点vis值无效，已设为2")
            
            x1 = x_center - width / 2
            x2 = x_center + width / 2
            y1 = y_center - height / 2
            y2 = y_center + height / 2
            
            if not (x1 <= kp_x <= x2 and y1 <= kp_y <= y2):
                kp_x = max(x1, min(x2, kp_x))
                kp_y = max(y1, min(y2, kp_y))
                warnings_list.append(f"行 {line_num}: 关键点不在框内，已截断")
            
            keypoints.append(Keypoint(x=kp_x, y=kp_y, vis=kp_vis))
    
    while len(keypoints) < num_keypoints:
        keypoints.append(Keypoint(x=0.5, y=0.5, vis=0))
    
    return Annotation(
        class_id=class_id,
        x_center=x_center,
        y_center=y_center,
        width=width,
        height=height,
        keypoints=keypoints
    ), warnings_list


def load_annotations(label_path: str, num_keypoints: int) -> Tuple[List[Annotation], List[str]]:
    annotations = []
    warnings_list = []
    
    if not os.path.exists(label_path):
        return annotations, warnings_list
    
    try:
        with open(label_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    ann, warns = parse_yolo_line(line, num_keypoints, line_num)
                    if ann:
                        annotations.append(ann)
                    warnings_list.extend(warns)
                except Exception as e:
                    warnings_list.append(f"行 {line_num}: 解析错误 - {e}")
    except Exception as e:
        warnings_list.append(f"读取文件错误: {e}")
    
    return annotations, warnings_list


def save_annotations(label_path: str, annotations: List[Annotation]):
    os.makedirs(os.path.dirname(label_path), exist_ok=True)
    
    lines = []
    for ann in annotations:
        lines.append(ann.to_yolo_line())
    
    with open(label_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
        if lines:
            f.write('\n')