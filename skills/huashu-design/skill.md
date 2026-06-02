---
name: huashu-design
version: 1.0.0
description: HTML 原型设计技能 — Landing Page / App 原型 / 幻灯片 / 动画演示 / 信息图。基于华述设计系统，包含反 AI Slop 规范、品牌资产协议、20 设计风格、动画 5 段式。触发词：做个页面、设计一个 landing page、做个 PPT、做个动画、做个海报、App 原型、HTML 原型。
triggers:
  - "做个页面"
  - "设计一个 landing page"
  - "做个 PPT"
  - "做个幻灯片"
  - "做个动画"
  - "做个海报"
  - "App 原型"
  - "HTML 原型"
  - "信息图"
  - "产品介绍页"
  - "设计稿"
allowed-tools:
  - read_file
  - write_file
  - edit_file
  - exec
  - web_search
  - image_generate
required-commands:
  - node
  - npx
---

# Huashu Design — HTML 原型设计技能

## 核心原则

**这个 skill 不是为了做网站，而是为了做展示用的原型。**

- 输出是 HTML，但目的是**展示 / 提案 / 提案**
- PPT / PDF 只是 HTML 的导出格式
- 核心能力：Landing Page > App 原型 > 幻灯片 > Motion Demo > 信息图

---

## 第一阶段：理解需求（5 必问）

收到任务后，先问清楚：

```
1. 这是什么类型的页面？
   - Landing Page / App 原型 / 幻灯片 / 动画 / 信息图

2. 用户有没有 design system / UI kit / 品牌规范？
   - logo / 色彩 / 字体 / 产品图

3. 有没有参考的竞品或产品？
   - 可以去搜一下真实产品

4. 是给谁看的？
   - 内部演示 / 客户提案 / 投资人 / 内部决策

5. 需要哪些输出格式？
   - HTML 演示 / PDF / PPTX / MP4 / GIF
```

### 无 Design Context 时的 Fallback

如果用户说"没有"或"随便"：
1. 从竞品官网搜真实产品截图
2. 从品牌官网找 logo 和色彩
3. 用 **Radix Colors** 做配色（https://www.radix-ui.com/colors）
4. 字体选 **Instrument Serif + Geist Sans**（有特色但不冷门）
5. 写入 `brand-spec.md` 并标注 "assumption"

---

## 第二阶段：反 AI Slop 检查

在写任何代码之前，先做这个检查：

### 必须避免的（AI Slop）

| 类型 | AI 习惯（禁止） | 正确做法 |
|------|----------------|---------|
| **渐变** | rainbow / mesh gradient | 单色 subtle 渐变仅限 button hover |
| **卡片** | 12px 圆角 + 左 border accent | 用真实品牌色，不用通用样式 |
| ** Emoji** | bullet 加 emoji / CTA 按钮表情 | 专业设计不用 emoji |
| **SVG** | AI 生成的抽象人物/设备/场景 | 只用 icon(16-32px) / 包装元素 / data viz |
| **Icon** | 每个 feature 都加 icon | Less is more |
| **字体** | Inter / Roboto / Arial / Space Grotesk | Instrument Serif / Cormorant / Bricolage Grotesque |
| **Bento Grid** | 每个 AI landing page 都有 | 确认真实需要再使用 |
| **三段式** | hero + 3-col + testimonials | 打破重组 |
| **数据** | 编造的 "10,000+ 用户" | 用 placeholder 或真实数据 |
| **引用** | 假的用户评价 | 用 placeholder |

### 三大原则

1. **Don't add filler** — 每个元素必须 earn its place，没有就删
2. **Ask before adding** — 加任何 section 前先问用户
3. **Create a system first** — 先建立色彩/字体/间距系统，再开始写

---

## 第三阶段：设计方案

### 选设计风格（从 20 种风格中选）

| 场景 | 推荐风格 |
|------|---------|
| **B2B / 技术产品** | 01 Pentagram（瑞士网格+字体）、03 iA Writer（内容优先） |
| **消费品 / 品牌** | 11 Build（极简留白）、18 Kenya Hara（无印良品风格） |
| **数据 / 仪表盘** | 02 Stamen（地图学可视化）、04 Fathom（科学期刊） |
| **创意 / 艺术** | 09 Experimental Jetset（原色）、15 Ash Thorp（定制字体） |
| **科技 / 未来感** | 06 Active Theory（WebGL）、16 Territory Studio（深色科幻） |
| **品牌介绍** | 12 Sagmeister & Walsh（人格化）、20 Neo Shen（动态字体） |

### 色彩系统

