"""LLM 客户端 — 支持联网搜索（通过 Firecrawl/Crawl4AI）+ 对话记忆自动存储"""

import json
import urllib.request
import urllib.error
from typing import Optional, List, Dict

from app.utils.config import settings
from app.knowledge.conversation_memory import memory


class LLMClient:
    """统一 LLM 调用接口"""

    def __init__(self, api_base: Optional[str] = None, api_key: Optional[str] = None, model: Optional[str] = None):
        # 用 is None 判断而不是 or —— 显式传入空字符串时应视作"空"，
        # 否则测试连接时会静默回落到已保存的旧配置，给出误导性的结果。
        self.api_base = (settings.LLM_API_BASE if api_base is None else api_base).rstrip("/")
        self.api_key = settings.LLM_API_KEY if api_key is None else api_key
        self.model = settings.LLM_MODEL if model is None else model

    def chat(self, messages: list, temperature: float = 0.7, max_tokens: int = 1024) -> str:
        """发送聊天请求，返回文本回复"""
        url = f"{self.api_base}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        body = json.dumps({
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }).encode("utf-8")

        try:
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())
                return result["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            return f"[API错误 {e.code}] {e.read().decode()[:200]}"
        except urllib.error.URLError as e:
            return f"[连接失败] {e.reason}。请检查API地址。"
        except Exception as e:
            return f"[错误] {str(e)}"

    def chat_with_memory(self, user_message: str, session_id: str = "default",
                         temperature: float = 0.7, max_tokens: int = 1024) -> str:
        """
        带记忆的对话：自动加载历史记录、存储新对话
        """
        # 1. 存储用户消息到记忆库
        memory.add_message("user", user_message, session_id=session_id)

        # 2. 加载历史对话
        history = memory.get_history(session_id=session_id, max_tokens=2000)

        # 3. 尝试知识库检索增强
        from app.knowledge.vector_store import VectorStore
        vs = VectorStore()
        kb_results = vs.search(user_message, limit=3)

        # 4. 构建 system prompt
        system_prompt = "你是一个专业的建筑工程管理AI助手。回答要简洁、准确、有据可查。"

        if kb_results:
            kb_context = "\n".join([r["content"] for r in kb_results])
            system_prompt += f"\n\n[知识库相关条目]\n{kb_context}"

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        # 5. 调用 API
        reply = self.chat(messages, temperature=temperature, max_tokens=max_tokens)

        # 6. 存储回复到记忆库
        memory.add_message("assistant", reply, session_id=session_id)

        return reply

    def chat_with_memory_async(self, user_message: str, session_id: str = "default",
                               temperature: float = 0.7, max_tokens: int = 1024,
                               on_done=None, on_error=None):
        """
        带记忆的异步对话：网络请求在后台线程执行，不阻塞 GUI 主线程。

        客户端"平台莫名卡住"的根因就是 chat() 的 urllib 请求在主线程里跑，
        网络一慢（30 秒超时窗口内）整个界面冻结、点哪都没反应。

        on_done(str)  —— 请求成功后回调（在主线程触发）
        on_error(str) —— 请求失败后回调（在主线程触发）
        """
        from app.ui.qt_task_runner import run_in_thread
        run_in_thread(
            lambda: self.chat_with_memory(user_message, session_id=session_id,
                                          temperature=temperature, max_tokens=max_tokens),
            on_done=on_done, on_error=on_error,
        )

    def web_search(self, query: str, region: str = "四川") -> str:
        """
        联网搜索：先用 Firecrawl/Crawl4AI 抓取结果，再用 LLM 总结
        """
        search_query = f"{query} {region}" if region else query
        raw_results = []

        # 1. Firecrawl 搜索
        try:
            from firecrawl import FirecrawlApp
            app = FirecrawlApp()
            result = app.search(search_query, limit=5)
            if isinstance(result, dict) and "data" in result:
                for r in result["data"][:5]:
                    raw_results.append({
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "snippet": r.get("description", r.get("content", "")),
                    })
        except Exception:
            pass

        # 2. Crawl4AI 备用
        if not raw_results:
            try:
                import asyncio
                from crawl4ai import AsyncWebCrawler

                async def crawl():
                    async with AsyncWebCrawler() as crawler:
                        search_url = f"https://www.baidu.com/s?wd={search_query}"
                        result = await crawler.arun(url=search_url)
                        if result and result.markdown:
                            return [{"title": f"搜索: {search_query}", "url": search_url, "snippet": result.markdown[:800]}]
                        return []

                loop = asyncio.new_event_loop()
                raw_results = loop.run_until_complete(crawl())
            except Exception:
                pass

        # 3. 如果都没搜到，用 LLM 的知识回答
        if not raw_results:
            prompt = f"""请回答以下问题。如果涉及实时数据，请明确说明你的知识截止日期。
问题：{query}
区域：{region}
"""
            return self.chat([{"role": "user", "content": prompt}], temperature=0.3)

        # 4. 构建搜索结果上下文
        search_context = "\n\n".join([
            f"标题: {r['title']}\n内容: {r['snippet']}\n来源: {r['url']}"
            for r in raw_results[:5]
        ])

        # 5. 让 LLM 总结搜索结果
        prompt = f"""你是一个联网搜索助手。以下是从互联网搜索到的关于「{query}」的结果，请用中文总结，标注信息来源。

搜索结果：
{search_context}

请给出简洁、准确的回答，并注明每个信息的来源。"""

        reply = self.chat([{"role": "user", "content": prompt}], temperature=0.3, max_tokens=1000)

        # 6. 缓存到知识库
        try:
            from app.knowledge.vector_store import VectorStore
            vs = VectorStore()
            vs.add_text(f"联网搜索:{query}", f"{search_context}\n\n{reply}", source_type="web_search")
        except Exception:
            pass

        return reply

    def is_available(self) -> tuple:
        """检查 API 是否可用。

        先试标准的 /models 列表；不少国产平台（如智谱 BigModel）不提供该端点，
        因此失败后回退到发一次极小的真实对话请求——那才是真正能用的判据。
        """
        if not self.api_base:
            return False, "❌ 还没有填写 API 地址"

        url = f"{self.api_base}/models"
        try:
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {self.api_key}"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
                models = [m.get("id", "") for m in data.get("data", [])]
                if self.model in models:
                    return True, f"✅ 连接成功，模型 {self.model} 可用"
                if models:
                    return True, (f"✅ 连接成功。\n注意：模型列表里没有「{self.model}」，"
                                  f"现有模型包括 {', '.join(models[:5])}，请确认模型名是否正确。")
                return True, "✅ 连接成功"
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                return False, f"❌ 鉴权失败（HTTP {e.code}）：API Key 不对或未领取。"
        except Exception:
            pass

        # 回退：发一次最小对话请求
        try:
            reply = self.chat([{"role": "user", "content": "回复一个字：好"}],
                              temperature=0, max_tokens=8)
        except Exception as e:
            return False, f"❌ 连接失败：{e}"

        if reply.startswith("[API错误"):
            detail = reply
            if "401" in reply or "403" in reply:
                return False, f"❌ 鉴权失败：API Key 不对或未领取。\n{detail}"
            if "404" in reply:
                return False, (f"❌ 接口地址或模型名不对（404）。\n{detail}\n"
                               "请检查 API 地址结尾是否多了或少了 /v1。")
            return False, f"❌ 调用失败：{detail}"
        if reply.startswith("[连接失败]") or reply.startswith("[错误]"):
            return False, f"❌ {reply}"

        return True, f"✅ 连接成功，模型 {self.model} 已就绪。\n模型返回：{reply[:40]}"

    def analyze_contract_risk(self, contract_text: str) -> dict:
        """合同风险识别：本地规则 + LLM 增强"""
        from app.agent.risk_analyzer import RiskAnalyzer
        local_result = RiskAnalyzer().analyze(contract_text)

        prompt = f"""你是一个建筑工程合同审查专家。分析以下合同条款的风险点，按 JSON 格式返回：
{{"tags": ["风险类别1", "风险类别2"], "warnings": ["具体风险说明..."], "risk_level": "高/中/低"}}

合同内容：
{contract_text[:3000]}
"""

        reply = self.chat([{"role": "user", "content": prompt}], temperature=0.3)
        try:
            ai_result = json.loads(reply.replace("```json", "").replace("```", "").strip())
            all_tags = list(set(local_result.get("tags", []) + ai_result.get("tags", [])))
            all_warnings = list(set(local_result.get("warnings", []) + ai_result.get("warnings", [])))
            return {
                "tags": all_tags,
                "warnings": all_warnings,
                "risk_level": max(local_result.get("risk_level", "低"),
                                  ai_result.get("risk_level", "低"),
                                  key=lambda x: {"低": 0, "中": 1, "高": 2}.get(x, 0)),
            }
        except Exception:
            return local_result


# 全局实例
llm = LLMClient()
