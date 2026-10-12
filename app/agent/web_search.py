"""联网搜索 — 零依赖实现（不需要任何 API Key）

策略（逐级降级，全部基于标准库 urllib）：
  1. 搜狗  ← 中文结果最准，实测可达
  2. 360搜索 ← 备用
  3. Bing 中文站 ← 兜底
  4. 第三方爬虫（若已安装）← Crawl4AI / Firecrawl 增强
最后交给 LLM 汇总成答案，并缓存进知识库。
"""

import re
import html
import urllib.request
import urllib.parse
from typing import List, Dict, Optional

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "identity",
}


def _fetch(url: str, timeout: int = 15) -> Optional[str]:
    """抓取网页 HTML 并自动识别编码"""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            ctype = resp.headers.get("Content-Type", "")
            m = re.search(r"charset=([\w-]+)", ctype, re.I)
            enc = m.group(1) if m else "utf-8"
            try:
                return raw.decode(enc, "ignore")
            except LookupError:
                return raw.decode("utf-8", "ignore")
    except Exception:
        return None


def _clean(s: str) -> str:
    """去标签 + 反转义 + 压缩空白"""
    s = re.sub(r"<!--.*?-->", "", s or "", flags=re.S)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def _unwrap_sogou(link: str) -> str:
    """搜狗跳转链接尽量还原真实 URL（失败则保留原链接）"""
    if link.startswith("//"):
        link = "https:" + link
    if link.startswith("/"):
        link = "https://www.sogou.com" + link
    return link


# ────────────────────────────────────────────
# 引擎 1：搜狗（首选，中文最准）
# ────────────────────────────────────────────

def _search_sogou(query: str, limit: int = 8) -> List[Dict]:
    url = "https://www.sogou.com/web?query=" + urllib.parse.quote(query)
    page = _fetch(url)
    if not page:
        return []

    results = []
    # 结果块：<div class="vrwrap"> ... <h3 class="vr-title"><a href="...">标题</a></h3>
    blocks = re.split(r'<div class="vrwrap"', page)[1:]
    for b in blocks:
        m = re.search(r'<h3[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', b, re.S)
        if not m:
            continue
        link, title = _unwrap_sogou(m.group(1)), _clean(m.group(2))
        if not title or len(title) < 4:
            continue
        # 摘要：<div class="text-layout"> 或 <p class="str_info"> 之类
        sm = re.search(r'class="(?:text-layout|str_info|fz-mid|space-txt)[^"]*"[^>]*>(.*?)</div>', b, re.S)
        if not sm:
            sm = re.search(r'<p[^>]*>(.*?)</p>', b, re.S)
        snippet = _clean(sm.group(1))[:400] if sm else ""
        results.append({"title": title, "url": link, "snippet": snippet})
        if len(results) >= limit:
            break

    if not results:  # 结构变化时的宽松兜底
        for link, title in re.findall(r'<h3[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', page, re.S):
            t = _clean(title)
            if t and len(t) > 4:
                results.append({"title": t, "url": _unwrap_sogou(link), "snippet": ""})
                if len(results) >= limit:
                    break
    return results


# ────────────────────────────────────────────
# 引擎 2：360 搜索
# ────────────────────────────────────────────

def _search_360(query: str, limit: int = 8) -> List[Dict]:
    url = "https://www.so.com/s?q=" + urllib.parse.quote(query)
    page = _fetch(url)
    if not page:
        return []

    results = []
    for link, title in re.findall(r'<h3[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', page, re.S):
        t = _clean(title)
        if not t or len(t) < 4:
            continue
        if link.startswith("//"):
            link = "https:" + link
        results.append({"title": t, "url": link, "snippet": ""})
        if len(results) >= limit:
            break
    return results


# ────────────────────────────────────────────
# 引擎 3：Bing 中文
# ────────────────────────────────────────────

def _search_bing(query: str, limit: int = 8) -> List[Dict]:
    url = ("https://cn.bing.com/search?q=" + urllib.parse.quote(query)
           + f"&count={limit}&setlang=zh-CN&cc=CN")
    page = _fetch(url)
    if not page:
        return []

    results = []
    blocks = re.findall(r'<li class="b_algo".*?(?=<li class="b_algo"|</ol>)', page, re.S)
    for b in blocks:
        m = re.search(r'<h2[^>]*>\s*<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>', b, re.S)
        if not m:
            continue
        title = _clean(m.group(2))
        if not title or "bing.com" in m.group(1):
            continue
        p = re.search(r'<p[^>]*>(.*?)</p>', b, re.S)
        snippet = _clean(p.group(1))[:400] if p else ""
        results.append({"title": title, "url": m.group(1), "snippet": snippet})
        if len(results) >= limit:
            break
    return results


