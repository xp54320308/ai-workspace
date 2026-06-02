# AI Tells 完整清单（来自 taste-skill 生产环境实测）

> 这些特征是从真实 LLM 生成的 landing page 测试中提取的。每一个都是 AI 的签名。

## Hero & 页面顶部

| Tell | 说明 |
|---|---|
| 版本标签 | `V0.6`、`v2.0`、`BETA`、`INVITE-ONLY PREVIEW` 作为 eyebrow |
| 品牌子标签 | `Marrow · No. 01 · The 6-quart` 式微 meta 行 |
| 装饰文字条 | `BRAND. MOTION. SPATIAL.`、`TYPE / FORM / MOTION` 在 hero 底部 |
| 假产品预览 | 用 div 搭建的假 dashboard/terminal/task list |
| 假版本页脚 | `v0.6.2-rc.1`、`last sync 4s ago · main` |

## Section 编号 & 微标签

| Tell | 说明 |
|---|---|
| Section 编号 eyebrow | `00 / INDEX`、`001 · Capabilities`、`06 · how it works` |
| 图片分页 | `01 / 4` 式图片/bento 分页 |
| 滚动提示带编号 | `Scroll · 001 Capabilities` |
| 年份范围标签 | `Index of Work, 2018 - 2026` 作为 eyebrow |

## 分隔符 & 点

| Tell | 说明 |
|---|---|
| 中点滥用 | `·` 每行超过 1 个，或作为万能分隔符 |
| 装饰状态点 | 每个 nav/list/badge 前的彩色圆点（非真实状态） |

## Em-Dash & 排版花招

| Tell | 说明 |
|---|---|
| Em-dash（—）| **任何位置都禁止**，包括 en-dash（–）作分隔符 |
| 断行斜体标题 | `for thirty*years.*` 式拆分 |
| 竖排旋转文字 | `INDEX OF WORK, 2018 - 2026` 旋转 90° |
| 装饰十字线 | 仅为"感觉设计过"而画的垂直/水平线 |

## 营销文案

| Tell | 说明 |
|---|---|
| "Quietly in use at" | 假低调的社交证明 |
| "From the field" / "Field notes" | 表演性工匠标签 |
| "We respect the French ones" | 假谦虚行业引用 |
| 天气/城市条 | `LIS 14:23 · 18°C` 式装饰 |
| eyebrow 下的微 meta 句 | "Each of these is a feature we ship today..." |
| 通用步骤标签 | "Stage 1 / Stage 2" → 用动词名词（Install、Configure、Ship） |

## Pills、标签 & 版本印记

| Tell | 说明 |
|---|---|
| 图片上的 pills | `Brand · 02`、`Field notes - journal` 叠加在照片上 |
| 装饰性照片说明 | `Field study no. 12 · Ines Caetano`（无真实摄影师） |
| 营销页版本号 | `v1.4.2`、`Build 0048` |
| 实时库存计数器 | `Reservation 412 of 800`（非真实限量数据） |

## 列表 & 分隔线

| Tell | 说明 |
|---|---|
| 每行都有 border | 10 行规格表每行下面一条 hairline |
| 进度条/评分条 | 大填充背景轨道 + 部分填充，landing page 上显 dashboard |

## Locale & 滚动提示

| Tell | 说明 |
|---|---|
| 城市名/时间/天气条 | `Lisbon, working with founders` 在 hero |
| 滚动提示 | `Scroll`、`↓ scroll`、`Scroll to explore`、鼠标滚轮动画图标 |
| 装饰状态点 | nav 项前的彩色圆点（非真实语义状态） |

## 表现力 Tell

| Tell | 说明 |
|---|---|
| 无限循环微动画 | 不是每个卡片都需要 pulse/shimmer |
| GSAP for show | 动画存在但无法用一句话说明理由 |
| `window.addEventListener('scroll')` | 直接监听滚动（应用 Motion useScroll / ScrollTrigger）|
| 假精确数字 | `92%`、`4.1×`、`48k` 无数据来源 |

---

*来源：taste-skill Section 9，基于生产环境 LLM 输出测试*
