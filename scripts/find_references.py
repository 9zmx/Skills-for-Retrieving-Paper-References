#!/usr/bin/env python3
"""
find_references.py - 输入论文标题，自动搜索相关参考文献并附文献地址。

主数据源：OpenAlex（完全免费、无需 key、通常不限流），一条命令完成：
  1. 按标题匹配目标论文（可选年份限定）
  2. 拉取该论文的"参考文献"（它引用的文献 referenced_works）
  3. 拉取"相关文献"（同主题/共引推荐 related_works）

每篇文献统一返回：标题 / 作者 / 年份 / 期刊或会议 / DOI / 可访问链接 / 被引数。
可选：--s2 用 Semantic Scholar 交叉验证链接（S2 限流较紧，仅按需开启）。

依赖：仅 Python 标准库（urllib），无需第三方包。
用法：
  python find_references.py "论文标题"
  python find_references.py "论文标题" --year 2017          # 限定年份提高匹配精度
  python find_references.py "论文标题" --top 20              # 每种最多输出 20 条（默认 10）
  python find_references.py "论文标题" --fmt bibtex          # 输出 BibTeX 格式
  python find_references.py "论文标题" --fmt json            # 输出 JSON
  python find_references.py "论文标题" --s2                  # 用 Semantic Scholar 交叉验证链接
"""

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request

OPENALEX_BASE = "https://api.openalex.org"
S2_BASE = "https://api.semanticscholar.org/graph/v1"

MAILTO = "reference-finder@doubao.local"

# OpenAlex work 需要的字段
OA_SELECT = (
    "id,doi,title,display_name,publication_year,primary_location,authorships,"
    "cited_by_count,referenced_works,related_works,type,open_access"
)


def http_get_json(url, timeout=30, retries=3):
    """GET 请求并解析 JSON，带有限重试与退避。"""
    last_err = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": MAILTO})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code == 429:
                time.sleep(2 * (attempt + 1))
                continue
            if e.code in (404, 400):
                return None
            time.sleep(1)
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(1)
    if last_err is not None:
        print(f"[warn] 请求失败: {url} -> {last_err}", file=sys.stderr)
    return None


# ---------- OpenAlex ----------

def oa_works_url(params):
    """构造 OpenAlex works URL。filter/sort 值需保留逗号/冒号/竖线，只编码内部内容。"""
    parts = []
    for k, v in params.items():
        if k in ("filter", "sort"):
            # filter：多个条件逗号分隔，键值冒号连接，ids 用竖线；sort：字段:方向
            items = v if isinstance(v, list) else [v]
            enc = [urllib.parse.quote(str(i), safe=",:|") for i in items]
            parts.append(f"{k}={','.join(enc)}")
        else:
            parts.append(f"{k}={urllib.parse.quote(str(v))}")
    return f"{OPENALEX_BASE}/works?{'&'.join(parts)}&mailto={MAILTO}"


def _title_sim(query, cand_title):
    """简单标题相似度：忽略大小写/标点后，词集合 Jaccard + 长度接近度。"""
    import re
    q = set(re.findall(r"\w+", query.lower()))
    c = set(re.findall(r"\w+", (cand_title or "").lower()))
    if not q or not c:
        return 0.0
    inter = len(q & c)
    union = len(q | c)
    jac = inter / union if union else 0.0
    # 长度接近度惩罚过度偏离的标题
    len_ratio = min(len(q), len(c)) / max(len(q), len(c)) if c and q else 0.0
    return 0.8 * jac + 0.2 * len_ratio