```css
/* 用 oklch 而非 hsl，色差更精准 */
:root {
  --primary: oklch(0.65 0.18 25);       /* 暖色调 */
  --background: oklch(0.98 0.01 90);
  --ink: oklch(0.15 0.02 250);
  --accent: oklch(0.70 0.18 130);       /* 薄荷绿 */
  --muted: oklch(0.70 0.02 250);
}
```

### 字体配对

| 场景 | Display | Body |
|------|---------|------|
| **高端/品牌** | Instrument Serif | Geist Sans |
| **技术/代码** | JetBrains Mono | Geist Sans |
| **编辑/出版** | Cormorant Garamond | Inter Tight |
| **现代/简洁** | Bricolage Grotesque | Söhne |

---

## 第四阶段：实现

### 输出格式选择

```
默认 → HTML 演示（最灵活）

需要 PDF → export_deck_pdf.mjs
需要 PPTX → 走 4 个硬约束（见下方）
需要视频 → render-video.js
需要 GIF → convert-formats.sh
```

### HTML 文件结构

```
project/
  index.html          ← 主入口
  slides/             ←（如需幻灯片）
    slide-01.html
    slide-02.html
  assets/
    fonts/
    images/
  deck_index.html     ←（幻灯片合并入口）
```

### PPTX 的 4 个硬约束（如果用户要 PPTX）

1. 宽高固定 **960pt × 540pt**（16:9，匹配 1920×1080）
2. 文本只允许 `<p>` 和 `<h1>`-`<h6>`（禁止 div 嵌套）
3. 背景/border/shadow 只能用 div
4. 禁止 CSS gradient 和 web component

### 动画 5 段式（如果需要动画）

| 段 | 时长 | 描述 |
|---|------|------|
| **S1 预备** | ~15% | 从底部/侧边进入 |
| **S2 聚焦** | ~15% | 元素定位 |
| **S3 展开** | ~40% | 展示功能和细节 |
| **S4 高潮** | ~20% | 3D pop-out / 强调 |
| **S5 消失** | ~10% | Logo + 淡出 |

### Easing 选择

| 场景 | Easing |
|------|--------|
| 卡片进入 / Terminal fade | **`expoOut`**（`cubic-bezier(0.16, 1, 0.3, 1)`） |
| Toggle / 按钮按压 | `overshoot`（`cubic-bezier(0.34, 1.56, 0.64, 1)`） |
| 自然回弹 | `spring` |

---

## 第五阶段：验证

```bash
# Playwright 截图验证（1920×1080）
npx playwright screenshot file://$(pwd)/index.html shot.png --viewport-size=1920,1080
```

### 常见错误

1. **Chromium 不渲染 emoji** → 改用 Unicode 符号（✓ × ● ◆）
2. **字体未加载就读 getBoundingClientRect** → 先 `document.fonts.ready.then()`
3. **动画缺 cross-fade** → 状态切换要同时 fade out 和 fade in
4. **GIF 质量差** → 用 palette 优化，不要直接录制

---

## 快捷参考

### 字号规范

| 场景 | 最小 | Headline | 副标题 |
|------|------|----------|--------|
| **幻灯片 1920×1080** | 24px | 80-160px | 60-120px |
| **印刷 PDF** | 10pt | 18-36pt | 11-12pt |
| **Web** | 14px | — | — |

### 设计风格速查

```
信息架构派：01 Pentagram / 02 Stamen / 03 iA Writer / 04 Fathom
运动艺术派：05 Locomotive / 06 Active Theory / 07 Field.io / 08 Resn
平面设计派：09 Exp. Jetset / 10 Müeller-Brockmann / 11 Build / 12 S&W
字体/极简派：13 Z. Lieberman / 14 Raven Kwok / 15 Ash Thorp / 16 Territory
东方/有机派：17 Takram / 18 Kenya Hara / 19 Irma Boom / 20 Neo Shen
```

---

## 示例对话

**用户**："帮我做个产品介绍页"

**我的回应**：

```
好的，我来帮你做一个产品介绍页。先确认几个问题：

1. 有没有品牌 Logo / 产品图 / 色彩规范？（真实资产还是需要我找参考）
2. 是哪个公司的产品？（我可以去搜一下真实的产品风格）
3. 主要给谁看？（客户 / 投资人 / 内部）
4. 需要什么格式？（HTML 演示 / PDF / PPTX）
5. 有没有参考的页面？（可以是竞品或者你喜欢的设计）

如果都没有，我会：
- 从竞品官网搜真实产品图
- 用 Radix Colors 配色
- Instrument Serif + Geist Sans 字体
- 参考 11 Build 或 18 Kenya Hara 风格

确认后我开始设计。
```
