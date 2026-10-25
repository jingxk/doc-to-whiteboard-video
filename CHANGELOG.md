# 变更日志

本仓库遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/) 格式，
版本语义遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

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
