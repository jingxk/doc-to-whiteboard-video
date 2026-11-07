# 文档白板视频工坊 · doc-to-whiteboard-video

把一份**文档**（PDF / Word / Markdown / 纯文本）端到端做成「带自然语音配音 + BGM + 硬字幕」的白板手绘动画成品视频。画面是暖米黄纸张底的手绘动画，声音是微软晓晓神经网络语音（连续无空白），字幕直接烧录进画面，输出即可播放的 MP4。

本仓库是**自包含安装包**：白板画面渲染器（从上游 [srt-whiteboard-animation](https://github.com/geeklee/srt-whiteboard-animation) vendoring 而来，已内嵌于 `scripts/render/`）负责「线稿 → 白板画面」，本技能补齐「文档 → 分幕/旁白 → 配音 → 字幕 → 成品」的完整链路，无需安装任何上游技能。

## 核心能力

- **文档解析**：PDF / Word / Markdown / 纯文本一键提取，内置中文单字换行重组
- **分幕策略**：按内容章节拆 10–14 幕，每幕只表达一个核心意思
- **旁白撰写**：口语化扩写（不是照念原文），字数 = 视频时长 × 5.8
- **多音字消歧**：edge-tts 不支持 SSML 注音，在文本层替换消歧（内置常见错读表）
- **TTS 配音**：edge-tts 晓晓语音，+30% 语速，连续时间轴首尾相接铺满、消除幕间静默
- **BGM 混音**：内置 CC BY 4.0 垫乐（`assets/bgm/steady-market-pulse.wav`），人声优先
- **硬字幕烧录**：PyAV + PIL 逐帧绘制，不依赖 libass；自动断句每条 6–26 字一行
- **质检门禁**：字幕可读性（停留时长 / 行宽 / 间隔）+ 音视频端到端自检

## 工作方式

六阶段流水线，每阶段产物落盘、可单独重跑：

```text
[阶段1] 解析文档 → 分幕策略（等待确认）
[阶段2] 生成画面（内嵌渲染器 scripts/render/）
[阶段3] 撰写旁白稿 + 多音字消歧
[阶段4] TTS 配音 → 连续时间轴 → BGM 混音
[阶段5] 硬字幕烧录
[阶段6] 质检 → 封装 → 交付
```

## 快速开始

### 1. 安装本技能（自包含，无需上游）

```bash
git clone https://github.com/jingxk/doc-to-whiteboard-video.git \
  ~/.codex/skills/doc-to-whiteboard-video
```

画面渲染器已内嵌在 `scripts/render/`，笔尖素材 `assets/drawing-hand.png` 已为无字干净版。

### 2. 环境准备

```bash
cd ~/.codex/skills/doc-to-whiteboard-video
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
# 另需系统 PATH 中可用的 ffmpeg / ffprobe
# Ubuntu: sudo apt-get update && sudo apt-get install -y ffmpeg
```

### 3. 环境预检（推荐）

```bash
python scripts/check_env.py
```

末行输出 `PASS` 即可开始；`FAIL` 会告诉你要装什么。也可集成进 CI。

### 4. 解析文档，制定分幕策略

```bash
python scripts/extract_doc.py <输入文件> -o /tmp/doc.txt
```

通读全文，按内容章节拆成 10–14 幕，每幕只表达一个核心意思，输出分幕策略表
（编号 / 核心表达 / 画面主体 / 建议时长 25–35s）。

### 5. 生成画面（内嵌渲染器）

为每幕生成暖米黄线稿 PNG（**禁止任何文字/数字/字母**）并写同名 `annotation.json`，
用内嵌渲染器逐幕渲染后再合并：

```bash
python scripts/render/render_stream_whiteboard.py <线稿.png> <标注.json> <输出.mp4>
python scripts/render/merge_scenes.py --inputs 幕1.mp4 幕2.mp4 ... --output <无音轨.mp4>
```

得到无音轨成片并记录其精确时长。

### 6. 旁白稿 + 多音字消歧

按 `references/narration-craft.md` 口语化扩写，字数目标 = 时长(s) × 5.8。

```bash
python scripts/polyphone_fix.py audio/narration.json          # 只读扫描
python scripts/polyphone_fix.py audio/narration.json --apply  # 执行替换
```

### 7. 配音 → 连续时间轴 → 混音

```bash
python scripts/gen_tts.py audio/narration.json --outdir audio/tts \
    --voice zh-CN-XiaoxiaoNeural --rate=+30%

python scripts/make_timeline.py audio/narration.json --tts-dir audio/tts \
    --out audio/timeline.json --target-ms <视频时长ms>

python scripts/build_audio.py --tts-dir audio/tts --timeline audio/timeline.json \
    --bgm assets/bgm/steady-market-pulse.wav --total-ms <视频时长ms> \
    --out audio/final_track.wav
```

### 8. 烧录硬字幕

```bash
python scripts/burn_subtitles.py --src <无音轨.mp4> --narration audio/narration.json \
    --timeline audio/timeline.json --out <带字幕无音轨.mp4> \
    --font-size 34 --max-chars 26
```

> 跨平台中文字体自动探测（macOS/Linux/Windows），也可用 `--font` 显式指定。

### 9. 质检 → 封装 → 交付

```bash
python scripts/mux_final.py --video <带字幕无音轨.mp4> --audio audio/final_track.wav \
    --out <成品>.mp4

python scripts/verify_output.py <成品>.mp4 --step 15 --frames 20,60,150,300
```

最后必须**人工终检**：听开头 30s、跳听 3 个中段、看字幕观感、看结尾是否静音。

## 关键参数速查

| 参数 | 值 | 说明 |
|---|---|---|
| TTS 引擎 | edge-tts 7.3.1 / zh-CN-XiaoxiaoNeural | 唯一实测可用版本，其他被微软 403 |
| 语速 | +30% | ≈5.8 字/秒 |
| 旁白字数 | 时长 × 5.8 | 宁多勿少 |
| 段间衔接 | 150ms | 连续感 |
| 首段偏移 | 800ms | 开场呼吸 |
| BGM 音量 | 0.08 | 垫底不盖人声 |
| 字幕字号 | 34（1080×720） | 画面高度 4–5% |
| 字幕每条 | 6–26 字 | 渲染 1 行 |
| 字幕间隔 | 100ms | ≥2 帧@60fps |
| 视频码率 | 8Mbps | 硬字幕重编码保画质 |

## 目录结构

```text
doc-to-whiteboard-video/
├── SKILL.md                          # 完整工作流与约束（技能入口）
├── README.md
├── LICENSE                           # MIT（保留上游署名）
├── requirements.txt                  # Python 依赖（edge-tts==7.3.1 等）
├── CHANGELOG.md
├── agents/openai.yaml                # Codex 元数据
├── scripts/                          # 脚本：解析/消歧/配音/时间轴/混音/烧录/封装/自检/环境预检
│   └── render/                         # 内嵌白板渲染器（vendored，无需上游技能）
├── references/                       # 踩坑清单、语音引擎、旁白工艺、质检门禁
├── THIRD_PARTY_LICENSES.md       # 上游 MIT 许可证全文与改动记录
└── assets/
    ├── bgm/steady-market-pulse.wav   # 内置 BGM（CC BY 4.0，需署名，见 bgm/ATTRIBUTION.md）
    ├── drawing-hand.png              # 无字笔尖/手部素材
    └── narration_template.json       # 旁白稿模板
```

## 踩坑提示（动手前必读）

`references/pitfalls.md` 沉淀了 30+ 条实测踩坑，五条最关键的：

1. **配音必须 edge-tts 晓晓**，且锁定 `7.3.1`（7.2.8 / 6.1.12 被微软 GEC 403）；画面渲染器已内嵌 `scripts/render/`，无需安装上游技能
2. **多音字只能在文本层消歧**——edge-tts 会把 SSML `<phoneme>` 当普通文本朗读
3. **语音必须首尾相接铺满**视频全长，按幕均分时间轴会造成幕间静默
4. **字幕必须烧录硬字幕**——homebrew ffmpeg 常无 libass，mov_text 软字幕很多播放器不显示
5. **字幕「偏大」的真凶是堆行数不是字号**——整段旁白要断成 6–26 字一条
6. **笔尖素材已内置无字版**——`assets/drawing-hand.png` 已抹除原始品牌字，下游视频不会再露出第三方标识
7. **av 与 opencv-python 共存可能报 libavdevice 冲突**——warning 可忽略；若崩溃，按 `check_env.py` 输出排查

## BGM 署名

`assets/bgm/steady-market-pulse.wav` 为 BudgetPixel 作品，采用 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议。再分发本仓库或由其生成的视频时，请保留署名，详见 `assets/bgm/ATTRIBUTION.md`。

## 第三方组件与署名

白板画面渲染器（`scripts/render/`）vendoring 自 [geeklee/srt-whiteboard-animation](https://github.com/geeklee/srt-whiteboard-animation)（MIT）。笔尖素材已抹除原始品牌字，上游许可证全文与改动记录见 [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md)。

## 贡献

欢迎提交 Issue 或 Pull Request。任何涉及配音、字幕、封装的改动，请用真实文档端到端跑一遍并附上成片抽帧验证。

## 许可证

本项目基于 MIT License 开源（保留上游版权声明），详见 [LICENSE](LICENSE)。
