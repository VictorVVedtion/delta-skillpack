"""NotebookLM knowledge engine integration."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from ..models import (
    Citation,
    KnowledgeResponse,
    NotebookLMConfig,
    NotebookType,
    QueryContext,
    SkillStep,
    StoryType,
)
from .memory import MemoryManager


class QueryCache:
    """三层查询缓存：内存 → 文件 → 语义。"""

    def __init__(self, cache_dir: Path, default_ttl_minutes: int = 30):
        self.cache_dir = cache_dir
        self.default_ttl = timedelta(minutes=default_ttl_minutes)
        self.memory_cache: dict[str, tuple[KnowledgeResponse, datetime]] = {}
        self.cache_file = cache_dir / "knowledge_cache.json"
        self._load_file_cache()

    def _load_file_cache(self) -> None:
        """Load cache from file."""
        self.file_cache: dict[str, dict[str, Any]] = {}
        if self.cache_file.exists():
            try:
                data = json.loads(self.cache_file.read_text(encoding="utf-8"))
                self.file_cache = data.get("entries", {})
            except (json.JSONDecodeError, OSError):
                pass

    def _save_file_cache(self) -> None:
        """Persist cache to file."""
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        data = {"entries": self.file_cache, "updated_at": datetime.now().isoformat()}
        self.cache_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _compute_key(self, question: str, notebook_type: NotebookType) -> str:
        """Compute cache key."""
        content = f"{notebook_type.value}:{question.lower().strip()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def get(
        self, question: str, notebook_type: NotebookType, ttl: timedelta | None = None
    ) -> KnowledgeResponse | None:
        """Get from cache (memory → file → semantic)."""
        key = self._compute_key(question, notebook_type)
        effective_ttl = ttl or self.default_ttl
        now = datetime.now()

        # Layer 1: Memory cache
        if key in self.memory_cache:
            response, cached_at = self.memory_cache[key]
            if now - cached_at < effective_ttl:
                response.cached = True
                return response

        # Layer 2: File cache
        if key in self.file_cache:
            entry = self.file_cache[key]
            cached_at = datetime.fromisoformat(entry["cached_at"])
            if now - cached_at < effective_ttl:
                response = KnowledgeResponse(**entry["response"])
                response.cached = True
                self.memory_cache[key] = (response, cached_at)
                return response

        # Layer 3: Semantic cache (simplified Jaccard similarity)
        return self._get_semantic(question, notebook_type, effective_ttl)

    def _get_semantic(
        self,
        question: str,
        notebook_type: NotebookType,
        ttl: timedelta,
        threshold: float = 0.85,
    ) -> KnowledgeResponse | None:
        """Find semantically similar cached question."""
        q_tokens = set(question.lower().split())
        now = datetime.now()

        for _key, entry in self.file_cache.items():
            if entry.get("notebook_type") != notebook_type.value:
                continue
            cached_at = datetime.fromisoformat(entry["cached_at"])
            if now - cached_at >= ttl:
                continue

            cached_tokens = set(entry.get("question", "").lower().split())
            if not cached_tokens:
                continue

            intersection = len(q_tokens & cached_tokens)
            union = len(q_tokens | cached_tokens)
            similarity = intersection / union if union > 0 else 0

            if similarity >= threshold:
                response = KnowledgeResponse(**entry["response"])
                response.cached = True
                return response

        return None

    def set(self, question: str, notebook_type: NotebookType, response: KnowledgeResponse) -> None:
        """Store in cache."""
        key = self._compute_key(question, notebook_type)
        now = datetime.now()

        # Memory cache
        self.memory_cache[key] = (response, now)

        # File cache
        self.file_cache[key] = {
            "question": question,
            "notebook_type": notebook_type.value,
            "response": response.model_dump(),
            "cached_at": now.isoformat(),
        }
        self._save_file_cache()


class NotebookRouter:
    """智能笔记本路由器。"""

    # 基于步骤和故事类型的路由规则
    ROUTING_RULES: dict[tuple[SkillStep | None, StoryType | None], NotebookType] = {
        (SkillStep.PLAN, StoryType.FEATURE): NotebookType.ARCHITECTURE,
        (SkillStep.PLAN, StoryType.REFACTOR): NotebookType.PATTERNS,
        (SkillStep.PLAN, None): NotebookType.ARCHITECTURE,
        (SkillStep.IMPLEMENT, StoryType.FEATURE): NotebookType.API,
        (SkillStep.IMPLEMENT, StoryType.UI): NotebookType.PATTERNS,
        (SkillStep.IMPLEMENT, None): NotebookType.API,
        (SkillStep.REVIEW, None): NotebookType.STANDARDS,
        (SkillStep.UI, StoryType.UI): NotebookType.PATTERNS,
        (SkillStep.UI, None): NotebookType.PATTERNS,
    }

    # 关键词到笔记本类型的映射
    KEYWORD_RULES: dict[NotebookType, list[str]] = {
        NotebookType.ARCHITECTURE: [
            "architecture",
            "design",
            "adr",
            "c4",
            "system",
            "structure",
        ],
        NotebookType.PATTERNS: ["pattern", "best practice", "convention", "idiom"],
        NotebookType.API: ["api", "endpoint", "interface", "method", "function"],
        NotebookType.STANDARDS: ["standard", "guideline", "style", "lint", "security"],
        NotebookType.TROUBLESHOOTING: [
            "error",
            "fix",
            "bug",
            "issue",
            "problem",
            "debug",
        ],
        NotebookType.DOMAIN: ["business", "domain", "rule", "requirement"],
    }

    def route(self, question: str, context: QueryContext) -> NotebookType:
        """Route question to appropriate notebook."""
        # 1. 规则匹配
        key = (context.current_step, context.story_type)
        if key in self.ROUTING_RULES:
            return self.ROUTING_RULES[key]

        # 2. 只按步骤匹配
        step_key = (context.current_step, None)
        if step_key in self.ROUTING_RULES:
            return self.ROUTING_RULES[step_key]

        # 3. 关键词匹配
        question_lower = question.lower()
        for notebook_type, keywords in self.KEYWORD_RULES.items():
            if any(kw in question_lower for kw in keywords):
                return notebook_type

        # 4. 默认
        return NotebookType.DOMAIN


class NotebookLMBridge:
    """NotebookLM 知识引擎桥接器。

    通过调用 notebooklm-skill 与 NotebookLM 交互，提供：
    1. 主动查询能力 - 任何模块可查询知识库
    2. 语义路由 - 自动路由到正确的笔记本
    3. 三层缓存 - 减少重复查询
    4. 引用追踪 - 保留知识来源
    """

    # 缓存 TTL 策略
    TTL_LONG = timedelta(minutes=120)  # 架构/模式问题
    TTL_SHORT = timedelta(minutes=10)  # 代码验证问题
    TTL_DEFAULT = timedelta(minutes=30)

    LONG_TTL_PATTERNS = [
        r"what is the .* (pattern|architecture|design)",
        r"how should .* be structured",
        r"what are the (coding standards|guidelines)",
    ]

    SHORT_TTL_PATTERNS = [
        r"is .* correct",
        r"does .* follow",
        r"should .* be",
        r"verify",
    ]

    def __init__(
        self,
        repo: Path,
        memory: MemoryManager,
        config: NotebookLMConfig,
    ):
        self.repo = Path(repo)
        self.memory = memory
        self.config = config
        self.skill_path = Path(config.skill_path).expanduser()

        cache_dir = self.memory.ralph_dir / "knowledge"
        self.cache = QueryCache(cache_dir, config.default_cache_ttl_minutes)
        self.router = NotebookRouter()

    def _get_ttl(self, question: str) -> timedelta:
        """根据问题类型返回缓存 TTL。"""
        question_lower = question.lower()

        for pattern in self.LONG_TTL_PATTERNS:
            if re.search(pattern, question_lower):
                return self.TTL_LONG

        for pattern in self.SHORT_TTL_PATTERNS:
            if re.search(pattern, question_lower):
                return self.TTL_SHORT

        return self.TTL_DEFAULT

    async def query(
        self,
        question: str,
        context: QueryContext,
        notebook_hint: NotebookType | None = None,
    ) -> KnowledgeResponse:
        """向 NotebookLM 查询知识。

        Args:
            question: 要查询的问题
            context: 查询上下文 (story, step, etc.)
            notebook_hint: 可选的笔记本类型提示

        Returns:
            带引用的知识响应
        """
        # 1. 确定笔记本类型
        notebook_type = notebook_hint or self.router.route(question, context)

        # 2. 检查缓存
        ttl = self._get_ttl(question)
        if self.config.cache_enabled:
            cached = self.cache.get(question, notebook_type, ttl)
            if cached:
                return cached

        # 3. 执行查询
        start_time = datetime.now()
        try:
            response = await self._execute_query(question, notebook_type)
        except (OSError, asyncio.TimeoutError, ValueError) as e:
            # 优雅降级
            return KnowledgeResponse(
                question=question,
                answer="",
                citations=[],
                confidence=0.0,
                notebook_type=notebook_type,
                query_time_ms=0,
                cached=False,
                error=str(e),
            )

        query_time = int((datetime.now() - start_time).total_seconds() * 1000)
        response.query_time_ms = query_time

        # 4. 缓存结果
        if self.config.cache_enabled and response.confidence > 0:
            self.cache.set(question, notebook_type, response)

        # 5. 记录到内存
        self._log_query(question, response, notebook_type)

        return response

    async def batch_query(
        self,
        questions: list[str],
        context: QueryContext,
    ) -> list[KnowledgeResponse]:
        """批量查询，按笔记本分组优化。"""
        if not questions:
            return []

        # 按笔记本类型分组
        grouped: dict[NotebookType, list[tuple[int, str]]] = {}
        for i, q in enumerate(questions):
            notebook_type = self.router.route(q, context)
            if notebook_type not in grouped:
                grouped[notebook_type] = []
            grouped[notebook_type].append((i, q))

        # 按组执行查询
        results: list[tuple[int, KnowledgeResponse]] = []

        for notebook_type, items in grouped.items():
            for idx, question in items:
                response = await self.query(question, context, notebook_hint=notebook_type)
                results.append((idx, response))

                # 批量查询间延迟
                if self.config.batch_delay_seconds > 0:
                    await asyncio.sleep(self.config.batch_delay_seconds)

        # 按原顺序排列
        results.sort(key=lambda x: x[0])
        return [r for _, r in results]

    async def _execute_query(self, question: str, notebook_type: NotebookType) -> KnowledgeResponse:
        """通过 notebooklm-skill 执行查询。"""
        # 获取笔记本 ID
        notebook_id = self._get_notebook_id(notebook_type)
        if not notebook_id:
            return KnowledgeResponse(
                question=question,
                answer="",
                citations=[],
                confidence=0.0,
                notebook_type=notebook_type,
                error=f"No notebook configured for type: {notebook_type.value}",
            )

        # 构建命令
        run_script = self.skill_path / "scripts" / "run.py"
        if not run_script.exists():
            return KnowledgeResponse(
                question=question,
                answer="",
                citations=[],
                confidence=0.0,
                notebook_type=notebook_type,
                error=f"NotebookLM skill not installed at {self.skill_path}",
            )

        cmd = [
            "python",
            str(run_script),
            "ask",
            "--notebook",
            notebook_id,
            "--question",
            question,
        ]

        # 执行
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.skill_path),
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=self.config.query_timeout_seconds,
            )
        except TimeoutError:
            return KnowledgeResponse(
                question=question,
                answer="",
                citations=[],
                confidence=0.0,
                notebook_type=notebook_type,
                error="Query timeout",
            )
        except (OSError, asyncio.TimeoutError) as e:
            return KnowledgeResponse(
                question=question,
                answer="",
                citations=[],
                confidence=0.0,
                notebook_type=notebook_type,
                error=str(e),
            )

        if proc.returncode != 0:
            error_msg = stderr.decode("utf-8", errors="replace").strip()
            return KnowledgeResponse(
                question=question,
                answer="",
                citations=[],
                confidence=0.0,
                notebook_type=notebook_type,
                error=error_msg or f"Exit code: {proc.returncode}",
            )

        # 解析响应
        return self._parse_response(
            question, notebook_type, stdout.decode("utf-8", errors="replace")
        )

    def _get_notebook_id(self, notebook_type: NotebookType) -> str | None:
        """Get notebook ID for type."""
        for nb in self.config.notebooks:
            if nb.type == notebook_type:
                return nb.id
        return self.config.default_notebook_id

    def _parse_response(
        self, question: str, notebook_type: NotebookType, output: str
    ) -> KnowledgeResponse:
        """Parse notebooklm-skill output."""
        # 尝试解析 JSON
        try:
            data = json.loads(output)
            citations = [
                Citation(
                    source=c.get("source", "Unknown"),
                    page=c.get("page"),
                    section=c.get("section"),
                    quote=c.get("quote", ""),
                )
                for c in data.get("citations", [])
            ]
            return KnowledgeResponse(
                question=question,
                answer=data.get("answer", ""),
                citations=citations,
                confidence=data.get("confidence", 0.8),
                notebook_type=notebook_type,
            )
        except json.JSONDecodeError:
            # 纯文本响应
            return KnowledgeResponse(
                question=question,
                answer=output.strip(),
                citations=[],
                confidence=0.5,  # 无引用时置信度较低
                notebook_type=notebook_type,
            )

    def _log_query(
        self, question: str, response: KnowledgeResponse, notebook_type: NotebookType
    ) -> None:
        """Log query to memory."""
        log_entry = (
            f"[NotebookLM:{notebook_type.value}] Q: {question[:100]}... "
            f"A: {response.summary[:100]}... "
            f"(confidence={response.confidence:.2f}, cached={response.cached})"
        )
        self.memory.append_progress(0, "KNOWLEDGE", "QUERY", log_entry)

    def format_context(self, responses: list[KnowledgeResponse]) -> str:
        """格式化为可注入 prompt 的上下文块。"""
        if not responses:
            return ""

        sections = []
        for resp in responses:
            if not resp.answer or resp.error:
                continue

            section = f"### {resp.question}\n\n{resp.answer}"

            if resp.citations:
                section += "\n\n**Sources:**\n"
                for i, cite in enumerate(resp.citations, 1):
                    source_info = cite.source
                    if cite.section:
                        source_info += f" - {cite.section}"
                    section += f"{i}. {source_info}\n"

            sections.append(section)

        if not sections:
            return ""

        return "## External Knowledge (from NotebookLM)\n\n" + "\n\n---\n\n".join(sections)
