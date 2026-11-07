---
name: doc-to-whiteboard-video
description: 把文档（PDF/Word/Markdown/纯文本）端到端做成「带自然语音配音 + BGM + 硬字幕」的白板手绘动画成品视频。本技能负责文档解析、分幕、旁白撰写与多音字消歧、edge-tts 晓晓配音、BGM 混音、硬字幕烧录、质检与封装，并内嵌白板流式笔迹渲染器（scripts/render/）生成画面。当用户给出文字/文档文件并要求「做成视频」「做成白板动画」「生成讲解视频」「文档转视频」时触发。
---

# 文档 → 白板动画成品视频

把一份文档变成可直接播放的成品 MP4：**画面**是暖米黄纸底的白板手绘动画，
**声音**是微软晓晓神经网络语音（连续无空白）+ 垫乐 BGM，**字幕**烧录进画面。

## 何时使用

- 用户给一份 PDF/Word/Markdown/纯文本，要求做成视频、讲解视频、白板动画
- 用户要求给视频配音、加字幕、加 BGM

## 与其他技能的分工

| 环节 | 负责技能 |
|---|---|
| 画面（线稿生成、标注、渲染、多幕合并） | **本技能内嵌**（`scripts/render/`，从上游 vendoring，无需外装） |
| 声音 + 字幕 + 封装 + 质检 | **本技能** |
| 字幕可读性门禁 | **本仓库内置规范**（`references/qa-gates.md`，无需额外安装技能） |

## 安装（首次使用，必读）

本技能为**自包含安装包**，画面渲染器已内嵌（`scripts/render/`），无需安装任何上游技能。

### 1. 安装本技能

```bash
git clone https://github.com/jingxk/doc-to-whiteboard-video.git \
  ~/.codex/skills/doc-to-whiteboard-video
```

或直接把仓库目录放进 `~/.codex/skills/doc-to-whiteboard-video/`（技能靠 `SKILL.md` 识别）。

### 2. 建 Python 环境并装依赖

```bash
cd ~/.codex/skills/doc-to-whiteboard-video
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
```

依赖清单：`edge-tts==7.3.1`、`av`(PyAV)、`Pillow`、`numpy`、`pypdf`、
`opencv-python`（内嵌画面渲染器需要）、`python-docx`（解析 .docx 需要）。
系统还需 PATH 中可用的 **ffmpeg** 与 **ffprobe**（macOS: `brew install ffmpeg`；
Ubuntu: `sudo apt-get update && sudo apt-get install -y ffmpeg`）。

> 不要把技能仓库自带的 `.git` 内 `.venv` 当作运行环境（动态库常损坏，
> 报 `libpython3.13.dylib not loaded`）。始终用自己新建的 `.venv` 或系统 Python。

### 3. 一键环境预检（推荐）

```bash
python scripts/check_env.py
```

逐项检查 Python 依赖、ffmpeg/ffprobe、内嵌渲染器与笔尖素材，末行 `PASS` 才可开始；
`FAIL` 会直接告诉你缺什么、怎么补。也可用于 CI。

## 字体说明（字幕烧录）

`burn_subtitles.py` 会按优先级自动探测中文字体（macOS 的 STHeiti/PingFang、
Linux 的 Noto Sans CJK、Windows 的微软雅黑/黑体）。若都找不到，用 `--font`
显式指定任意含中文字形的 TTF/TTC：

```bash
python scripts/burn_subtitles.py ... --font /path/to/NotoSansCJK-Regular.ttc
```

## 流水线

```
[阶段1] 解析文档 → 分幕策略
[阶段2] 生成画面（内嵌渲染器 scripts/render/）
[阶段3] 撰写旁白稿 + 多音字消歧
[阶段4] TTS 配音 → 连续时间轴 → BGM 混音
[阶段5] 硬字幕烧录
[阶段6] 质检 → 封装 → 交付
```

### 阶段 1：解析文档 → 分幕策略

```bash
python scripts/extract_doc.py <输入文件> -o /tmp/doc.txt
```

- 通读全文，**按内容章节拆成 10–14 幕**，每幕只表达一个核心意思
- 输出分幕策略表（编号 / 核心表达 / 画面主体 / 建议时长 25–35s），**等待用户确认**

### 阶段 2：生成画面（本技能内嵌渲染器）

本技能已内嵌白板流式笔迹渲染器（`scripts/render/`），**无需安装上游技能**。

1. 用 ImageGen 生成每幕线稿 PNG（暖米黄 `#F5EBD7` 底、**绝对禁止任何文字/数字/字母**，文字全靠硬字幕）
2. 为每张线稿写同名 `scene-NN.annotation.json`（region / sequence / startMs / protectedRegions / sceneDurationMs，详见 `references/pitfalls.md` 与本仓库内嵌渲染器约定）
3. 逐幕渲染：
   ```bash
   python scripts/render/render_stream_whiteboard.py <线稿.png> <标注.json> <输出.mp4>        [assets/drawing-hand.png]
   ```
   可选 `--ink-path grid|skeleton`、`--color-fill contour-wipe|brush`、`--total-ms <毫秒>`。
4. 多幕合并：
   ```bash
   python scripts/render/merge_scenes.py --inputs 幕1.mp4 幕2.mp4 ... --output <无音轨.mp4>
   ```

产出：`<项目>-白板动画成片-无音轨.mp4`，记录其**精确时长**（后续所有计算的基准）。