def oa_search(title, year=None):
    """OpenAlex 按标题搜索，返回按 相似度×被引 排序的候选。"""
    def _build(yr):
        filters = [f"title.search:{title}"]
        if yr:
            filters.append(f"publication_year:{yr}")
        return {"filter": filters, "per_page": 10, "select": OA_SELECT}

    data = http_get_json(oa_works_url(_build(year)))
    results = (data or {}).get("results", [])
    if not results and year:
        # 标题+年份无结果时，回退为仅按标题，再精确筛选年份
        data2 = http_get_json(oa_works_url(_build(None)))
        results = [w for w in (data2 or {}).get("results", [])
                   if w.get("publication_year") == year]
    # 排序：优先相似度，其次被引数（取权威版本）
    results = sorted(
        results,
        key=lambda w: (_title_sim(title, w.get("title")), w.get("cited_by_count") or 0),
        reverse=True,
    )
    return results


def oa_topic_search(topic, limit=10, year=None):
    """按研究方向关键词搜索，按被引数降序返回该方向高被引论文。

    用于 --topic 模式：用户给方向词（如"健身 app"），自动找该方向权威文献。
    策略：title.search（标题命中方向词，排除全文误匹配）+ type:article（限期刊论文）。
    """
    filters = [f"title.search:{topic}", "type:article"]
    if year:
        filters.append(f"publication_year:{year}")
    params = {
        "filter": filters,
        "sort": "cited_by_count:desc",
        "per_page": limit,
        "select": OA_SELECT,
    }
    data = http_get_json(oa_works_url(params))
    results = (data or {}).get("results", [])
    if not results and year:
        # 标题+年份无结果时回退为不限年份
        filters.pop()
        params["filter"] = filters
        data2 = http_get_json(oa_works_url(params))
        results = (data2 or {}).get("results", [])
    return results


def oa_get(id):
    """OpenAlex 按 id（如 https://openalex.org/W...）取单篇。"""
    url = f"{OPENALEX_BASE}/works/{urllib.parse.quote(id, safe='')}?select={OA_SELECT}&mailto={MAILTO}"
    return http_get_json(url)


def oa_get_many(ids):
    """按 id 列表批量取（filter=ids.openalex 用 | 分隔）。"""
    ids = [i for i in ids if i]
    if not ids:
        return []
    params = {"filter": ["ids.openalex:" + "|".join(ids)], "per_page": 50, "select": OA_SELECT}
    data = http_get_json(oa_works_url(params))
    return (data or {}).get("results", [])


def oa_title(w):
    return w.get("title") or w.get("display_name") or "(无标题)"


def oa_authors(w):
    out = []
    for a in (w.get("authorships") or []):
        nm = ((a.get("author") or {}).get("display_name"))
        if nm:
            out.append(nm)
        if len(out) >= 8:
            break
    if len(w.get("authorships") or []) > 8:
        out.append("等")
    return ", ".join(out) or "未知"


def oa_venue(w):
    loc = w.get("primary_location") or {}
    src = loc.get("source") or {}
    return src.get("display_name") or "无期刊信息"


def oa_link(w):
    doi = w.get("doi")
    if doi:
        return doi  # doi 字段已是 https://doi.org/...
    loc = w.get("primary_location") or {}
    if loc.get("landing_page_url"):
        return loc["landing_page_url"]
    if loc.get("pdf_url"):
        return loc["pdf_url"]
    return None


def oa_to_paper(w):
    """把 OpenAlex work 规整成统一 dict。"""
    doi = w.get("doi")
    ext = {}
    if doi:
        ext["DOI"] = doi.replace("https://doi.org/", "")
    oa = w.get("open_access") or {}
    return {
        "title": oa_title(w),
        "authors": [(a.get("author") or {}).get("display_name") for a in (w.get("authorships") or [])
                    if (a.get("author") or {}).get("display_name")] or [],

        "year": w.get("publication_year"),
        "venue": oa_venue(w),
        "externalIds": ext,
        "citationCount": w.get("cited_by_count") or 0,
        "url": oa_link(w),
        "isOpenAccess": bool(oa.get("is_oa")),
        "_openalex_id": w.get("id"),
    }


# ---------- Semantic Scholar（可选交叉验证） ----------

