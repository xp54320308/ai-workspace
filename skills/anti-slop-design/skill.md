---
name: anti-slop-design
description: 前端设计反 AI 味技能。提炼自 taste-skill（26.7k stars），检测并消除 AI 生成内容的典型特征，输出有品味的设计。
version: 1.0
source: https://github.com/Leonxlnx/taste-skill
---

# Anti-Slop Design Skill

> **核心理念**：AI 生成的前端有可识别的"AI 味"——紫色渐变、Inter 字体、三列卡片、em-dash 满天飞。这个 skill 系统性地消除这些特征。

**适用范围**：Landing page、Portfolio、营销页、品牌页。不适用于 Dashboard、数据表格、复杂产品 UI。

---

## 0. 先读懂 brief（不要猜）

动手前先输出一行 **Design Read**：

> "Reading this as: [页面类型] for [目标用户], with a [风格语言], leaning toward [技术方案]。"

示例：
- "Reading this as: B2B SaaS landing for technical buyers, with a Linear-style minimalist language, leaning toward Tailwind + Geist + restrained motion."
- "Reading this as: solo designer portfolio for hiring managers, with an editorial language, leaning toward native CSS + scroll-driven animation."

**如果 brief 模糊**：只问一个问题，不要猜。能推断就直接声明 Design Read 然后开干。

---

## 1. AI 默认行为清单（必须主动回避）

### 🎨 视觉默认
| AI 默认行为 | 替代方案 |
|---|---|
| 紫色渐变 / 蓝色发光 | 中性底色 + 单一高对比强调色（Emerald、Electric Blue、Deep Rose） |
| 居中 Hero + 深色网格背景 | 非对称拆分、左对齐、滚动固定等变体 |
| 三列等宽功能卡片 | 2 列交错、非对称网格、横向滚动 |
| 到处加玻璃拟态 | 只在 premium consumer / Apple 风格时使用 |
| 无限循环微动画 | 动画必须有理由（层级/叙事/反馈/状态转换） |
| Inter + slate-900 | Geist、Outfit、Cabinet Grotesk、Satoshi 先选 |

### 🔤 字体默认
| AI 默认行为 | 规则 |
|---|---|
| 默认用 Inter | 除非用户明确要"neutral/Linear-style"，否则换别的 |
| 创意 brief → 衬线体 | **禁止**。衬线只用于：品牌明确指定、或 genuinely editorial/luxury/heritage |
| 随机混用字体族强调 | 同一字体的 italic/bold 才是正确做法 |
| Fraunces、Instrument Serif | **作为默认禁止**（LLM 最爱的两个衬线体）|

### 🎨 配色默认
| AI 默认行为 | 规则 |
|---|---|
| 奢侈品 brief → 米色+黄铜+深棕 | **禁止**。冷灰银、森林绿、钴蓝+奶油、纯灰+单色弹出 |
| 每个项目用同样的暖色系 | 必须轮换，不能连续两个项目用同色系 |
| 全页多个强调色 | 最多 1 个强调色，饱和度 < 80% |
| 不同 section 用不同色调 | 选定一个 accent，全页锁定 |

### 📐 布局默认
| AI 默认行为 | 规则 |
|---|---|
| 每个 section 都有 eyebrow（小标题） | **每 3 个 section 最多 1 个 eyebrow** |
| "左大标题 + 右小段落" split header | 禁止。改为垂直堆叠 |
| 连续 3+ 个 image+text 交错布局 | 最多 2 个连续，第 3 个必须换布局 |
| 8 个 section 用同一种布局 | 至少 4 种不同布局族 |

---

## 2. AI Tells 清单（生产环境实测特征）

### 🚫 视觉特征（Visual Tells）
- ~~霓虹/外发光~~ → 用内边框或微色调阴影
- ~~纯黑 #000000~~ → off-black、zinc-950、charcoal
- ~~过度饱和的强调色~~ → 去饱和融入中性色
- ~~大标题用渐变文字~~ → 限制使用
- ~~自定义鼠标光标~~ → 禁止（过时、无障碍差）

### 🚫 内容特征（Content Tells）
- ~~"John Doe"、"Sarah Chan"~~ → 用有创意的、符合 locale 的真实名字
- ~~99.9%、50%、1234567~~ → 用有机数据（47.2%、+1 (312) 847-1928）
- ~~"Acme"、"Nexus"、"SmartFlow"~~ → 创造有质感的品牌名
- ~~"Elevate"、"Seamless"、"Unleash"~~ → 具体动词，不说废话

### 🚫 布局特征（Layout Tells）
- ~~三列等宽功能卡片~~ → 非对称布局
- ~~每行都有 border-b 的规格表~~ → 卡片/分组/横向滚动
- ~~"Works with GitHub, GitLab..." 小标签~~ → 移到独立 section
- ~~Hero 里的信任 logo 墙~~ → 放到 hero 下方独立 section

### 🚫 营销文案特征（Copy Tells）
- ~~"Quietly in use at"~~ → "Trusted by" / "Used at"
- ~~"From the field" / "Field notes"~~ → 用功能标签（"Testimonials"、"Latest writing"）
- ~~"We respect the French ones"~~ → 假谦虚行业引用，禁止
- ~~天气/城市条（"LIS 14:23 · 18°C"）~~ → 除非 brief 明确关于地点/时区

---

## 3. Em-Dash 全面禁令 ⚠️ 最重要

**Em-dash（—）完全禁止。** 这是 LLM 的 #1 视觉签名。

