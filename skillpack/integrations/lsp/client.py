"""
LSP 客户端 (v6.0)

提供 LSP 协议客户端实现，支持代码智能功能。
"""

import subprocess
import json
import threading
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
from dataclasses import dataclass

from .config import LSPConfig, LSPServerConfig, detect_language


@dataclass
class Location:
    """位置信息"""
    file: Path
    line: int
    column: int
    end_line: Optional[int] = None
    end_column: Optional[int] = None


@dataclass
class Symbol:
    """符号信息"""
    name: str
    kind: str
    location: Location
    container: Optional[str] = None


@dataclass
class HoverInfo:
    """悬停信息"""
    content: str
    language: Optional[str] = None


class LSPClient:
    """
    LSP 客户端

    支持功能:
    - go-to-definition
    - find-references
    - hover
    - document-symbols
    - workspace-symbols
    """

    def __init__(self, config: LSPConfig):
        """
        初始化 LSP 客户端

        Args:
            config: LSP 配置
        """
        self._config = config
        self._servers: Dict[str, subprocess.Popen] = {}
        self._request_id = 0
        self._pending_requests: Dict[int, threading.Event] = {}
        self._responses: Dict[int, Any] = {}
        self._initialized: Dict[str, bool] = {}
        self._lock = threading.Lock()

    def start(self, language: str) -> bool:
        """
        启动指定语言的 LSP 服务器

        Args:
            language: 语言标识

        Returns:
            是否启动成功
        """
        if not self._config.enabled:
            return False

        if language in self._servers:
            return True

        server_config = self._config.servers.get(language)
        if not server_config:
            return False

        try:
            # 启动服务器进程
            cmd = [server_config.command] + server_config.args
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self._servers[language] = process

            # 启动读取线程
            reader_thread = threading.Thread(
                target=self._read_responses,
                args=(language, process),
                daemon=True,
            )
            reader_thread.start()

            # 初始化
            return self._initialize(language)

        except FileNotFoundError:
            print(f"⚠️ LSP 服务器未找到: {server_config.command}")
            return False
        except Exception as e:
            print(f"⚠️ LSP 启动失败: {e}")
            return False

    def stop(self, language: str):
        """停止 LSP 服务器"""
        if language in self._servers:
            try:
                self._send_notification(language, "shutdown")
                self._send_notification(language, "exit")
                self._servers[language].terminate()
            except Exception:
                pass
            finally:
                del self._servers[language]
                if language in self._initialized:
                    del self._initialized[language]

    def stop_all(self):
        """停止所有服务器"""
        for language in list(self._servers.keys()):
            self.stop(language)

    def goto_definition(
        self,
        file_path: Path,
        line: int,
        column: int,
    ) -> Optional[Location]:
        """
        跳转到定义

        Args:
            file_path: 文件路径
            line: 行号 (0-indexed)
            column: 列号 (0-indexed)

        Returns:
            定义位置或 None
        """
        language = detect_language(file_path)
        if not language or not self._ensure_started(language):
            return None

        response = self._send_request(
            language,
            "textDocument/definition",
            {
                "textDocument": {"uri": file_path.as_uri()},
                "position": {"line": line, "character": column},
            },
        )

        if not response:
            return None

        # 处理响应
        if isinstance(response, list) and response:
            loc = response[0]
        elif isinstance(response, dict):
            loc = response
        else:
            return None

        return self._parse_location(loc)

    def find_references(
        self,
        file_path: Path,
        line: int,
        column: int,
        include_declaration: bool = True,
    ) -> List[Location]:
        """
        查找引用

        Args:
            file_path: 文件路径
            line: 行号 (0-indexed)
            column: 列号 (0-indexed)
            include_declaration: 是否包含声明

        Returns:
            引用位置列表
        """
        language = detect_language(file_path)
        if not language or not self._ensure_started(language):
            return []

        response = self._send_request(
            language,
            "textDocument/references",
            {
                "textDocument": {"uri": file_path.as_uri()},
                "position": {"line": line, "character": column},
                "context": {"includeDeclaration": include_declaration},
            },
        )

        if not response or not isinstance(response, list):
            return []

        return [
            loc for loc in (self._parse_location(item) for item in response)
            if loc is not None
        ]

    def hover(
        self,
        file_path: Path,
        line: int,
        column: int,
    ) -> Optional[HoverInfo]:
        """
        获取悬停信息

        Args:
            file_path: 文件路径
            line: 行号 (0-indexed)
            column: 列号 (0-indexed)

        Returns:
            悬停信息或 None
        """
        language = detect_language(file_path)
        if not language or not self._ensure_started(language):
            return None

        response = self._send_request(
            language,
            "textDocument/hover",
            {
                "textDocument": {"uri": file_path.as_uri()},
                "position": {"line": line, "character": column},
            },
        )

        if not response or "contents" not in response:
            return None

        contents = response["contents"]

        # 处理不同格式的内容
        if isinstance(contents, str):
            return HoverInfo(content=contents)
        elif isinstance(contents, dict):
            return HoverInfo(
                content=contents.get("value", ""),
                language=contents.get("language"),
            )
        elif isinstance(contents, list):
            parts = []
            for item in contents:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    parts.append(item.get("value", ""))
            return HoverInfo(content="\n\n".join(parts))

        return None

    def document_symbols(self, file_path: Path) -> List[Symbol]:
        """
        获取文档符号

        Args:
            file_path: 文件路径

        Returns:
            符号列表
        """
        language = detect_language(file_path)
        if not language or not self._ensure_started(language):
            return []

        response = self._send_request(
            language,
            "textDocument/documentSymbol",
            {"textDocument": {"uri": file_path.as_uri()}},
        )

        if not response or not isinstance(response, list):
            return []

        return self._parse_symbols(response, file_path)

    def _ensure_started(self, language: str) -> bool:
        """确保服务器已启动"""
        if language not in self._servers:
            return self.start(language)
        return language in self._initialized and self._initialized[language]

    def _initialize(self, language: str) -> bool:
        """初始化 LSP 连接"""
        workspace_root = self._config.workspace_root or Path.cwd()

        response = self._send_request(
            language,
            "initialize",
            {
                "processId": None,
                "rootUri": workspace_root.as_uri(),
                "capabilities": {
                    "textDocument": {
                        "hover": {"contentFormat": ["markdown", "plaintext"]},
                        "definition": {"linkSupport": True},
                        "references": {},
                        "documentSymbol": {"hierarchicalDocumentSymbolSupport": True},
                    },
                    "workspace": {
                        "symbol": {"symbolKind": {"valueSet": list(range(1, 27))}},
                    },
                },
            },
        )

        if response:
            self._send_notification(language, "initialized", {})
            self._initialized[language] = True
            return True

        return False

    def _send_request(
        self,
        language: str,
        method: str,
        params: Dict,
    ) -> Optional[Any]:
        """发送请求并等待响应"""
        if language not in self._servers:
            return None

        with self._lock:
            self._request_id += 1
            request_id = self._request_id

        message = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }

        # 创建等待事件
        event = threading.Event()
        self._pending_requests[request_id] = event

        # 发送消息
        self._send_message(language, message)

        # 等待响应
        if event.wait(timeout=self._config.timeout_seconds):
            result = self._responses.pop(request_id, None)
            del self._pending_requests[request_id]
            return result

        # 超时
        del self._pending_requests[request_id]
        return None

    def _send_notification(
        self,
        language: str,
        method: str,
        params: Optional[Dict] = None,
    ):
        """发送通知（无需响应）"""
        message = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params:
            message["params"] = params

        self._send_message(language, message)

    def _send_message(self, language: str, message: Dict):
        """发送 LSP 消息"""
        if language not in self._servers:
            return

        content = json.dumps(message)
        header = f"Content-Length: {len(content)}\r\n\r\n"

        try:
            self._servers[language].stdin.write(header.encode())
            self._servers[language].stdin.write(content.encode())
            self._servers[language].stdin.flush()
        except Exception:
            pass

    def _read_responses(self, language: str, process: subprocess.Popen):
        """读取响应线程"""
        while language in self._servers:
            try:
                # 读取头部
                header = b""
                while b"\r\n\r\n" not in header:
                    byte = process.stdout.read(1)
                    if not byte:
                        return
                    header += byte

                # 解析 Content-Length
                header_str = header.decode()
                content_length = 0
                for line in header_str.split("\r\n"):
                    if line.startswith("Content-Length:"):
                        content_length = int(line.split(":")[1].strip())
                        break

                if content_length == 0:
                    continue

                # 读取内容
                content = process.stdout.read(content_length).decode()
                message = json.loads(content)

                # 处理响应
                if "id" in message:
                    request_id = message["id"]
                    if request_id in self._pending_requests:
                        self._responses[request_id] = message.get("result")
                        self._pending_requests[request_id].set()

            except Exception:
                break

    def _parse_location(self, data: Dict) -> Optional[Location]:
        """解析位置信息"""
        if not data:
            return None

        uri = data.get("uri", data.get("targetUri", ""))
        range_data = data.get("range", data.get("targetRange", {}))

        if not uri or not range_data:
            return None

        start = range_data.get("start", {})
        end = range_data.get("end", {})

        # 从 URI 解析路径
        if uri.startswith("file://"):
            file_path = Path(uri[7:])
        else:
            file_path = Path(uri)

        return Location(
            file=file_path,
            line=start.get("line", 0),
            column=start.get("character", 0),
            end_line=end.get("line"),
            end_column=end.get("character"),
        )

    def _parse_symbols(
        self,
        data: List[Dict],
        file_path: Path,
    ) -> List[Symbol]:
        """解析符号列表"""
        symbols = []

        SYMBOL_KINDS = {
            1: "File", 2: "Module", 3: "Namespace", 4: "Package",
            5: "Class", 6: "Method", 7: "Property", 8: "Field",
            9: "Constructor", 10: "Enum", 11: "Interface", 12: "Function",
            13: "Variable", 14: "Constant", 15: "String", 16: "Number",
            17: "Boolean", 18: "Array", 19: "Object", 20: "Key",
            21: "Null", 22: "EnumMember", 23: "Struct", 24: "Event",
            25: "Operator", 26: "TypeParameter",
        }

        def process_symbol(item: Dict, container: Optional[str] = None):
            name = item.get("name", "")
            kind_num = item.get("kind", 0)
            kind = SYMBOL_KINDS.get(kind_num, "Unknown")

            # 获取位置
            loc_data = item.get("location", {})
            if not loc_data:
                # DocumentSymbol 格式
                range_data = item.get("range", item.get("selectionRange", {}))
                loc_data = {"uri": file_path.as_uri(), "range": range_data}

            loc = self._parse_location(loc_data)
            if loc:
                symbols.append(Symbol(
                    name=name,
                    kind=kind,
                    location=loc,
                    container=container,
                ))

            # 处理子符号
            for child in item.get("children", []):
                process_symbol(child, name)

        for item in data:
            process_symbol(item)

        return symbols
