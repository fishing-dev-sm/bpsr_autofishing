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

def save_debug_detection_image(img, center, size, detected=False):
    """
    保存带有检测框的调试截图
    
    参数:
        img: 原始截图
        center: 检测中心坐标
        size: 检测区域大小
        detected: 是否检测到目标
    """
    if not DEBUG_ENABLED or not DEBUG_SAVE_DETECTION_SCREENSHOT:
        return
    
    debug_img = img.copy()
    cx, cy = center
    half_size = size // 2
    
    # 计算检测框坐标
    x1 = max(0, int(cx - half_size))
    y1 = max(0, int(cy - half_size))
    x2 = min(img.shape[1], int(cx + half_size))
    y2 = min(img.shape[0], int(cy + half_size))
    
    # 绘制检测框
    color = (0, 255, 0) if detected else (0, 0, 255)  # 绿色=检测到，红色=未检测到
    thickness = 2
    cv2.rectangle(debug_img, (x1, y1), (x2, y2), color, thickness)
    
    # 绘制中心点
    cv2.circle(debug_img, (int(cx), int(cy)), 3, color, -1)
    
    # 添加文字标注
    text = f"Center:({cx},{cy}) Size:{size}x{size} {'DETECTED' if detected else 'NOT_DETECTED'}"
    cv2.putText(debug_img, text, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    
    # 生成带时间戳的文件名
    import time
    timestamp = int(time.time())
    filename = f"{DEBUG_SCREENSHOT_PREFIX}_{timestamp}_{'detected' if detected else 'not_detected'}.png"
    
    # 保存图片
    cv2.imwrite(filename, debug_img)
    log(f"Debug截图已保存到: {filename} ({'检测到' if detected else '未检测到'})")

def has_broad_red_or_white_in_region(img, center, size, ratio_threshold=REEL_RED_RATIO_THRESHOLD):
    """
    检测指定区域内是否有宽泛的红色或白色出现
    
    参数:
        img: 截图图像（BGR格式）
        center: 检测区域中心坐标 (x, y)
        size: 检测区域边长（正方形）
        ratio_threshold: 红色/白色像素占比阈值
    
    返回:
        bool: 是否检测到足够比例的红色或白色
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
    
    # 定义红色的HSV范围（适度宽泛，确保能检测到红色）
    # 红色范围1：0-10度（包含一些橙红色，提高检测率）
    lower_red1 = np.array([0, 50, 50])      # 降低饱和度和明度阈值，提高检测率
    upper_red1 = np.array([10, 255, 255])   # 稍微扩大色相范围
    
    # 红色范围2：160-180度（深红色）
    lower_red2 = np.array([160, 50, 50])    # 降低饱和度阈值，扩大检测范围
    upper_red2 = np.array([180, 255, 255])
    
    # 适度包含红橙色以提高检测率
    
    # 创建掩码
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    
    # 合并红色掩码（只包含纯红色）
    red_mask = cv2.bitwise_or(mask1, mask2)
    
    # 白色检测 - 基于实际白色值#fdf6f6进行精确检测
    target_white_rgb = np.array(REEL_WHITE_COLOR_TARGET)  # RGB格式的目标白色
    target_white_bgr = target_white_rgb[::-1]  # 转换为BGR格式
    
    # 方法1：基于目标白色的RGB距离检测（更精确）
    # 计算每个像素与目标白色的欧几里得距离
    diff = np.abs(roi.astype(np.float32) - target_white_bgr.astype(np.float32))
    color_distance = np.sqrt(np.sum(diff**2, axis=2))
    white_bgr_precise = color_distance < REEL_WHITE_COLOR_TOLERANCE
    
    # 方法2：HSV色彩空间，低饱和度高明度（更宽松的白色检测）
    white_hsv_mask = cv2.inRange(hsv, np.array([0, 0, 200]), np.array([180, 30, 255]))
    
    # 合并两种白色检测方法（提高精确度）
    white_condition = np.logical_or(white_bgr_precise, white_hsv_mask > 0)
    white_mask = white_condition.astype(np.uint8) * 255
    
    # 合并红色和白色掩码
    combined_mask = cv2.bitwise_or(red_mask, white_mask)
    
    # 计算红色和白色像素比例
    red_pixels = cv2.countNonZero(red_mask)
    white_pixels = cv2.countNonZero(white_mask)
    total_red_white_pixels = cv2.countNonZero(combined_mask)
    total_pixels = roi.shape[0] * roi.shape[1]
    
    red_ratio = red_pixels / total_pixels
    white_ratio = white_pixels / total_pixels
    combined_ratio = total_red_white_pixels / total_pixels
    
    # 详细的检测日志
    result = combined_ratio >= ratio_threshold
    
    # 修正红色和白色的检测逻辑：红色和白色是交替出现的，分别独立检测
    # 降低单独检测阈值，因为红色通常像素较少
    red_threshold = ratio_threshold * 0.3   # 红色阈值0.3%，因为红色通常较少
    white_threshold = ratio_threshold * 0.3 # 白色阈值0.3%
    
    # 独立检测红色和白色，任一检测到都算有效
    has_red = red_ratio >= red_threshold
    has_white = white_ratio >= white_threshold
    
    # 总体检测结果：红色或白色任一检测到即为真
    result = has_red or has_white
    
    detection_msg = []
    if has_red:
        detection_msg.append("红色")
    if has_white:
        detection_msg.append("白色")
    
    log(f"红白检测详情：区域{roi.shape} 红色{red_pixels}({red_ratio:.3f},阈值{red_threshold:.3f}) 白色{white_pixels}({white_ratio:.3f},阈值{white_threshold:.3f}) -> 检测到{'/'.join(detection_msg) if detection_msg else '无'}")
    
    # 返回详细检测结果
    return result, has_red, has_white
