"""Web 爬虫集成 — 5 个内置爬虫工具的统一接口"""

import json
from typing import List, Dict, Optional


class WebScraperEngine:
    """
    Web 爬虫统一引擎
    内置 5 个爬虫工具，自动选择最佳可用工具
    """

    def __init__(self):
        self.available = self._check_available()

    def _check_available(self) -> Dict[str, bool]:
        """检查各爬虫是否可用"""
        result = {}
        try:
            import firecrawl
            result["firecrawl"] = True
        except ImportError:
            result["firecrawl"] = False

        try:
            import crawl4ai
            result["crawl4ai"] = True
        except ImportError:
            result["crawl4ai"] = False

        try:
            import browser_use
            result["browser_use"] = True
        except ImportError:
            result["browser_use"] = False

        try:
            import xcrawl
            result["xcrawl"] = True
        except ImportError:
            result["xcrawl"] = False

        try:
            import agent_reach
            result["agent_reach"] = True
        except ImportError:
            result["agent_reach"] = False

        return result

    def get_status(self) -> Dict:
        """获取各爬虫状态"""
        return {
            "available": self.available,
            "count": sum(1 for v in self.available.values() if v),
            "total": len(self.available),
        }

    def search(self, query: str, region: str = "四川", max_results: int = 5) -> List[Dict]:
        """
        通用搜索，自动选择最佳可用爬虫
        优先四川区域
        """
        search_query = f"{query} {region}" if region else query

        if self.available.get("firecrawl"):
            return self._search_firecrawl(search_query, max_results)
        elif self.available.get("crawl4ai"):
            return self._search_crawl4ai(search_query, max_results)
        elif self.available.get("browser_use"):
            return self._search_browser_use(search_query, max_results)
        elif self.available.get("xcrawl"):
            return self._search_xcrawl(search_query, max_results)

        return []

    def scrape_url(self, url: str) -> Optional[str]:
        """抓取单个 URL 内容"""
        if self.available.get("firecrawl"):
            return self._scrape_firecrawl(url)
        elif self.available.get("crawl4ai"):
            return self._scrape_crawl4ai(url)
        elif self.available.get("browser_use"):
            return self._scrape_browser_use(url)
        return None

    def search_company_credit(self, company_name: str, region: str = "四川") -> List[Dict]:
        """查询企业资信"""
        query = f"{company_name} 资质 信用 {region}"
        return self.search(query, region=region)

    def search_material_price(self, material: str, region: str = "四川") -> List[Dict]:
        """查询材料价格"""
        query = f"{material} 信息价 {region}"
        return self.search(query, region=region)

    def search_standard(self, keyword: str, region: str = "四川") -> List[Dict]:
        """查询规范标准"""
        query = f"{keyword} 标准 规范 {region}"
        return self.search(query, region=region)

    # ── Firecrawl ──

    def _search_firecrawl(self, query: str, max_results: int) -> List[Dict]:
        try:
            from firecrawl import FirecrawlApp
            app = FirecrawlApp()
            result = app.search(query, limit=max_results)
            if isinstance(result, dict) and "data" in result:
                return [
                    {
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "snippet": r.get("description", ""),
                    }
                    for r in result["data"][:max_results]
                ]
        except Exception as e:
            return [{"title": f"Firecrawl 错误: {e}", "url": "", "snippet": ""}]
        return []

    def _scrape_firecrawl(self, url: str) -> Optional[str]:
        try:
            from firecrawl import FirecrawlApp
            app = FirecrawlApp()
            result = app.scrape_url(url)
            if isinstance(result, dict):
                return result.get("markdown", result.get("text", ""))
        except Exception:
            pass
        return None

    # ── Crawl4AI ──

    def _search_crawl4ai(self, query: str, max_results: int) -> List[Dict]:
        try:
            import asyncio
            from crawl4ai import AsyncWebCrawler

            async def crawl():
                async with AsyncWebCrawler() as crawler:
                    search_url = f"https://www.baidu.com/s?wd={query}"
                    result = await crawler.arun(url=search_url)
                    if result and result.markdown:
                        return [{
                            "title": f"搜索: {query}",
                            "url": search_url,
                            "snippet": result.markdown[:500],
                        }]
                    return []

            loop = asyncio.new_event_loop()
            return loop.run_until_complete(crawl())
        except Exception as e:
            return [{"title": f"Crawl4AI 错误: {e}", "url": "", "snippet": ""}]

    def _scrape_crawl4ai(self, url: str) -> Optional[str]:
        try:
            import asyncio
            from crawl4ai import AsyncWebCrawler

            async def crawl():
                async with AsyncWebCrawler() as crawler:
                    result = await crawler.arun(url=url)
                    return result.markdown if result else None

            loop = asyncio.new_event_loop()
            return loop.run_until_complete(crawl())
        except Exception:
            pass
        return None

    # ── Browser Use ──

    def _search_browser_use(self, query: str, max_results: int) -> List[Dict]:
        try:
            from browser_use import Agent, Controller

            async def run():
                agent = Agent(
                    task=f"搜索: {query}，返回前{max_results}个结果",
                    controller=Controller(),
                )
                result = await agent.run()
                if result:
                    return [{"title": f"Browser Use: {query}", "url": "", "snippet": str(result)[:500]}]
                return []

            import asyncio
            loop = asyncio.new_event_loop()
            return loop.run_until_complete(run())
        except Exception as e:
            return [{"title": f"Browser Use 错误: {e}", "url": "", "snippet": ""}]

    def _scrape_browser_use(self, url: str) -> Optional[str]:
        try:
            from browser_use import Agent, Controller

            async def run():
                agent = Agent(
                    task=f"打开 {url} 并提取页面内容",
                    controller=Controller(),
                )
                result = await agent.run()
                return str(result) if result else None

            import asyncio
            loop = asyncio.new_event_loop()
            return loop.run_until_complete(run())
        except Exception:
            pass
        return None

    # ── XCrawl ──

    def _search_xcrawl(self, query: str, max_results: int) -> List[Dict]:
        try:
            from xcrawl import XCrawl

            crawler = XCrawl()
            search_url = f"https://www.baidu.com/s?wd={query}"
            result = crawler.crawl(search_url)

            if result and hasattr(result, "text"):
                return [{
                    "title": f"搜索: {query}",
                    "url": search_url,
                    "snippet": result.text[:500],
                }]
        except Exception as e:
            return [{"title": f"XCrawl 错误: {e}", "url": "", "snippet": ""}]
        return []


# 全局实例
web_scraper = WebScraperEngine()


if __name__ == "__main__":
    status = web_scraper.get_status()
    print(f"爬虫状态: {status['count']}/{status['total']} 可用")
    for name, available in status["available"].items():
        print(f"  {'✅' if available else '❌'} {name}")
