# autokey.py
import sys
import time
import random
import keyboard
from datetime import datetime

def log(*args, sep=' ', end='\n'):
    """带时间前缀的打印函数，支持多个参数"""
    now = datetime.now().strftime("[%H:%M:%S]")
    print(now, *args, sep=sep, end=end)

def auto_key_press(key, max_delay_ms):
    """
    自动按键主函数
    :param key: 要按的键名
    :param max_delay_ms: 最大延迟毫秒数
    """
    isRunning = [True]
    
    def on_esc_press(e):
        if e.event_type == keyboard.KEY_DOWN and e.name.lower() in ('esc', '~', 'q', 'ctrl'):
            log(f"检测到 {e.name} 键按下，程序即将退出...")
            isRunning[0] = False

    # 注册退出热键
    keyboard.on_press(on_esc_press)
    log(f"开始{key}连按，每次{max_delay_ms}ms内随机间隔")
    log("按 Esc/~/Q/Ctrl 键可随时退出")
    
    try:
        while isRunning[0]:
            # 生成随机延迟（0到max_delay_ms之间）
            delay_ms = random.randint(50, max_delay_ms)  # 最小50ms避免过快
            delay_s = delay_ms / 1000.0
            
            log(f"等待 {delay_ms}ms 后按下 {key}")
            time.sleep(delay_s)
            
            if not isRunning[0]:  # 在延迟期间可能被退出
                break
                
            # 按下并释放按键
            keyboard.press(key)
            time.sleep(0.05)  # 短暂按住50ms
            keyboard.release(key)
            log(f"按下 {key}")
            
    except Exception as e:
        log("发生异常：", e)
    finally:
        keyboard.unhook_all()
        log("程序已终止。")

def main():
    """主程序入口"""
    sys.stdout.reconfigure(encoding='utf-8')
    
    try:
        # 获取用户输入
        delay_input = input("请输入延迟随机范围ms: ")
        max_delay_ms = int(delay_input)
        
        if max_delay_ms <= 0:
            print("延迟时间必须大于0")
            return
            
        key_input = input("请输入需要连按的按键: ").strip()
        if not key_input:
            print("按键不能为空")
            return
            
        # 开始自动按键
        auto_key_press(key_input, max_delay_ms)
        
    except ValueError:
        print("延迟时间必须是有效的数字")
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序出错: {e}")

if __name__ == "__main__":
    main()
