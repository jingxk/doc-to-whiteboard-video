# 变更日志

本仓库遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/) 格式，
版本语义遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

## [1.2.1] - 2026-11-07

### 修复（CI 与安装文档）

- GitHub Actions 在环境预检前安装 `ffmpeg`，补齐 Ubuntu runner 缺失的 `ffmpeg` / `ffprobe`
- README.md / SKILL.md 明确 `ffprobe` 随 `ffmpeg` 一起安装，并给出可直接执行的 Ubuntu 命令
- 不改变视频生成流程，不引入任何上游技能依赖，仍是单一仓库自包含安装包

## [1.2.0] - 2026-11-07

### 重大变更：自包含安装包

- **内嵌白板渲染器，移除对上游技能 `srt-whiteboard-animation` 的依赖**：画面渲染所需的 `render_stream_whiteboard.py` / `stream_render.py` / `merge_scenes.py` 已 vendoring 进 `scripts/render/`，用户只需安装本技能一个仓库即可跑完整流程
- **笔尖素材内置无字版** `assets/drawing-hand.png`（已抹除原始笔杆品牌字）
- 新增 `THIRD_PARTY_LICENSES.md`：保留上游 MIT 许可证全文与改动记录（符合 MIT 署名要求）
- `check_env.py` 改为检查内嵌 `scripts/render/`，不再要求安装上游技能
- SKILL.md / README.md / pitfalls.md 全面更新，明确「单一仓库、单条 clone 即可用」
- 统一安装路径与环境预检输出；质检门禁改为仓库内置规范，不要求额外安装任何技能
- Release 归档采用规范顶层目录，并排除本地缓存与中间产物

## [1.1.0] - 2026-11-07

### 修复（安装与首次使用体验）

- **requirements.txt 补齐 `opencv-python`**：上游渲染器需要，此前缺失导致阶段2报 `ModuleNotFoundError: No module named 'cv2'`
- **requirements.txt 补齐 `python-docx`**：`extract_doc.py` 解析 .docx 需要，此前缺失导致阶段1报 `ModuleNotFoundError: No module named 'docx'`
- **`burn_subtitles.py` 字体跨平台**：不再硬编码 macOS 字体路径，自动探测 macOS / Linux / Windows 中文字体，均找不到时用 `--font` 指定
- **新增 `scripts/check_env.py`**：一键环境预检，逐项报告 Python 依赖 / ffmpeg / 渲染组件是否就绪，可用于 CI

### 文档

- SKILL.md / README.md 重写当时的双仓库安装流程
- `references/pitfalls.md` 新增「6.5 环境与安装」小节，汇总安装期踩坑
- 标注上游 `drawing-hand.png` 笔杆含品牌字，并内置无字替代素材

## [1.0.0] - 2026-10-25

首个公开版本。由一次真实交付（人口结构拐点下的跨周期资产配置与风险控制战略建议书，394s 成片）完整复盘沉淀而成。

### 新增

- 六阶段流水线：文档解析 → 分幕 → 旁白 + 多音字消歧 → TTS 配音 + BGM 混音 → 硬字幕烧录 → 质检封装
- 八支脚本：`extract_doc.py`（中文单字换行重组）、`polyphone_fix.py`、`gen_tts.py`（支持 `--only` 局部重录）、`make_timeline.py`（连续时间轴）、`build_audio.py`（apad 补齐 + BGM）、`burn_subtitles.py`（断句 + 烧录）、`mux_final.py`、`verify_output.py`
- 四份参考：`pitfalls.md`（30+ 条实测踩坑）、`voice-engine.md`（TTS 选型与多音字替换表）、`narration-craft.md`（旁白工艺）、`qa-gates.md`（质检门禁）
- 内置 BGM：`assets/bgm/steady-market-pulse.wav`（BudgetPixel，CC BY 4.0，附署名文件）
- 旁白稿模板 `assets/narration_template.json`
- GitHub 规范：CI（语法/JSON/署名检查）、Issue 与 PR 模板、MIT 许可（保留上游署名）

### 关键技术定论

- 配音锁定 edge-tts 7.3.1 晓晓（7.2.8 / 6.1.12 被微软 GEC 403）
- 多音字只能在文本层消歧（edge-tts 将 SSML `<phoneme>` 当文本朗读）
- 语音按段实际时长首尾相接铺满（段间 150ms），字数 = 时长 × 5.8
- 字幕必须 PyAV + PIL 烧录硬字幕（homebrew ffmpeg 无 libass，mov_text 软字幕多播放器不显示）
- 字幕每条 6–26 字渲染一行 + 字号 34，解决「偏大」实为堆行数问题
