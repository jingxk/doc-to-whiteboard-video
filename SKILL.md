---
name: doc-to-whiteboard-video
description: 把文档（PDF/Word/Markdown/纯文本）端到端做成「带自然语音配音 + BGM + 硬字幕」的白板手绘动画成品视频。本技能负责文档解析、分幕、旁白撰写与多音字消歧、edge-tts 晓晓配音、BGM 混音、硬字幕烧录、质检与封装；画面生成部分编排调用 srt-whiteboard-animation 技能。当用户给出文字/文档文件并要求「做成视频」「做成白板动画」「生成讲解视频」「文档转视频」时触发。
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
| 画面（线稿生成、标注、渲染、多幕合并） | **`srt-whiteboard-animation`**（本技能调用它，见 [geeklee/srt-whiteboard-animation](https://github.com/geeklee/srt-whiteboard-animation)，本仓库是其下游衍生） |
| 声音 + 字幕 + 封装 + 质检 | **本技能** |
| 字幕可读性门禁 | **`caption-access-desk`**（本技能调用它，可选；未安装时按 `references/qa-gates.md` 的硬性门禁人工核对） |

## 运行环境（强制）

所有脚本用**隔离的 Python 环境**，不要用损坏的技能自带 `.venv`（动态库常报
`libpython3.13.dylib not loaded`）。推荐任选其一：

```bash
# 方式 A：仓库内虚拟环境（推荐）
python3 -m venv .venv && . .venv/bin/activate

# 方式 B：系统 Python（需自行装好下列依赖）
PY=python3
```

依赖：`edge-tts==7.3.1`、`av`(PyAV)、`Pillow`、`numpy`、`pypdf`，
另需系统 PATH 中可用的 `ffmpeg`。

```bash
pip install -r requirements.txt
# 缺失个别包时：$PY -m pip install edge-tts==7.3.1 av Pillow numpy pypdf
```

## 流水线

```
[阶段1] 解析文档 → 分幕策略
[阶段2] 生成画面（交给 srt-whiteboard-animation）
[阶段3] 撰写旁白稿 + 多音字消歧
[阶段4] TTS 配音 → 连续时间轴 → BGM 混音
[阶段5] 硬字幕烧录
[阶段6] 质检 → 封装 → 交付
```

### 阶段 1：解析文档 → 分幕策略

```bash
$PY scripts/extract_doc.py <输入文件> -o /tmp/doc.txt
```

- 通读全文，**按内容章节拆成 10–14 幕**，每幕只表达一个核心意思
- 输出分幕策略表（编号 / 核心表达 / 画面主体 / 建议时长 25–35s），**等待用户确认**

### 阶段 2：生成画面

**加载 `srt-whiteboard-animation` 技能**，按它的 7 步确认关卡执行（线稿 → 标注 → 预览 → 调整 → 渲染 → 合并）。

产出：`<项目>-白板动画成片-无音轨.mp4`，记录其**精确时长**（后续所有计算的基准）。

> 该技能默认每步等待确认。用户若说「继续推进」，可连续执行。

### 阶段 3：旁白稿 + 多音字消歧

按 `references/narration-craft.md` 撰写，**口语化扩写**（不是照念原文）。

字数目标：`时长(s) × 5.8`。例：394s → 约 2285 字。

```bash
# 扫描风险（只读）
$PY scripts/polyphone_fix.py audio/narration.json
# 执行替换（会写回文件）
$PY scripts/polyphone_fix.py audio/narration.json --apply
```

**必须先消歧再生成语音**——edge-tts 不支持 SSML 注音，出错只能靠改文本。
详见 `references/voice-engine.md`。

### 阶段 4：配音 → 连续时间轴 → 混音

```bash
# 4.1 生成语音（晓晓 +30%）
$PY scripts/gen_tts.py audio/narration.json --outdir audio/tts \
    --voice zh-CN-XiaoxiaoNeural --rate=+30%

# 4.2 连续时间轴（首尾相接铺满，消除静默）
$PY scripts/make_timeline.py audio/narration.json --tts-dir audio/tts \
    --out audio/timeline.json --target-ms <视频时长ms>

# 4.3 合成音轨（BGM 音量 0.08）
$PY scripts/build_audio.py --tts-dir audio/tts --timeline audio/timeline.json \
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
$PY scripts/burn_subtitles.py --src <无音轨.mp4> --narration audio/narration.json \
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
$PY scripts/mux_final.py --video <带字幕无音轨.mp4> --audio audio/final_track.wav \
    --out <成品>.mp4

# 6.2 端到端自检
$PY scripts/verify_output.py <成品>.mp4 --step 15 --frames 20,60,150,300
```

字幕可读性质检：用 `caption-access-desk` 技能跑 lint，
目标 **等级 A（≥90 分）、致命 0 项**。流程见 `references/qa-gates.md`。

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
