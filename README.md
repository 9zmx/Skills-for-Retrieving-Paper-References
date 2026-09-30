# Skills-for-Retrieving-Paper-References

> 输入论文标题或研究方向关键词，自动检索相关参考文献与文献链接，一键导出 BibTeX / JSON。
> 面向论文写作、文献调研与开题起步的轻量开源 skill。

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)]()

---

## 📌 项目简介

**reference-finder** 是一个基于 [OpenAlex](https://openalex.org/) 开放学术数据库的参考文献检索工具。只需给它一篇论文的标题（或一个研究方向关键词），它就能自动帮你：

- ✅ 按标题匹配到目标论文
- ✅ 拉取该论文的**参考文献**（它引用的文献）
- ✅ 拉取**相关推荐文献**（同主题/共引的相似论文）
- ✅ 每篇文献统一返回：标题 / 作者 / 年份 / 期刊或会议 / **DOI / 可访问链接** / 被引数
- ✅ 一键导出 **BibTeX**（直接粘进 `.bib` 文件或 Zotero）或 **JSON**

**典型应用场景：**
- 写论文时需要某篇核心论文的完整参考文献清单
- 开题 / 文献调研起步时，快速摸清一个研究方向的高被引权威论文
- 给引文管理器批量生成 BibTeX 引用条目

---

## ✨ 核心特性

| 特性 | 说明 |
|------|------|
| 🎯 **双模式** | ① 单篇模式（按精确标题搜）② 方向模式（按方向关键词搜高被引论文） |
| 🌐 **免费数据源** | 基于 OpenAlex，完全免费、无需 API Key、通常不限流 |
| 🧩 **零依赖** | 仅用 Python 标准库（urllib），无需 pip 安装任何第三方包 |
| 🔗 **真实链接** | 每条文献都带 DOI / arXiv / 开放获取 PDF 等可访问链接 |
| 📦 **多格式输出** | 文本（人读友好）/ BibTeX（引用）/ JSON（程序处理） |
| 🔍 **精准匹配** | 标题相似度 × 被引数双重排序，优先锁定权威版本 |
| 🖥 **跨平台** | Windows / macOS / Linux 均可直接运行 |

---

## 🚀 快速开始

### 环境要求
- Python 3.8 及以上（无需任何第三方库）

### 克隆
```bash
git clone git@github.com:9zmx/Skills-for-Retrieving-Paper-References.git
cd Skills-for-Retrieving-Paper-References
```

### 基本用法

```bash
# ① 单篇模式：输入论文标题
python scripts/find_references.py "Deep Residual Learning for Image Recognition"

# ② 限定年份，避免同名论文匹配错
python scripts/find_references.py "Attention Is All You Need" --year 2017

# ③ 已知 DOI 时精确定位（最可靠）
python scripts/find_references.py "BERT" --doi 10.18653/v1/N19-1423

# ④ 方向模式：给研究方向关键词，找该方向高被引论文并逐篇拉参考文献
python scripts/find_references.py --topic "mobile fitness application"

# ⑤ 输出 BibTeX（可直接粘进 .bib / Zotero）
python scripts/find_references.py "ResNet" --fmt bibtex

# ⑥ 输出 JSON（供程序进一步处理）
python scripts/find_references.py "GPT-4 Technical Report" --fmt json
```

---

## 📖 使用指南

### 模式一：单篇模式（按标题搜）

给一篇论文的精确标题，返回该论文的**参考文献** + **相关推荐**。

```bash
python scripts/find_references.py "Learning From Older Adults to Promote Independent Physical Activity Using Mobile Health" --year 2021 --top 6
```

**输出示例：**
```
正在按标题搜索: Learning From Older Adults to Promote Independent Physical Activity Using Mobile Health
限定年份: 2021

===== 匹配到的目标论文 =====
[T] Learning From Older Adults to Promote Independent Physical Activity Using Mobile Health (mHealth)
    作者: Camille Nebeker, Zvinka Z. Zlatar  |  年份: 2021
    期刊/会议: Frontiers in Public Health  |  被引: 26
    链接: https://doi.org/10.3389/fpubh.2021.703910
    开放获取: 是

===== 参考文献（6 条）=====
[1] Quantification of Five Neuropsychological Approaches to Defining Mild Cognitive Impairment
    作者: Amy J. Jak, Mark William Bondi, ...  |  年份: 2009
    期刊/会议: American Journal of Geriatric Psychiatry  |  被引: 841
    链接: https://doi.org/10.1097/jgp.0b013e31819431d5
...
```

### 模式二：方向模式（按研究方向关键词搜）

给一个研究方向关键词（如"健身 app"、"目标检测"、"mHealth"），自动找出该方向**按被引数排序的高被引论文**，并逐篇拉取它们的参考文献。适合开题、文献调研起步。

```bash
python scripts/find_references.py --topic "mobile fitness application" --top 5 --refs 8
```

**输出示例：**
```
========== 高被引论文 1/5 ==========
[1] Gamification Use and Design in Popular Health and Fitness Mobile Applications
    作者: Victor R. Cotton, Mitesh S. Patel  |  年份: 2018
    期刊/会议: American Journal of Health Promotion  |  被引: 114
    链接: https://doi.org/10.1177/0890117118790394
  -- 参考文献（3 条）--
[1] Just a Fad? Gamification in Health and Fitness Apps
    作者: Cameron Lister, ...  |  年份: 2014
    期刊/会议: JMIR Serious Games  |  被引: 511
    链接: https://doi.org/10.2196/games.3413
...
```

> **提示**：方向模式使用 `title.search` + `type:article` 过滤，确保方向词命中标题、且只保留期刊论文，避免全文误匹配到不相关的高频论文。

---

## ⚙️ 参数说明

| 参数 | 说明 | 默认 |
|------|------|------|
| `title`（位置参数） | 论文标题（与 `--topic` 二选一） | 必填之一 |
| `--topic` | 研究方向关键词，找该方向高被引论文 | 无 |
| `--year` | 限定出版年份，减少同名误匹配 | 无 |
| `--doi` | 已知 DOI 时精确定位论文（最可靠） | 无 |
| `--top` | 单篇模式每类条数 / 方向模式论文数 | 10 |
| `--refs` | 方向模式下每篇论文拉取参考文献条数 | 8 |
| `--fmt` | 输出格式：`text` / `bibtex` / `json` | text |
| `--s2` | 用 Semantic Scholar 交叉验证链接 | 关 |

---

## 🔧 作为 AI Skill 使用

本项目同时是一个标准 **Agent Skill**（`SKILL.md` + `scripts/` 结构），兼容 Claude Agent Skills 等遵循 `SKILL.md` 规范的 AI 工具链。

**安装到 Claude：**
```bash
# 将整个 reference-finder 目录放入 skills 目录
cp -r reference-finder ~/.claude/skills/
```

AI 助手读取 `SKILL.md` 的 `description` 即可识别触发场景（"找参考文献"、"搜相关文献"、"列引用"、"生成 BibTeX"等）。

---

## 📂 目录结构

```
Skills-for-Retrieving-Paper-References/
├── SKILL.md                       # skill 使用说明（供 AI 助手读取）
└── scripts/
    └── find_references.py         # 核心执行脚本（纯 Python 标准库）
```

---

## ⚠️ 注意事项

- **数据源**：主源为 OpenAlex（免费、无需 Key、通常不限流）；Semantic Scholar 仅作可选交叉验证（`--s2`，限流较紧）。
- **数据缺陷**：OpenAlex 对极个别知名论文的年份索引可能有缺陷（如 "Attention Is All You Need" 缺 2017 原版），遇到匹配不对建议用 `--doi` 精确定位。
- **链接优先级**：DOI → arXiv → 开放获取 PDF → 论文主页。个别老文献可能无在线链接，属正常。
- **限流**：脚本已内置 429 退避重试，批量查询时按节奏执行即可。

---

## 🤝 贡献

欢迎通过 **Issue** 提交 bug 或功能建议，或通过 **Pull Request** 贡献代码。贡献前请确保脚本改动经过真实数据测试。

---

## 📄 许可

本项目基于 **MIT License** 开源，可自由使用、修改与商用。