| 位置 | 规则 |
|---|---|
| 标题 | 用句号或逗号 |
| 标签/按钮/图片说明 | 用换行、列、或 hairline |
| 正文 | 重组句子：两个句子用句号，或逗号，或括号，或冒号 |
| 引用归属 | 用普通连字符加空格（` - `）|
| 日期范围 | 用连字符（2018-2026）|

**唯一允许的破折字符**：普通连字符 `-`（复合词、范围、标记分隔）

> 如果输出包含任何可见的 `—` 或 `–`，必须重写。

---

## 4. Hero 纪律

- **标题最多 2 行**，副标题最多 20 词且最多 3-4 行
- **CTA 必须无需滚动可见**
- **顶部 padding 最大 pt-24**（≈6rem），不要让内容飘在视口中间
- **Hero 最多 4 个文本元素**：eyebrow（可选）、标题、副标题、CTA
- **禁止在 Hero 里放**：小标签、信任条、定价预览、功能列表、社交证明头像行
- **"Used by" logo 墙放 hero 下方**，不在 hero 里
- **Hero 需要真实视觉**：纯文字+渐变 blob 不是 hero，是占位符

---

## 5. CTA 纪律

- **按钮文字必须一行**：桌面端 2 行 wrap = 失败
- **主 CTA 标签最多 3 个词**，理想 1-2 个
- **同一页面同一 intent 只能有一个 CTA**："Get in touch" + "Let's talk" + "Contact us" = 失败
- **按钮对比度 WCAG AA**：文字必须可读，禁止白底白字

---

## 6. 三旋钮系统（可选，用于量化设计方向）

| 旋钮 | 范围 | 含义 |
|---|---|---|
| `DESIGN_VARIANCE` | 1-10 | 1=完美对称，10=艺术混沌 |
| `MOTION_INTENSITY` | 1-10 | 1=静态，10=电影级/物理动画 |
| `VISUAL_DENSITY` | 1-10 | 1=美术馆/留白，10=驾驶舱/密集 |

**默认基线**：`8 / 6 / 4`

| Brief 关键词 | VARIANCE | MOTION | DENSITY |
|---|---|---|---|
| minimalist / clean / Linear-style | 5-6 | 3-4 | 2-3 |
| premium consumer / Apple-y | 7-8 | 5-7 | 3-4 |
| playful / Awwwards / experimental | 9-10 | 8-10 | 3-4 |
| trust-first / public-sector | 3-4 | 2-3 | 4-5 |

---

## 7. 技术默认值

- **框架**：React / Next.js，默认 Server Components
- **样式**：Tailwind v4
- **动画**：Motion（原 Framer Motion），从 `motion/react` 导入
- **图标**：Phosphor > HugeIcons > Radix > Tabler。禁止手绘 SVG。
- **字体**：用 `next/font` 或 `@font-face` 自托管，禁止 Google Fonts CDN
- **Emoji**：默认禁止，用户明确要求时才用

---

## 8. 暗色模式

- 默认同时设计明暗两套
- 不用纯黑 `#000000` 和纯白 `#ffffff`，用 off-black/off-white
- 整页一个主题，section 之间不翻转
- 尊重 `prefers-color-scheme`

---

## 9. Pre-Flight Checklist（交付前必查）

### 基础检查
- [ ] Design Read 已输出
- [ ] 旋钮值已设定且有理由
- [ ] 设计系统已选定（如适用）

### Em-Dash 扫描
- [ ] 全页零 em-dash（标题、标签、正文、引用、按钮、alt text）

### 一致性锁定
- [ ] 全页一个主题（明/暗）
- [ ] 全页一个强调色
- [ ] 全页一个圆角系统

### Hero 检查
- [ ] 标题 ≤ 2 行，副标题 ≤ 20 词
- [ ] CTA 无需滚动可见
- [ ] 顶部 padding ≤ pt-24
- [ ] 最多 4 个文本元素
- [ ] 有真实视觉（非纯文字+渐变）

### 布局检查
- [ ] Eyebrow 数量 ≤ ceil(section数 / 3)
- [ ] 无连续 3+ 个 image+text 交错
- [ ] 8 个 section 至少 4 种布局族
- [ ] 无"左标题+右段落" split header

### CTA 检查
- [ ] 按钮文字不 wrap
- [ ] 同一 intent 只有一个 CTA
- [ ] 按钮对比度 WCAG AA

### 内容检查
- [ ] 无 AI 品牌名（Acme、Nexus）
- [ ] 无废话动词（Elevate、Seamless）
- [ ] 无假精确数字
- [ ] 每个可见字符串已复查

### 图片检查
- [ ] 用真实图片/生成图片，无 div 假截图
- [ ] Logo 墙用真实 SVG，非纯文字

---

## 10. 快速诊断口诀

遇到前端输出时，按这个顺序检查：

1. **有 em-dash 吗？** → 删
2. **用了 Inter 吗？** → 换
3. **紫色渐变？** → 换强调色
4. **三列等宽卡片？** → 换布局
5. **每个 section 都有 eyebrow？** → 砍到 1/3
6. **"Acme" / "Elevate"？** → 换具体词
7. **Hero 超出一屏？** → 缩

> 这 7 条覆盖了 80% 的 AI 味。剩下的看完整 checklist。

---

*Source: [taste-skill](https://github.com/Leonxlnx/taste-skill) by Leonxlnx (26.7k stars) · MIT License · 提炼适配 OpenClaw*
