# -*- coding: utf-8 -*-
"""
本地/私有 Git 仓库解析脚本
仅包含私有仓库特有逻辑（Git 错误分类、clone 鉴权），
通用解析能力由 repo_common 模块提供。
"""
import os
import sys
import argparse
import subprocess
import hashlib
import shutil
from typing import Dict

# 确保能导入同目录下的共用模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from repo_common import (
    emit_json, validate_workdir, process_cloned_repo,
    git_clone_with_retry, get_credential,
)

# === Git 错误关键词 ===
AUTH_FAILURE_KEYWORDS = [
    "Authentication failed",
    "could not read Username",
    "HTTP Basic: Access denied",
    "Invalid username or password",
    "remote: HTTP Basic:",
    "fatal: Authentication failed",
    "remote: Unauthorized",
    "The requested URL returned error: 401",
    "The requested URL returned error: 403",
]
NETWORK_ERROR_KEYWORDS = [
    "Could not resolve host",
    "Connection refused",
    "Connection timed out",
    "Network is unreachable",
    "No route to host",
    "Failed to connect",
    "SSL certificate problem",
]


def check_git_env() -> bool:
    """检查宿主机是否安装了 git 客户端"""
    try:
        subprocess.run(["git", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except Exception:
        return False


def classify_git_error(stderr: str, has_token: bool) -> Dict:
    """根据 Git stderr 输出精确分类错误类型，返回标准化的错误信息"""
    stderr_lower = stderr.lower()

    # 鉴权类错误
    for keyword in AUTH_FAILURE_KEYWORDS:
        if keyword.lower() in stderr_lower:
            if has_token:
                return {
                    "status": "error",
                    "reason": "auth_invalid",
                    "message": "当前 Git 凭证已失效或无权限访问该仓库，请提供新的有效令牌。"
                }
            else:
                return {
                    "status": "error",
                    "reason": "auth_required",
                    "message": "仓库需要身份验证，请提供 Git 访问令牌 (Personal Access Token)。"
                }

    # 网络类错误
    for keyword in NETWORK_ERROR_KEYWORDS:
        if keyword.lower() in stderr_lower:
            return {
                "status": "error",
                "reason": "network_error",
                "message": f"网络连接异常，无法访问仓库服务器。详情: {stderr.strip()}"
            }

    # 仓库不存在
    if "repository not found" in stderr_lower or "does not exist" in stderr_lower:
        return {
            "status": "error",
            "reason": "not_found",
            "message": "仓库地址不存在或无权限访问，请检查 URL 是否正确。"
        }

    # 兜底
    return {
        "status": "error",
        "reason": "git_error",
        "message": f"Git 操作失败: {stderr.strip()}"
    }


def pull_or_clone(repo_url: str, workdir: str, token: str = None) -> str:
    """拉取私有仓库代码，自动处理缓存和多方案凭据"""
    hash_id = hashlib.md5(repo_url.encode()).hexdigest()[:8]
    cache_dir = os.path.join(workdir, "temp_repo", f"local_{hash_id}")

    # 对于本地/私有仓库，如果已存在 .git 目录，尝试 pull
    if os.path.exists(os.path.join(cache_dir, ".git")):
        try:
            res = subprocess.run(
                ["git", "pull", "--depth", "1"],
                cwd=cache_dir, capture_output=True, text=True,
                timeout=60, encoding='utf-8'
            )
            if res.returncode == 0:
                return cache_dir
        except Exception:
            pass
        # Pull 失败则删掉重来 (Clone)
        shutil.rmtree(cache_dir, ignore_errors=True)

    # 调用共用模块的多方案 Clone 逻辑
    success = git_clone_with_retry(repo_url, cache_dir, token)
    
    if success:
        return cache_dir
    else:
        # 如果 Clone 失败，根据是否有 token 返回错误
        if not token:
            emit_json({"status": "error", "reason": "auth_required", 
                        "message": "该私有仓库需要身份验证，请提供访问令牌。"})
        else:
            emit_json({
                "status": "error", 
                "reason": "auth_invalid", 
                "message": "尝试了多种鉴权方式（Basic Auth 和 Header Auth）均由于凭证无效或权限不足而失败。请检查 Token 是否有效及权限范围。"
            })
        sys.exit(0)


def process_repository(repo_url: str, workdir: str, token: str):
    """本地/私有仓库解析主流程"""
    if not check_git_env():
        emit_json({"status": "error", "reason": "env_missing", "message": "宿主机未安装 git 客户端。"})
        return

    cache_dir = pull_or_clone(repo_url, workdir, token)
    if cache_dir:
        process_cloned_repo(cache_dir, repo_url, "Repository Directory Map")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DevNexus 本地/私有 Git 仓库解析工具")
    parser.add_argument("url", help="Git 仓库 URL")
    parser.add_argument("--workdir", required=True, help="temp_repo 输出目录（必填）")
    args = parser.parse_args()

    workdir = validate_workdir(args.workdir)
    # Token 注入：环境变量 > 凭证缓存（按域名匹配）> 无
    auth_token = os.getenv("GIT_TOKEN") or os.getenv("GITLAB_TOKEN")
    if not auth_token:
        # 从 URL 提取域名，尝试匹配凭证缓存
        url = args.url
        domain = ""
        if "://" in url:
            parts = url.split("://", 1)
            host_part = parts[1].split("/")[0]
            domain = host_part.split("@")[-1]  # 去掉 user@ 前缀
        if domain:
            auth_token = get_credential(domain)
    process_repository(args.url, workdir, auth_token)
