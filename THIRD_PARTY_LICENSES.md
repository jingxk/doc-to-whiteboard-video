# 第三方许可证与署名

本仓库为**自包含安装包**，画面渲染所需的白板流式笔迹渲染器已内嵌于
`scripts/render/`，无需额外安装上游技能。

## 内嵌组件：白板流式笔迹渲染器

来源：[geeklee/srt-whiteboard-animation](https://github.com/geeklee/srt-whiteboard-animation)
（MIT License，本仓库是其下游衍生，已 vendoring 进 `scripts/render/`）

内嵌文件：
- `scripts/render/render_stream_whiteboard.py` — 整合渲染器（mask 编排 + stream 画法）
- `scripts/render/stream_render.py` — 单图流式笔迹渲染核心
- `scripts/render/merge_scenes.py` — 多幕合并
- `assets/drawing-hand.png` — 笔尖/手部素材（**已抹除原始笔杆上的品牌字**，替换为正版无字版）

### 对上游代码的改动
- 笔尖素材 `drawing-hand.png`：移除了笔杆上印制的作者品牌字，避免下游视频露出第三方标识。
- 渲染器运行所需的 Python 依赖（`opencv-python`、`numpy`、`Pillow`）已并入本仓库 `requirements.txt`。
- 上游渲染脚本中一处调用 `_lay_ink(..., None)` 多传参数的 bug 已修正（`render_stream_whiteboard.py`）。

以下为上游原始 MIT 许可证全文：

```
MIT License

Copyright (c) 2026 江哥是老登啊

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
