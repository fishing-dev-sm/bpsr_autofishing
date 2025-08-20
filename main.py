# main.py
import ctypes

import game_logic
ctypes.windll.shcore.SetProcessDpiAwareness(2) 
import sys
sys.stdout.reconfigure(encoding='utf-8')
import time
import keyboard
from config import *
from window_util import *
from color_util import *
from utils import save_screenshot

def monitor_window(hwnd):
    isRunning = [True]
    last_key = [None]  # 记录上一次长按的"a"或"d"
    # 会话统计
    session_start_ts = time.time()
    attempts = 0
    successes = 0
    failures = 0
    window = get_window_by_hwnd(hwnd)
    if not window:
        log(f"未找到窗口句柄 {hwnd} 对应的窗口")
        return

    def on_esc_press(e):
        if e.event_type == keyboard.KEY_DOWN and e.name.lower() in ('esc', '~', 'q', 'ctrl'):
            log(f"检测到 {e.name} 键按下，程序即将退出...")
            isRunning[0] = False

    keyboard.on_press(on_esc_press)
    log("程序已启动，按 Esc 键可随时退出")
    window.activate()
    log("已切换到目标窗口")
    time.sleep(1)

    try:
        while isRunning[0]:
            full_img = capture_window(hwnd)
            height, width = full_img.shape[:2]
            game_logic.check_and_replace_rod(full_img,width,height,hwnd,window)
                
            click_mouse_window(hwnd, *get_scale_point(CLICK_POS, full_img.shape[1], full_img.shape[0]))
            attempts += 1
            log(f"甩钩（第{attempts}次），{START_DELAY}秒后检测红点")

            # 新增：等待1秒检测特殊颜色区域
            time.sleep(2.5)
            full_img = capture_window(hwnd)
            # cv2.imshow('window title',full_img)

            # 补足剩余延迟（如后面还需等到2秒），兼容原蓝色检测逻辑
            time.sleep(1)
            delay_start = time.time()
            blue_detected = False
            while time.time() - delay_start < (START_DELAY - 2):
                full_img = capture_window(hwnd)
                if full_img is not None:
                    if is_blue_target(full_img, get_scale_area(BLUE_ROI,width,height), BLUE_COLORS, tolerance=BLUE_TOLERANCE):
                        failures += 1
                        log(f"鱼跑了（失败+1，目前 成功/失败/尝试 = {successes}/{failures}/{attempts}）")
                        blue_detected = True
                        break
                time.sleep(0.05)
            if blue_detected:
                continue

            # ====== 步骤2：自动定位红点密集区域 ======
            full_img = capture_window(hwnd)
            found_red = False
            count = 0
            fish_region = []
            while not found_red and count<3:
                offset = count * 100  # 每次偏移100像素
                center = (RED_SEARCH_REGION_CENTER[0], RED_SEARCH_REGION_CENTER[1] + offset)
                red_rect, red_ratio = find_max_red_region(
                    full_img, get_search_region(get_scale_point(center,width,height), RED_SEARCH_REGION_OFFSET), RED_DETECT_BOX_SIZE, RED_THRESHOLD)
                # utils.save_screenshot(full_img, f'full_img')
                log(f"检测到红点区域：{red_rect}, 密集度={red_ratio:.2f}")
                fish_region = red_rect
                count+=1
                if red_ratio >= RED_THRESHOLD:
                    break
            if red_ratio < RED_THRESHOLD:
                log("找不到红点")
                # return

            red_start_time = None
            is_pressed = False
            is_rapid_clicking = False  # 新增：标记是否在连点模式
            rapid_click_count = 0      # 连点计数器，用于控制日志频率
            cycle_active = True
            blue_check_enable = True
            # 新增：A/D 触发状态记录（用于边沿触发日志与锁定切换）
            ad_prev_hot = {"a": False, "d": False}

            while cycle_active and isRunning[0]:
                full_img = capture_window(hwnd)
                if full_img is None:
                    time.sleep(0.1)
                    continue

                if blue_check_enable and is_blue_target(full_img, get_scale_area(BLUE_ROI,width,height), BLUE_COLORS, tolerance=BLUE_TOLERANCE):
                    failures += 1
                    log(f"鱼跑了（失败+1，目前 成功/失败/尝试 = {successes}/{failures}/{attempts}）")
                    break

                # 只监控本轮刚刚自动检测到的红点区域
                x1, y1, x2, y2 = red_rect
                
                if not is_pressed: 
                    roi = full_img[y1:y2, x1:x2]
                    red = is_red_dominant(roi, threshold=RED_THRESHOLD)
                    white = is_white_dominant(roi, threshold=0.2)

                if not red and white:
                    if not is_pressed and not is_rapid_clicking:
                        # 检测收鱼线区域是否有红色出现
                        reel_center = get_scale_point(REEL_RED_CHECK_CENTER, width, height)
                        reel_size = get_int_scale_val(REEL_RED_CHECK_SIZE, width, height)
                        
                        has_red = has_broad_red_in_region(full_img, reel_center, reel_size)
                        log(f"收鱼线区域红色检测：{reel_center} ({reel_size}x{reel_size}) -> {'有红色' if has_red else '无红色'}")
                        
                        if has_red:
                            # 如果检测到红色，使用连点模式
                            log("【启动连点模式】检测到收鱼线区域红色，开始鼠标连点收线")
                            is_rapid_clicking = True
                            rapid_click_count = 0
                        else:
                            # 没有红色，使用原来的长按模式
                            log("【启动长按模式】未检测到红色，使用传统长按收线")
                            press_mouse_window(hwnd, *CLICK_POS)
                            is_pressed = True
                    elif is_rapid_clicking:
                        # 持续连点模式
                        rapid_click_count += 1
                        if rapid_click_count % 20 == 1:  # 每20次连点输出一次日志
                            log(f"【连点进行中】第{rapid_click_count}次连点...")
                        rapid_click_mouse_window(hwnd, *CLICK_POS)
                else:
                    red_start_time = None
                    # 重置连点状态
                    if is_rapid_clicking:
                        log(f"【退出连点模式】鱼漂状态变化，共连点{rapid_click_count}次")
                        is_rapid_clicking = False
                        rapid_click_count = 0

                # ------- A/D互斥长按逻辑（新版：左右红橙色检测，锁定-切换） -------
                if is_pressed:
                    # 计算 A/D 检测方框（按分辨率缩放）
                    a_cx, a_cy = get_scale_point(AD_A_CENTER, width, height)
                    d_cx, d_cy = get_scale_point(AD_D_CENTER, width, height)
                    box = get_int_scale_val(AD_BOX_SIZE, width, height)
                    half = max(1, box // 2)

                    def clamp(v, lo, hi):
                        return max(lo, min(v, hi))

                    # A 区域 ROI
                    ax1 = clamp(a_cx - half, 0, width - 1)
                    ay1 = clamp(a_cy - half, 0, height - 1)
                    ax2 = clamp(a_cx + half, 0, width)
                    ay2 = clamp(a_cy + half, 0, height)
                    roi_a = full_img[ay1:ay2, ax1:ax2] if ay2 > ay1 and ax2 > ax1 else None

                    # D 区域 ROI
                    dx1 = clamp(d_cx - half, 0, width - 1)
                    dy1 = clamp(d_cy - half, 0, height - 1)
                    dx2 = clamp(d_cx + half, 0, width)
                    dy2 = clamp(d_cy + half, 0, height)
                    roi_d = full_img[dy1:dy2, dx1:dx2] if dy2 > dy1 and dx2 > dx1 else None

                    a_hot = has_red_or_orange(roi_a) if roi_a is not None else False
                    d_hot = has_red_or_orange(roi_d) if roi_d is not None else False

                    # 触发边沿日志（避免每帧刷屏）
                    if a_hot and not ad_prev_hot["a"]:
                        log("A判定触发（红橙色命中）")
                    if d_hot and not ad_prev_hot["d"]:
                        log("D判定触发（红橙色命中）")
                    ad_prev_hot["a"] = a_hot
                    ad_prev_hot["d"] = d_hot

                    # 锁定-切换逻辑
                    # 规则：
                    # - A 触发后，持续按 A，直到 D 触发才切换到 D；
                    # - D 触发后，持续按 D，直到 A 触发才切换到 A；
                    # - 两侧都触发时，保持当前方向；若无当前方向，则不按。
                    if last_key[0] == "a":
                        if d_hot:
                            keyboard.release("a"); log("释放A（D触发，切换到D）")
                            keyboard.press("d"); log("按下D")
                            last_key[0] = "d"
                        else:
                            # 继续保持 A 按下（不重复按）
                            pass
                    elif last_key[0] == "d":
                        if a_hot:
                            keyboard.release("d"); log("释放D（A触发，切换到A）")
                            keyboard.press("a"); log("按下A")
                            last_key[0] = "a"
                        else:
                            # 继续保持 D 按下
                            pass
                    else:
                        # 当前没有方向被按下
                        if a_hot and not d_hot:
                            keyboard.press("a"); log("按下A（首次）")
                            last_key[0] = "a"
                        elif d_hot and not a_hot:
                            keyboard.press("d"); log("按下D（首次）")
                            last_key[0] = "d"
                        elif a_hot and d_hot:
                            # 同时触发，未有历史方向则暂不按
                            pass
                    
                    cx1, cy1, cx2, cy2 = get_scale_area(COLOR_CHECK_AREA,width, height)
                    if is_color_match(full_img, cx1, cy1, cx2, cy2, TARGET_COLOR):
                        successes += 1
                        log(f"钓鱼完成（成功+1，目前 成功/失败/尝试 = {successes}/{failures}/{attempts}）")
                        release_mouse()
                        is_pressed = False
                        if is_rapid_clicking:
                            log(f"【钓鱼完成，退出连点模式】共连点{rapid_click_count}次")
                            is_rapid_clicking = False  # 重置连点状态
                            rapid_click_count = 0
                        blue_check_enable = False
                        # ===== 这里是新加的配置延迟 =====
                        time.sleep(AFTER_DETECT_CLICK_DELAY)
                        click_mouse_window(hwnd, *(get_scale_point(SECOND_CLICK_POS,width,height)))
                        log(f"{AFTER_SECOND_CLICK_DELAY}秒后继续钓鱼")
                        time.sleep(AFTER_SECOND_CLICK_DELAY)
                        cycle_active = False
                        if last_key[0] == "a":
                            keyboard.release("a")
                        if last_key[0] == "d":
                            keyboard.release("d")
                        last_key[0] = None
                else:
                    # 重置连点状态
                    if is_rapid_clicking:
                        log(f"【退出连点模式】未处于收鱼状态，共连点{rapid_click_count}次")
                        is_rapid_clicking = False
                        rapid_click_count = 0
                    if last_key[0] == "a":
                        keyboard.release("a")
                        last_key[0] = None
                    if last_key[0] == "d":
                        keyboard.release("d")
                        last_key[0] = None

                time.sleep(0.04)
    except Exception as e:
        log("发生异常：", e)
    finally:
        session_end_ts = time.time()
        session_start_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(session_start_ts))
        session_end_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(session_end_ts))
        duration = max(0.0, session_end_ts - session_start_ts)
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = int(duration % 60)
        success_rate = (successes / attempts * 100.0) if attempts > 0 else 0.0
        per_min = (successes / (duration / 60.0)) if duration > 0 else 0.0
        per_hour = (successes / (duration / 3600.0)) if duration > 0 else 0.0

        log("================ 会话统计 ================")
        log(f"时间区间：{session_start_str}  →  {session_end_str}  （{hours:02d}:{minutes:02d}:{seconds:02d}）")
        log(f"结果：成功 {successes}，失败 {failures}，尝试 {attempts}，成功率 {success_rate:.2f}%")
        log(f"单位时间效率：{per_min:.2f} 成功/分钟，{per_hour:.2f} 成功/小时")
        log("===========================================")
        release_mouse()
        if last_key[0] == "a":
            keyboard.release("a")
        if last_key[0] == "d":
            keyboard.release("d")
        keyboard.unhook_all()
        log("程序已终止。")

if __name__ == "__main__":
    hwnds = find_window_by_process_name(PROCESS_NAME)
    if not hwnds:
        log(f"未找到名为 {PROCESS_NAME} 的窗口")
    else:
        hwnd = hwnds[0]
        log("开始监控窗口：", win32gui.GetWindowText(hwnd))
        monitor_window(hwnd)
