---
name: reference-finder
description: 输入论文标题，自动搜索匹配论文并返回其相关参考文献、相关推荐文献及每篇文献的标题/作者/年份/期刊/DOI/可访问链接，支持文本、BibTeX、JSON 三种输出，可选用 OpenAlex 交叉验证链接。当用户输入论文标题/题目，要求"找参考文献"、"搜相关文献"、"列引用"、"给我参考文献和链接"、"生成 BibTeX 引用"等时使用。也适用于给定研究方向关键词时顺藤摸瓜梳理相关文献。
---

# Reference Finder（参考文献搜索器）

## Overview

输入一篇论文的标题（可选年份/作者限定），通过 OpenAlex 开放学术数据库（免费、无需 key）自动完成三步：
1. 按标题匹配到目标论文；
2. 拉取该论文的**参考文献**（它引用的文献）；
3. 拉取**相关推荐**（同主题/共引的相似文献）。

每篇文献统一返回：标题 / 作者 / 年份 / 期刊或会议 / DOI / 可访问链接 / 被引数，并支持一键输出 BibTeX 引用条目。

## Quick Start

核心脚本：`scripts/find_references.py`（仅依赖 Python 标准库，无需 pip 安装第三方包）。
主数据源：OpenAlex（免费、无需 key、通常不限流）；Semantic Scholar 仅作可选交叉验证。

```bash
# 基础用法：输入论文标题
python scripts/find_references.py "Attention Is All You Need"

# 限定年份，提高匹配精度（防止同名论文匹配错）
python scripts/find_references.py "Attention Is All You Need" --year 2017

# 已知 DOI 时精确定位（最可靠，绕过标题歧义）
python scripts/find_references.py "BERT" --doi 10.18653/v1/N19-1423

# 每种结果最多输出 20 条（默认 10）
python scripts/find_references.py "BERT: Pre-training of Deep Bidirectional Transformers" --top 20

# 输出 BibTeX 格式（可直接粘进 .bib 文件 / Zotero）
python scripts/find_references.py "ResNet" --fmt bibtex

# 输出 JSON（供程序进一步处理）
python scripts/find_references.py "GPT-4 Technical Report" --fmt json

# 同时用 Semantic Scholar 交叉验证链接（S2 限流较紧，按需开启）
python scripts/find_references.py "Deep Residual Learning for Image Recognition" --s2

# 方向搜索模式：给研究方向关键词，自动找该方向高被引论文并逐篇拉参考文献
python scripts/find_references.py --topic "mobile fitness application"
python scripts/find_references.py --topic "mobile fitness application" --top 5 --refs 8
```

## 触发时机（When to Use）

- 用户给出论文标题，要求列出它的参考文献、相关文献、被引用文献；
- 用户要"给我这个题目的参考文献和文献链接/地址"；
- 用户要生成某篇文献的 BibTeX 引用条目，或要整理参考文献清单；
- 用户给研究方向关键词，要顺藤摸瓜找一批相关文献。
- 用户做项目/开题前"先摸清领域文献"——输入方向词（如"健身 app"、"目标检测"），快速定位该方向高被引权威论文。

## 两种使用模式

**A. 单篇模式（title）**：给精确论文标题，返回该论文的参考文献 + 相关推荐。
**B. 方向模式（--topic）**：给研究方向关键词，自动找出该方向按被引数排序的高被引论文，并逐篇拉取参考文献。适合开题、文献调研起步阶段。

注意：本 skill 负责**检索并输出文献与链接**。若用户要求的是整套"文献综述/调研报告"（归纳、对比、评估研究主题），应结合 `doubao-academic-researcher` 使用；本 skill 作为其中获取参考文献原始数据的一环。

## 工作流程（Workflow）

**单篇模式：**
1. **确认输入**：取出论文标题；若用户同时给了年份、作者、会议，作为可选参数传入。
2. **匹配目标论文**：脚本按标题搜索，`--year` 可显著降低同名误匹配。输出会先展示匹配到的目标论文，请确认标题与用户意图一致。
3. **拉取参考文献 + 相关推荐**：脚本自动完成，按 `--top` 控制条数（默认每类 10 条）。
4. **选择输出格式**：
   - 默认文本（人读友好，含链接）；
   - `--fmt bibtex`（给引用管理器 / 论文 .bib 用）；
   - `--fmt json`（给程序用）。
5. **可选用 Semantic Scholar 交叉验证**：`--s2` 用于二次核对链接，尤其当用户强调链接准确性或目标论文较冷门时推荐使用。
6. **向用户汇报**：直接呈现匹配到的目标论文 + 参考文献清单 + 相关推荐清单，每篇给出链接。

**方向模式（--topic）：**
1. 用户给方向关键词（如"健身 app"），脚本用 `title.search` + `type:article` 限定标题命中、排除全文误匹配。
2. 按被引数降序返回该方向高被引论文，条数由 `--top` 控制。
3. 对每篇高被引论文，拉取其参考文献，条数由 `--refs` 控制（默认 8）。
4. 向用户逐篇呈现高被引论文 + 其参考文献。

## 参数速查

| 参数 | 说明 | 默认 |
|------|------|------|
| `title`（位置参数） | 论文标题（与 `--topic` 二选一） | 必填之一 |
| `--topic` | 研究方向关键词，找该方向高被引论文 | 无 |
| `--year` | 限定出版年份，减少同名误匹配 | 无 |
| `--doi` | 已知 DOI 时精确定位论文（最可靠） | 无 |
| `--top` | 单篇模式每类条数 / 方向模式论文数 | 10 |
| `--refs` | 方向模式下每篇论文拉取参考文献条数 | 8 |
| `--fmt` | `text` / `bibtex` / `json` | text |
| `--s2` | 用 Semantic Scholar 交叉验证链接 | 关 |

## 注意事项

- **匹配策略**：脚本按「标题相似度 × 被引数」排序选取目标论文，优先权威版本；`--year` 可进一步缩小范围。若匹配结果明显不对，优先补 `--doi` 精确定位。
- **数据源限制**：主源 OpenAlex 对极个别知名论文的年份索引可能有缺陷（如 "Attention Is All You Need" 在 OpenAlex 中缺 2017 原版），遇到这种情况建议用 `--doi` 或 `--s2` 校正。
- **限流**：Semantic Scholar 免费额度约 1 请求/秒且可能按环境硬限流；OpenAlex 一般宽松。脚本均已带 429 退避重试。
- **链接优先级**：DOI → arXiv → 开放获取 PDF → 论文主页。部分老文献可能无在线链接，会省略"链接"行，属正常。
- 脚本仅用标准库，无第三方依赖，跨平台（Windows / macOS / Linux）均可直接运行。
