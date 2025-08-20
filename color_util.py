# color_util.py

import numpy as np
import cv2
from config import *
from window_util import log

def is_red_dominant(roi, threshold=0.6):
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    lower_red1 = np.array([0, 100, 100])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([160, 100, 100])
    upper_red2 = np.array([180, 255, 255])
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask = cv2.bitwise_or(mask1, mask2)
    red_pixel_count = cv2.countNonZero(mask)
    total_pixels = roi.shape[0] * roi.shape[1]
    red_ratio = red_pixel_count / total_pixels
    return red_ratio >= threshold

def is_white_dominant(roi, threshold=0.2):
    # 转为灰度图或直接在 BGR 上操作
    # 假设 BGR 图像中，白色像素满足三个通道都接近 255
    white_mask = np.all(roi > 200, axis=2)  # 所有通道都大于 240 被认为是白色
    white_ratio = np.sum(white_mask) / (roi.shape[0] * roi.shape[1])
    log(f"白色像素比例: {white_ratio:.2f} (阈值: {threshold})")
    return white_ratio > threshold

def find_max_red_region(img, search_rect, box_size=7, threshold=RED_THRESHOLD):
    """
    在指定大区域内滑动窗口，找到红色像素比例最高的小区域
    返回 (x1, y1, x2, y2), max_ratio
    """
    x1, y1, x2, y2 = search_rect
    h, w = img.shape[:2]
    max_ratio = 0
    max_rect = (x1, y1, x1+box_size, y1+box_size)
    for cy in range(y1, y2-box_size+1):
        for cx in range(x1, x2-box_size+1):
            if cx < 0 or cy < 0 or cx+box_size > w or cy+box_size > h:
                continue
            roi = img[cy:cy+box_size, cx:cx+box_size]
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            lower_red1 = np.array([0, 100, 100])
            upper_red1 = np.array([10, 255, 255])
            lower_red2 = np.array([160, 100, 100])
            upper_red2 = np.array([180, 255, 255])
            mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
            mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
            mask = cv2.bitwise_or(mask1, mask2)
            ratio = cv2.countNonZero(mask) / (box_size * box_size)
            if ratio > max_ratio:
                max_ratio = ratio
                max_rect = (cx, cy, cx+box_size, cy+box_size)
    return max_rect, max_ratio

def is_color_match(img, x1, y1, x2, y2, target_color, tolerance=15):
    roi = img[y1:y2, x1:x2]
    avg_color = cv2.mean(roi)[:3]
    avg_color = np.round(avg_color).astype(int)
    target_bgr = target_color[::-1]
    diff = np.abs(avg_color - target_bgr)
    return np.all(diff <= tolerance)

def is_blue_target(img, roi, color_list, tolerance=8):
    x1, y1, x2, y2 = roi
    roi_img = img[y1:y2, x1:x2]
    avg_color = cv2.mean(roi_img)[:3]
    avg_color = np.round(avg_color).astype(int)
    for color in color_list:
        target_bgr = color[::-1]
        diff = np.abs(avg_color - target_bgr)
        if np.all(diff <= tolerance):
            print(f"检测到目标蓝绿色：{color}，实际={avg_color[::-1]}")
            return True
    return False

def region_has_color(img, center, color_list, offset=2, tolerance=20, ratio=0.5):
    x, y = center
    h, w = img.shape[:2]
    match_cnt = 0
    total_cnt = 0
    for dx in range(-offset, offset + 1):
        for dy in range(-offset, offset + 1):
            cx, cy = x + dx, y + dy
            if 0 <= cx < w and 0 <= cy < h:
                total_cnt += 1
                pixel = img[cy, cx]  # BGR
                for color in color_list:
                    bgr_color = color[::-1]
                    if np.all(np.abs(pixel - bgr_color) <= tolerance):
                        match_cnt += 1
                        break
    if total_cnt == 0:
        return False
    proportion = match_cnt / total_cnt
    return proportion >= ratio