S2_FIELDS = "title,authors,year,venue,externalIds,url,citationCount,isOpenAccess,openAccessPdf"


def s2_match(title):
    url = f"{S2_BASE}/paper/match?query={urllib.parse.quote(title)}&fields={S2_FIELDS}"
    data = http_get_json(url)
    return (data or {}).get("data", [])


# ---------- 输出 ----------

def doi_link(p):
    ext = p.get("externalIds") or {}
    if ext.get("DOI"):
        return "https://doi.org/" + ext["DOI"]
    if p.get("url"):
        return p["url"]
    return None


def fmt_paper(p, index):
    authors = p.get("authors") or []
    astr = ", ".join(authors[:8])
    if len(authors) > 8:
        astr += " 等"
    lines = [
        f"[{index}] {p.get('title') or '(无标题)'}",
        f"    作者: {astr or '未知'}  |  年份: {p.get('year') or '?'}",
        f"    期刊/会议: {p.get('venue') or '无期刊信息'}  |  被引: {p.get('citationCount') or 0}",
    ]
    link = doi_link(p)
    if link:
        lines.append(f"    链接: {link}")
    if p.get("isOpenAccess"):
        lines.append("    开放获取: 是")
    return "\n".join(lines)


def fmt_bibtex(p):
    authors = p.get("authors") or []
    last = authors[-1].split()[-1] if authors and authors[-1].split() else "unknown"
    bibkey = "".join(c for c in last if c.isalnum())
    if p.get("year"):
        bibkey += str(p["year"])
    ext = p.get("externalIds") or {}
    doi = ext.get("DOI", "")
    fields = []
    if p.get("title"):
        fields.append(f"  title = {{{p['title']}}},")
    if authors:
        fields.append(f"  author = {{{' and '.join(authors)}}},")
    if p.get("year"):
        fields.append(f"  year = {{{p['year']}}},")
    if p.get("venue"):
        fields.append(f"  journal = {{{p['venue']}}},")
    if doi:
        fields.append(f"  doi = {{{doi}}},")
    return f"@article{{{bibkey},\n" + "\n".join(fields) + "\n}"


