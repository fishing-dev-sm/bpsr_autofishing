## 星痕共鸣自动钓鱼（改进版）

### 重要声明
- **非盈利**：本项目仅供学习与研究使用，严禁任何形式的商业化利用。
- **非侵入**：不修改游戏文件、不注入进程，仅通过屏幕截图与模拟键鼠交互实现自动化。
- **视觉方案**：全部逻辑基于图像与颜色识别（ROI/HSV/均值等），不进行内存读写或网络拦截。

本项目是在上游项目的基础上进行功能改进与参数优化的自动钓鱼脚本，主要面向 Windows 平台的《星痕共鸣》游戏。

上游仓库（致谢）：[xxfttkx/auto_fish](https://github.com/xxfttkx/auto_fish)

### 功能特性
- 截图与窗口控制：使用 mss 截取客户区画面，自动适配 DPI 缩放；基于窗口句柄进行点击、按压。
- 分辨率自适应：以 1920×1080 为基准，运行时对坐标/尺寸进行等比缩放，适配常见 16:9 分辨率。
- 红点识别与上钩：在指定搜索区域内滑动检测红色占比，结合白色占比变化判定“上钩”。
- 鱼跑了检测：通过指定 ROI 的蓝绿色均值匹配进行“鱼跑了”识别。
- 遛鱼方向（新版）：
  - 以 A(794,540)/D(1124,540) 为中心的 20×20 方框做红/橙色像素占比检测；
  - 采用“触发-锁定-切换”策略：
    - A 触发后持续按 A，仅当 D 触发才切到 D；反之亦然；
    - 触发消失不会松键；同时触发保持当前方向；无方向则不按；
  - 每次触发、按下、释放都会输出日志。
- 自动换竿：检测右下区域“添加鱼竿”按钮，通过按键+两次点击自动更换。
- 会话统计：程序结束打印时间区间、成功率、单位时间效率（成功/分钟、成功/小时）。

### 重要说明（颜色判定限制）
- **强烈建议**：遛鱼方向依赖于判定区域内的红/橙色像素占比（A 判定点 `(794,540)`、D 判定点 `(1124,540)`，各自 `20×20` 方框，随分辨率缩放）。请确保角色外观不会在上述区域附近出现红/橙色元素，以免误触发方向键。
- **避免在判定区域出现干扰色**：包括但不限于发色/染发、服装染色、武器或时装特效、坐骑/宠物发光效果、UI 贴花等。
- **建议**：测试或挂机时尽量使用默认外观、降低特效亮度/粒子效果，确保场景中不出现大面积红/橙色。

### 目录结构
- `main.py`：主循环与整体流程
- `config.py`：所有可调坐标/阈值/延迟配置
- `color_util.py`：颜色相关识别（红/白/蓝绿、红橙检测）
- `window_util.py`：窗口/截图/坐标缩放、辅助函数
- `game_logic.py`：自动换竿逻辑
- `assets/`：模板图片
- `钓鱼流程分析.md`：流程与判定的中文说明文档

### 环境与依赖
- 平台：Windows（使用 `win32gui`、`pygetwindow`、`ctypes.windll` 等）
- Python：建议 3.9+
- 依赖安装：

```bash
pip install -r requirements.txt
```

### 快速开始
1. 进入游戏并打开钓鱼界面。
2. 运行脚本：

```bash
python main.py
```

3. 程序会自动聚焦到目标窗口并开始循环；按 `Esc`/`~`/`Q`/`Ctrl` 任意键可退出。

### 关键配置（`config.py`）
- 进程名：`PROCESS_NAME`（默认 `Star.exe`）
- 甩钩/收尾：`CLICK_POS`、`SECOND_CLICK_POS`、`START_DELAY`、`AFTER_SECOND_CLICK_DELAY`、`AFTER_DETECT_CLICK_DELAY`
- 红点搜索：`RED_SEARCH_REGION_CENTER`、`RED_SEARCH_REGION_OFFSET`、`RED_DETECT_BOX_SIZE`、`RED_THRESHOLD`
- 鱼跑了：`BLUE_ROI`、`BLUE_COLORS`、`BLUE_TOLERANCE`
- 完成判定：`COLOR_CHECK_AREA`、`TARGET_COLOR`
- 换竿：`ROD_NO_DURABILITY_KEY`、`ROD_CHANGE_CLICK_POS`、`ROD_CONFIRM_CLICK_POS`、`ROD_NO_DURABILITY_DELAY`
- 新版遛鱼方向：`AD_A_CENTER=(794,540)`、`AD_D_CENTER=(1124,540)`、`AD_BOX_SIZE=20`、`AD_RED_ORANGE_RATIO=0.10`

提示：若分辨率/UI 缩放不同，可优先调整中心与区域坐标；脚本会做等比缩放。

### 常见问题
- 识别偏移：请截图确认游戏窗口客户区位置与分辨率，必要时调整相关 ROI 坐标。
- 触发过敏/迟钝：微调 `AD_RED_ORANGE_RATIO` 或方框大小、中心坐标。
- 成功判定不触发：微调 `COLOR_CHECK_AREA` 与 `TARGET_COLOR`。
- 运行报缺依赖：确保 `pip install -r requirements.txt` 成功，并在 Windows 环境运行。

### 许可证
本项目基于 AGPL-3.0 许可证发布，详见仓库中的 `LICENSE` 文件。保留对上游项目的署名与链接。