def has_red_or_orange(roi, ratio_threshold=AD_RED_ORANGE_RATIO):
    """
    检测 ROI 内是否存在足够比例的红/橙色像素。
    - 复用上钩判定的 HSV 思路，扩大色相至包含橙色段（H≈10~25）。
    - 返回：红橙色像素占比 >= ratio_threshold。
    """
    if roi is None or roi.size == 0:
        return False
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

    # 红色两段
    lower_red1 = np.array([0, 100, 100])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([160, 100, 100])
    upper_red2 = np.array([180, 255, 255])

    # 橙色一段（衔接红色上沿）
    lower_orange = np.array([10, 100, 100])
    upper_orange = np.array([25, 255, 255])

    mask_r1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask_r2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask_or = cv2.inRange(hsv, lower_orange, upper_orange)

    mask = cv2.bitwise_or(cv2.bitwise_or(mask_r1, mask_r2), mask_or)
    ratio = cv2.countNonZero(mask) / (roi.shape[0] * roi.shape[1])
    return ratio >= ratio_threshold

def region_rect_major_color(img, rect, color_list, tolerance=20, ratio=0.5):
    x1, y1, x2, y2 = rect
    roi = img[y1:y2, x1:x2]
    # cv2.imshow('window title',roi)
    h, w = roi.shape[:2]
    match_cnt = 0
    total_cnt = h * w
    for yy in range(h):
        for xx in range(w):
            pixel = roi[yy, xx]  # BGR
            for color in color_list:
                bgr_color = color[::-1]
                if np.all(np.abs(pixel - bgr_color) <= tolerance):
                    match_cnt += 1
                    break
    if total_cnt == 0:
        return False
    proportion = match_cnt / total_cnt
    return proportion >= ratio

def has_broad_red_in_region(img, center, size, ratio_threshold=REEL_RED_RATIO_THRESHOLD):
    """
    检测指定区域内是否有宽泛的红色出现
    
    参数:
        img: 截图图像（BGR格式）
        center: 检测区域中心坐标 (x, y)
        size: 检测区域边长（正方形）
        ratio_threshold: 红色像素占比阈值
    
    返回:
        bool: 是否检测到足够比例的红色
    """
    if img is None or img.size == 0:
        return False
    
    h, w = img.shape[:2]
    cx, cy = center
    half_size = size // 2
    
    # 计算检测区域边界，确保不超出图像范围
    x1 = max(0, int(cx - half_size))
    y1 = max(0, int(cy - half_size))
    x2 = min(w, int(cx + half_size))
    y2 = min(h, int(cy + half_size))
    
    # 提取ROI
    roi = img[y1:y2, x1:x2]
    if roi.size == 0:
        return False
    
    # 转换为HSV色彩空间进行红色检测
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    
    # 定义红色的HSV范围（极宽泛检测，包含各种红色变化）
    # 红色范围1：0-15度（扩大覆盖偏橙红色）
    lower_red1 = np.array([0, 30, 30])      # 进一步降低饱和度和明度阈值
    upper_red1 = np.array([15, 255, 255])   # 扩大色相范围
    
    # 红色范围2：150-180度（扩大覆盖偏紫红色）
    lower_red2 = np.array([150, 30, 30])    # 扩大色相范围，降低阈值
    upper_red2 = np.array([180, 255, 255])
    
    # 橙红色范围（15-35度，扩大范围）
    lower_orange = np.array([15, 30, 30])
    upper_orange = np.array([35, 255, 255])
    
    # 粉红色范围（可能的红色变化）
    lower_pink = np.array([140, 30, 30])
    upper_pink = np.array([170, 255, 255])
    
    # 创建掩码
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask3 = cv2.inRange(hsv, lower_orange, upper_orange)
    mask4 = cv2.inRange(hsv, lower_pink, upper_pink)
    
    # 合并所有掩码
    temp_mask = cv2.bitwise_or(cv2.bitwise_or(mask1, mask2), mask3)
    combined_mask = cv2.bitwise_or(temp_mask, mask4)
    
    # 计算红色像素比例
    red_pixels = cv2.countNonZero(combined_mask)
    total_pixels = roi.shape[0] * roi.shape[1]
    red_ratio = red_pixels / total_pixels
    
    # 详细的检测日志
    result = red_ratio >= ratio_threshold
    log(f"红色检测详情：区域{roi.shape} 红色像素{red_pixels}/{total_pixels} 比例{red_ratio:.3f} 阈值{ratio_threshold:.3f} -> {'检测到' if result else '未检测到'}")
    log(f"扩展检测范围：红色(0-15°,150-180°) 橙色(15-35°) 粉红(140-170°) 饱和度≥30 明度≥30")
    
    return result