def main():
    parser = argparse.ArgumentParser(description="输入论文标题，搜索相关参考文献和链接")
    parser.add_argument("title", nargs="?", help="论文标题（与 --topic 二选一）")
    parser.add_argument("--topic", default=None, help="研究方向关键词，自动找该方向高被引论文（与 title 二选一）")
    parser.add_argument("--year", type=int, default=None, help="限定出版年份")
    parser.add_argument("--doi", default=None, help="已知 DOI 时精确定位论文（绕过标题歧义）")
    parser.add_argument("--top", type=int, default=10, help="每种最多输出条数（默认 10）")
    parser.add_argument("--refs", type=int, default=8, help="topic 模式下每篇论文拉取参考文献条数（默认 8）")
    parser.add_argument("--fmt", choices=["text", "bibtex", "json"], default="text")
    parser.add_argument("--s2", action="store_true", help="用 Semantic Scholar 交叉验证链接")
    args = parser.parse_args()

    if not args.topic and not args.title:
        print("错误：需要提供论文标题（位置参数）或 --topic 方向关键词。", file=sys.stderr)
        sys.exit(1)

    if args.fmt == "json":
        if args.topic:
            output = {"topic": args.topic, "papers": []}
        else:
            output = {"query": args.title, "target": None, "references": [], "related": []}
    elif args.topic:
        print(f"正在按方向搜索: {args.topic}")
        if args.year:
            print(f"限定年份: {args.year}")

    # ==== --topic 模式：方向搜索 + 逐篇拉参考文献 ====
    if args.topic:
        papers = oa_topic_search(args.topic, limit=args.top, year=args.year)
        if not papers:
            print("未找到该方向的论文。", file=sys.stderr)
            sys.exit(1)
        for idx, w in enumerate(papers, 1):
            t = oa_to_paper(w)
            t_id = w.get("id")
            refs = oa_get_many((w.get("referenced_works") or [])[: args.refs]) if t_id else []
            refs = [oa_to_paper(x) for x in refs]
            if args.fmt == "json":
                output["papers"].append({"target": t, "references": refs})
            elif args.fmt == "text":
                print(f"\n========== 高被引论文 {idx}/{len(papers)} ==========")
                print(fmt_paper(t, idx))
                print(f"  -- 参考文献（{len(refs)} 条）--")
                if not refs:
                    print("   （无，或引用数据未收录）")
                for i, r in enumerate(refs, 1):
                    print(fmt_paper(r, i))
            else:
                print(f"% 高被引论文 {idx}")
                print(fmt_bibtex(t))
                for r in refs:
                    print(fmt_bibtex(r))
        if args.fmt == "json":
            print(json.dumps(output, ensure_ascii=False, indent=2))
        return

    # ==== 单篇标题模式 ====
    if args.fmt == "text":
        print(f"正在按标题搜索: {args.title}")
        if args.year:
            print(f"限定年份: {args.year}")

    # 1. 匹配目标论文
    if args.doi:
        # 已知 DOI 时精确匹配
        doi = args.doi.lower().replace("https://doi.org/", "").replace("http://doi.org/", "")
        data = http_get_json(f"{OPENALEX_BASE}/works?filter=doi:{urllib.parse.quote(doi)}&mailto={MAILTO}&select={OA_SELECT}")
        candidates = (data or {}).get("results", [])
        if not candidates:
            print(f"未找到 DOI={args.doi} 对应的论文。", file=sys.stderr)
            sys.exit(1)
    else:
        candidates = oa_search(args.title, args.year)
        if not candidates:
            print("未找到匹配论文。", file=sys.stderr)
            sys.exit(1)
    target = oa_to_paper(candidates[0])
    t_id = candidates[0].get("id")

    if args.fmt == "json":
        output["target"] = target
    elif args.fmt == "text":
        print("\n===== 匹配到的目标论文 =====")
        print(fmt_paper(target, "T"))
    else:
        print("% 目标论文")
        print(fmt_bibtex(target))
        print()

    # 2. 参考文献（引用文献）
    refs = oa_get_many((candidates[0].get("referenced_works") or [])[: args.top]) if t_id else []
    refs = [oa_to_paper(w) for w in refs]
    if args.fmt == "json":
        output["references"] = refs
    elif args.fmt == "text":
        print(f"\n===== 参考文献（{len(refs)} 条）=====")
        if not refs:
            print("（无，或该论文引用数据未收录）")
        for i, r in enumerate(refs, 1):
            print(fmt_paper(r, i))
            print()
    else:
        print("% 参考文献")
        for r in refs:
            print(fmt_bibtex(r))
            print()

    # 3. 相关文献（推荐）
    related = oa_get_many((candidates[0].get("related_works") or [])[: args.top]) if t_id else []
    related = [oa_to_paper(w) for w in related]
    if args.fmt == "json":
        output["related"] = related
    elif args.fmt == "text":
        print(f"===== 相关文献（{len(related)} 条）=====")
        if not related:
            print("（无）")
        for i, r in enumerate(related, 1):
            print(fmt_paper(r, i))
            print()
    else:
        print("% 相关文献")
        for r in related:
            print(fmt_bibtex(r))
            print()

    # 4. 可选 Semantic Scholar 交叉验证
    if args.s2:
        print("\n===== Semantic Scholar 交叉验证 =====")
        s2_hits = s2_match(args.title)
        for p in s2_hits[:3]:
            print(f"  - {p.get('title') or '(无标题)'}")
            link = doi_link(p)
            if link:
                print(f"    链接: {link}")
            time.sleep(1)

    if args.fmt == "json":
        print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
