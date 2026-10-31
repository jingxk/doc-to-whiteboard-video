# 文档白板视频工坊 · doc-to-whiteboard-video

把一份**文档**（PDF / Word / Markdown / 纯文本）端到端做成「带自然语音配音 + BGM + 硬字幕」的白板手绘动画成品视频。画面是暖米黄纸张底的手绘动画，声音是微软晓晓神经网络语音（连续无空白），字幕直接烧录进画面，输出即可播放的 MP4。

本仓库是 [srt-whiteboard-animation](https://github.com/geeklee/srt-whiteboard-animation) 的**下游衍生技能（fork）**：上游负责「字幕 → 白板画面」，本技能补齐「文档 → 字幕/旁白 → 配音 → 字幕 → 成品」的完整链路。

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
[阶段2] 生成画面（调用 srt-whiteboard-animation）
[阶段3] 撰写旁白稿 + 多音字消歧
[阶段4] TTS 配音 → 连续时间轴 → BGM 混音
[阶段5] 硬字幕烧录
[阶段6] 质检 → 封装 → 交付
```

## 快速开始

### 1. 环境准备

```bash
git clone https://github.com/jingxk/doc-to-whiteboard-video.git
cd doc-to-whiteboard-video
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
# 另需系统 PATH 中可用的 ffmpeg
```

### 2. 解析文档，制定分幕策略

```bash
python scripts/extract_doc.py <输入文件> -o /tmp/doc.txt
```

通读全文，按内容章节拆成 10–14 幕，每幕只表达一个核心意思，输出分幕策略表（编号 / 核心表达 / 画面主体 / 建议时长 25–35s）。

### 3. 生成画面

加载 `srt-whiteboard-animation` 技能（[上游仓库](https://github.com/geeklee/srt-whiteboard-animation)），按它的七步确认关卡执行（线稿 → 标注 → 预览 → 调整 → 渲染 → 合并），得到无音轨成片并记录其**精确时长**——后续所有计算的基准。

### 4. 旁白稿 + 多音字消歧

按 `references/narration-craft.md` 口语化扩写，字数目标 = 时长(s) × 5.8。模板见 `assets/narration_template.json`。

```bash
python scripts/polyphone_fix.py audio/narration.json          # 扫描风险（只读）
python scripts/polyphone_fix.py audio/narration.json --apply  # 执行替换
```

### 5. 配音 → 连续时间轴 → 混音

```bash
python scripts/gen_tts.py audio/narration.json --outdir audio/tts \
    --voice zh-CN-XiaoxiaoNeural --rate=+30%

python scripts/make_timeline.py audio/narration.json --tts-dir audio/tts \
    --out audio/timeline.json --target-ms <视频时长ms>

python scripts/build_audio.py --tts-dir audio/tts --timeline audio/timeline.json \
    --bgm assets/bgm/steady-market-pulse.wav --total-ms <视频时长ms> \
    --out audio/final_track.wav
```

### 6. 烧录硬字幕

```bash
python scripts/burn_subtitles.py --src <无音轨.mp4> --narration audio/narration.json \
    --timeline audio/timeline.json --out <带字幕无音轨.mp4> \
    --font-size 34 --max-chars 26
```

### 7. 质检 → 封装 → 交付

```bash
python scripts/mux_final.py --video <带字幕无音轨.mp4> --audio audio/final_track.wav \
    --out <成品>.mp4

python scripts/verify_output.py <成品>.mp4 --step 15 --frames 20,60,150,300
```

字幕可读性质检用 `caption-access-desk` 技能跑 lint，目标**等级 A（≥90 分）、致命 0 项**；流程与基线见 `references/qa-gates.md`。**最后必须人工终检**：听开头 30s、跳听 3 个中段、看字幕观感、看结尾是否静音。

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
├── scripts/                          # 八支脚本：解析/消歧/配音/时间轴/混音/烧录/封装/自检
├── references/                       # 踩坑清单、语音引擎、旁白工艺、质检门禁
└── assets/
    ├── bgm/steady-market-pulse.wav   # 内置 BGM（CC BY 4.0，需署名，见 bgm/ATTRIBUTION.md）
    └── narration_template.json       # 旁白稿模板
```

## 踩坑提示（动手前必读）

`references/pitfalls.md` 沉淀了 30+ 条实测踩坑，五条最关键的：

1. **配音必须 edge-tts 晓晓**，且锁定 `7.3.1`（7.2.8 / 6.1.12 被微软 GEC 403）
2. **多音字只能在文本层消歧**——edge-tts 会把 SSML `<phoneme>` 当普通文本朗读
3. **语音必须首尾相接铺满**视频全长，按幕均分时间轴会造成幕间静默
4. **字幕必须烧录硬字幕**——homebrew ffmpeg 常无 libass，mov_text 软字幕很多播放器不显示
5. **字幕「偏大」的真凶是堆行数不是字号**——整段旁白要断成 6–26 字一条

## BGM 署名

`assets/bgm/steady-market-pulse.wav` 为 BudgetPixel 作品，采用 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议。再分发本仓库或由其生成的视频时，请保留署名，详见 `assets/bgm/ATTRIBUTION.md`。

## 上游致意

本仓库fork自 [geeklee/srt-whiteboard-animation](https://github.com/geeklee/srt-whiteboard-animation)（MIT），画面生成阶段完全依赖上游技能，请一并前往上游仓库 Star。

## 贡献

欢迎提交 Issue 或 Pull Request。任何涉及配音、字幕、封装的改动，请用真实文档端到端跑一遍并附上成片抽帧验证。

## 许可证

本项目基于 MIT License 开源（保留上游版权声明），详见 [LICENSE](LICENSE)。
