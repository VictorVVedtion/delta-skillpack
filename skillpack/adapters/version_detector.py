"""
版本检测器 (v6.0)

自动检测 Codex/Gemini CLI 版本并探测可用功能。
"""

import subprocess
import re
import os
from datetime import datetime
from typing import Optional, Dict
from dataclasses import dataclass

from .base import CLIVersion, FeatureStatus


@dataclass
class VersionCache:
    """版本缓存"""
    codex: Optional[CLIVersion] = None
    gemini: Optional[CLIVersion] = None
    cached_at: Optional[str] = None


class VersionDetector:
    """
    CLI 版本检测器

    自动检测 Codex 和 Gemini CLI 版本，支持缓存和离线模式。
    """

    # Codex 功能版本映射
    CODEX_FEATURES: Dict[str, str] = {
        "skills": "0.89.0",                 # Skills 系统
        "fork": "0.89.0",                   # Fork 分支功能
        "gpt-5.2-codex": "0.89.0",          # GPT-5.2-Codex 模型
        "multi-conversation": "0.85.0",     # 多对话控制
        "thread-rollback": "0.85.0",        # 线程回滚
        "full-auto": "0.80.0",              # --full-auto 参数
        "sandbox": "0.80.0",                # 沙箱模式
        "exec": "0.75.0",                   # exec 子命令
        "basic": "0.70.0",                  # 基础功能
    }

    # Gemini 功能版本映射
    GEMINI_FEATURES: Dict[str, str] = {
        "agent-skills": "0.25.0",           # Agent Skills
        "json-output": "0.25.0",            # JSON 输出
        "workspace-integration": "0.25.0",  # Workspace 集成
        "policy-engine": "0.25.0",          # 策略引擎
        "gemini-3-flash": "0.25.0",         # Gemini 3 Flash 模型
        "gemini-3-pro": "0.20.0",           # Gemini 3 Pro 模型
        "sandbox": "0.20.0",                # 沙箱模式 (-s)
        "yolo": "0.20.0",                   # YOLO 模式 (--yolo)
        "file-context": "0.15.0",           # @ 文件引用
        "basic": "0.10.0",                  # 基础功能
    }

    def __init__(self, cache_ttl_seconds: int = 300):
        """
        初始化版本检测器

        Args:
            cache_ttl_seconds: 缓存有效期（秒）
        """
        self._cache = VersionCache()
        self._cache_ttl = cache_ttl_seconds

    def detect_codex(self, force_refresh: bool = False) -> CLIVersion:
        """
        检测 Codex CLI 版本

        Args:
            force_refresh: 强制刷新缓存

        Returns:
            CLIVersion 版本信息
        """
        if not force_refresh and self._cache.codex:
            return self._cache.codex

        version = self._run_version_command("codex", "--version")

        # 探测功能（保留原始 features 中的特殊状态）
        original_features = version.features.copy() if version.features else {}
        features = self._probe_features(version, self.CODEX_FEATURES)
        features.update({k: v for k, v in original_features.items() if k not in self.CODEX_FEATURES})
        version.features = features

        self._cache.codex = version
        self._cache.cached_at = datetime.now().isoformat()

        return version

    def detect_gemini(self, force_refresh: bool = False) -> CLIVersion:
        """
        检测 Gemini CLI 版本

        Args:
            force_refresh: 强制刷新缓存

        Returns:
            CLIVersion 版本信息
        """
        if not force_refresh and self._cache.gemini:
            return self._cache.gemini

        version = self._run_version_command("gemini", "--version")

        # 探测功能（保留原始 features 中的特殊状态）
        original_features = version.features.copy() if version.features else {}
        features = self._probe_features(version, self.GEMINI_FEATURES)
        features.update({k: v for k, v in original_features.items() if k not in self.GEMINI_FEATURES})
        version.features = features

        self._cache.gemini = version
        self._cache.cached_at = datetime.now().isoformat()

        return version

    def detect_all(self, force_refresh: bool = False) -> Dict[str, CLIVersion]:
        """
        检测所有 CLI 版本

        Returns:
            Dict[cli_name, CLIVersion]
        """
        return {
            "codex": self.detect_codex(force_refresh),
            "gemini": self.detect_gemini(force_refresh),
        }

    def _run_version_command(self, cli: str, version_flag: str) -> CLIVersion:
        """
        执行版本检测命令

        Args:
            cli: CLI 名称
            version_flag: 版本参数

        Returns:
            CLIVersion 版本信息
        """
        detected_at = datetime.now().isoformat()

        try:
            result = subprocess.run(
                [cli, version_flag],
                capture_output=True,
                text=True,
                timeout=10,
            )

            raw_output = result.stdout.strip() or result.stderr.strip()
            version = self._parse_version(raw_output)

            return CLIVersion(
                cli_name=cli,
                version=version,
                raw_output=raw_output,
                detected_at=detected_at,
            )

        except FileNotFoundError:
            # CLI 未安装
            return CLIVersion(
                cli_name=cli,
                version="0.0.0",
                raw_output=f"{cli} not found",
                detected_at=detected_at,
                features={"installed": FeatureStatus.UNAVAILABLE},
            )

        except subprocess.TimeoutExpired:
            # 超时
            return CLIVersion(
                cli_name=cli,
                version="0.0.0",
                raw_output="timeout",
                detected_at=detected_at,
                features={"timeout": FeatureStatus.UNAVAILABLE},
            )

        except Exception as e:
            # 其他错误
            return CLIVersion(
                cli_name=cli,
                version="0.0.0",
                raw_output=str(e),
                detected_at=detected_at,
            )

    def _parse_version(self, output: str) -> str:
        """
        解析版本号

        支持格式:
        - "codex 0.89.0"
        - "gemini-cli version 0.25.0"
        - "0.89.0"
        - "v0.89.0"
        """
        # 匹配常见版本格式
        patterns = [
            r"(\d+\.\d+\.\d+(?:-[\w.]+)?)",  # 0.89.0 或 0.89.0-beta.1
            r"v(\d+\.\d+\.\d+)",              # v0.89.0
            r"version\s+(\d+\.\d+\.\d+)",     # version 0.89.0
        ]

        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return match.group(1)

        return "0.0.0"

    def _probe_features(
        self,
        version: CLIVersion,
        feature_map: Dict[str, str]
    ) -> Dict[str, FeatureStatus]:
        """
        根据版本探测可用功能

        Args:
            version: CLI 版本信息
            feature_map: 功能-版本映射

        Returns:
            功能状态字典
        """
        features = {}

        for feature, min_version in feature_map.items():
            if version >= min_version:
                features[feature] = FeatureStatus.AVAILABLE
            else:
                features[feature] = FeatureStatus.UNAVAILABLE

        return features

    def get_install_command(self, cli: str) -> str:
        """获取安装命令"""
        commands = {
            "codex": "npm install -g @openai/codex",
            "gemini": "npm install -g @google/gemini-cli",
        }
        return commands.get(cli, f"# Unknown CLI: {cli}")

    def get_upgrade_command(self, cli: str) -> str:
        """获取升级命令"""
        commands = {
            "codex": "npm update -g @openai/codex",
            "gemini": "npm update -g @google/gemini-cli",
        }
        return commands.get(cli, f"# Unknown CLI: {cli}")

    def format_version_report(self) -> str:
        """格式化版本报告"""
        codex = self.detect_codex()
        gemini = self.detect_gemini()

        lines = [
            "╔══════════════════════════════════════════════════════════╗",
            "║              Skillpack v6.0 CLI 版本检测                 ║",
            "╠══════════════════════════════════════════════════════════╣",
        ]

        # Codex 状态
        codex_status = "✅" if codex.version != "0.0.0" else "❌"
        codex_features = sum(1 for s in codex.features.values() if s == FeatureStatus.AVAILABLE)
        lines.append(f"║ {codex_status} Codex CLI: {codex.version:<10} ({codex_features} features)          ║")

        # Gemini 状态
        gemini_status = "✅" if gemini.version != "0.0.0" else "❌"
        gemini_features = sum(1 for s in gemini.features.values() if s == FeatureStatus.AVAILABLE)
        lines.append(f"║ {gemini_status} Gemini CLI: {gemini.version:<10} ({gemini_features} features)         ║")

        lines.append("╚══════════════════════════════════════════════════════════╝")

        return "\n".join(lines)