### 阶段 3：旁白稿 + 多音字消歧

按 `references/narration-craft.md` 撰写，**口语化扩写**（不是照念原文）。

字数目标：`时长(s) × 5.8`。例：394s → 约 2285 字。

```bash
# 扫描风险（只读）
python scripts/polyphone_fix.py audio/narration.json
# 执行替换（会写回文件）
python scripts/polyphone_fix.py audio/narration.json --apply
```

**必须先消歧再生成语音**——edge-tts 不支持 SSML 注音，出错只能靠改文本。
详见 `references/voice-engine.md`。

### 阶段 4：配音 → 连续时间轴 → 混音

```bash
# 4.1 生成语音（晓晓 +30%）
python scripts/gen_tts.py audio/narration.json --outdir audio/tts \
    --voice zh-CN-XiaoxiaoNeural --rate=+30%

# 4.2 连续时间轴（首尾相接铺满，消除静默）
python scripts/make_timeline.py audio/narration.json --tts-dir audio/tts \
    --out audio/timeline.json --target-ms <视频时长ms>

# 4.3 合成音轨（BGM 音量 0.08）
python scripts/build_audio.py --tts-dir audio/tts --timeline audio/timeline.json \
    --bgm assets/bgm/steady-market-pulse.wav --total-ms <视频时长ms> \
    --out audio/final_track.wav
```

- **语音必须连续**：`make_timeline.py` 按每段实际时长串联（段间 150ms），
  不按幕均分。语音短于视频 >8s 会告警，需补写旁白。
- 内置 BGM：`assets/bgm/steady-market-pulse.wav`（BudgetPixel，CC BY 4.0，
  专为金融/知识旁白设计，49.97s 循环）。发布需署名。
- 换 BGM 时先 `ffmpeg -i bgm.wav -af volumedetect` 测响度，再定 `--bgm-volume`
  （底噪 -14dB 用 0.08；更响的要更低）。

### 阶段 5：硬字幕烧录

```bash
python scripts/burn_subtitles.py --src <无音轨.mp4> --narration audio/narration.json \
    --timeline audio/timeline.json --out <带字幕无音轨.mp4> \
    --font-size 34 --max-chars 26
```

- **必须烧录硬字幕**：ffmpeg 无 libass，mov_text 软字幕很多播放器不显示
- 脚本自动断句：**每条 6–26 字渲染 1 行**，停留 0.83–7s，相邻留 100ms
- 字号参考：1080×720 用 34（画面高度 4–5%）
- 24000 帧约需 7 分钟，务必 `run_in_background`

### 阶段 6：质检 → 封装 → 交付

```bash
# 6.1 封装
python scripts/mux_final.py --video <带字幕无音轨.mp4> --audio audio/final_track.wav \
    --out <成品>.mp4

# 6.2 端到端自检
python scripts/verify_output.py <成品>.mp4 --step 15 --frames 20,60,150,300
```

字幕可读性质检：按 `references/qa-gates.md` 的硬性门禁逐项核对，
重点检查每条 6–26 字、单行、停留 0.83–7s、相邻间隔 ≥2 帧、BGM 署名。
可用 `scripts/verify_output.py` 做客观项自检，并保留人工终检。

**最后必须人工终检**：听开头 30s、跳听 3 个中段、看字幕观感、看结尾是否静音。
脚本只能查「有没有」，查不了「好不好」。

## 关键参数速查

| 参数 | 值 | 说明 |
|---|---|---|
| TTS 引擎 | edge-tts 7.3.1 / zh-CN-XiaoxiaoNeural | 唯一版本可用，其他被 403 |
| 语速 | +30% | ≈5.8 字/秒 |
| 旁白字数 | 时长 × 5.8 | 宁多勿少 |
| 段间衔接 | 150ms | 连续感 |
| 首段偏移 | 800ms | 开场呼吸 |
| BGM 音量 | 0.08 | 垫底不盖人声 |
| 字幕字号 | 34（1080×720） | 画面高度 4–5% |
| 字幕每条 | 6–26 字 | 渲染 1 行 |
| 字幕间隔 | 100ms | ≥2 帧@60fps |
| 视频码率 | 8Mbps | 硬字幕重编码保画质 |

## 目录约定

```text
assets/whiteboard/<项目名>/
  scene-NN-<名称>.png / .annotation.json / -whiteboard.mp4   # 画面（阶段2）
  <项目名>-白板动画成片-无音轨.mp4                            # 阶段2 产物
  <项目名>-白板动画成片-带字幕无音轨.mp4                      # 阶段5 产物
  <项目名>-白板动画成片-最终版<日期>.mp4                      # 交付
  audio/
    narration.json        # 旁白稿
    tts/cueNN.mp3         # TTS 语音
    timeline.json         # 连续时间轴
    voice_track.wav       # 纯语音轨
    final_track.wav       # 含 BGM 最终音轨
```

## 参考资料

- `references/pitfalls.md` — 踩坑清单（30+ 条，动手前必读）
- `references/voice-engine.md` — TTS 引擎选型、多音字替换表
- `references/narration-craft.md` — 旁白撰写规范、口语化对照
- `references/qa-gates.md` — 质检门禁与达标基线
- `assets/narration_template.json` — 旁白稿模板
- `assets/bgm/steady-market-pulse.wav` — 内置 BGM（CC BY 4.0，需署名）