# ────────────────────────────────────────────
# 引擎 4/5：第三方爬虫（可选增强）
# ────────────────────────────────────────────

def _search_crawl4ai(query: str, limit: int = 5) -> List[Dict]:
    try:
        import asyncio
        from crawl4ai import AsyncWebCrawler

        async def run():
            async with AsyncWebCrawler() as crawler:
                url = "https://cn.bing.com/search?q=" + urllib.parse.quote(query)
                r = await crawler.arun(url=url)
                return r.markdown if r else ""

        loop = asyncio.new_event_loop()
        md = loop.run_until_complete(run())
        loop.close()
        out = []
        if md:
            for t, u in re.findall(r'\[([^\]\n]{8,90})\]\((https?://[^)\s]+)\)', md):
                if "bing.com" in u or "microsoft" in u:
                    continue
                out.append({"title": t.strip(), "url": u, "snippet": ""})
                if len(out) >= limit:
                    break
        return out
    except Exception:
        return []


def _search_firecrawl(query: str, limit: int = 5) -> List[Dict]:
    try:
        from firecrawl import FirecrawlApp
        app = FirecrawlApp()
        r = app.search(query, limit=limit)
        data = r.get("data", r) if isinstance(r, dict) else []
        return [
            {"title": x.get("title", ""), "url": x.get("url", ""),
             "snippet": x.get("description", x.get("content", ""))[:400]}
            for x in data[:limit]
        ]
    except Exception:
        return []


# ────────────────────────────────────────────
# 统一入口
# ────────────────────────────────────────────

_ENGINES = (_search_sogou, _search_360, _search_bing, _search_crawl4ai, _search_firecrawl)


def web_search(query: str, limit: int = 8, region: str = "四川") -> List[Dict]:
    """
    联网搜索：多引擎自动降级，零依赖可用
    :param query: 查询词
    :param limit: 返回条数
    :param region: 区域限定（默认四川），传 "" 取消
    """
    q = f"{query} {region}".strip() if region else query

    for engine in _ENGINES:
        try:
            items = engine(q, limit)
        except Exception:
            items = []
        if items:
            return items
    return []


def web_search_full(query: str, limit: int = 6, region: str = "四川") -> List[Dict]:
    """多引擎合并去重（结果更全，略慢）"""
    q = f"{query} {region}".strip() if region else query

    seen, merged = set(), []
    for engine in _ENGINES[:3]:  # 只合并前三个 HTML 引擎
        try:
            items = engine(q, limit)
        except Exception:
            items = []
        for it in items:
            key = it["url"].split("?")[0].rstrip("/")
            if key in seen:
                continue
            seen.add(key)
            merged.append(it)
            if len(merged) >= limit:
                return merged
    return merged


def search_company_credit(company_name: str, region: str = "四川") -> dict:
    """查询企业资信"""
    q = f"{company_name} 资质等级 信用评价 中标业绩"
    return {"company": company_name, "region": region,
            "results": web_search(q, region=region), "source": "web_search"}


def search_material_price(material_name: str, region: str = "四川") -> dict:
    """查询材料信息价"""
    q = f"{material_name} 信息价 造价 价格"
    return {"material": material_name, "region": region,
            "results": web_search(q, region=region), "source": "web_search"}


def search_standard(standard_keyword: str, region: str = "四川") -> dict:
    """查询规范标准"""
    q = f"{standard_keyword} 国家标准 规范 全文"
    return {"keyword": standard_keyword, "region": region,
            "results": web_search(q, region=region), "source": "web_search"}


if __name__ == "__main__":
    for k in ("C30混凝土 价格", "成都 混凝土 信息价", "GB50300"):
        print(f"\n【{k}】")
        for i, r in enumerate(web_search(k, limit=3), 1):
            print(f"  {i}. {r['title'][:60]}")
            print(f"     {r['url'][:85]}")
            if r["snippet"]:
                print(f"     {r['snippet'][:100]}")
