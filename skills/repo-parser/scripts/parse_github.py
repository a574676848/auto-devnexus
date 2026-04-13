# -*- coding: utf-8 -*-
"""
GitHub 仓库解析脚本
仅包含 GitHub 特有逻辑（URL 解析、API 预检、clone），
通用解析能力由 repo_common 模块提供。
"""
import os
import sys
import json
import argparse
import urllib.request
import urllib.error
import hashlib
import subprocess
import shutil
from typing import Tuple

# 确保能导入同目录下的共用模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from repo_common import (
    emit_json, validate_workdir, process_cloned_repo,
    get_credential,
)

# GitHub API 仓库大小上限 (KB)
MAX_REPO_SIZE_KB = 500 * 1024  # 约 500MB


def get_repo_info_from_url(url: str) -> Tuple[str, str]:
    """从 GitHub 网址提取 owner 和 repo"""
    url = url.strip("/").replace(".git", "")
    parts = url.split("github.com/")
    if len(parts) < 2:
        return "", ""
    segments = parts[1].split("/")
    if len(segments) >= 2:
        return segments[0], segments[1]
    return "", ""


def check_repo_size(owner: str, repo: str, token: str = None) -> bool:
    """使用 GitHub API 预检仓库大小，支持 Token 访问私有仓库"""
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {"User-Agent": "DevNexus-Repo-Parser"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(api_url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            size_kb = data.get("size", 0)
            return size_kb <= MAX_REPO_SIZE_KB
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            emit_json({"status": "error", "reason": "auth_invalid",
                        "message": "GitHub Token 无效或已过期，请提供新的有效令牌。"})
            sys.exit(0)
        elif e.code == 404:
            if not token:
                emit_json({"status": "error", "reason": "auth_required",
                            "message": "该仓库可能是私有仓库，需要 GitHub Personal Access Token 才能访问。"})
            else:
                emit_json({"status": "error", "reason": "auth_invalid",
                            "message": "使用当前 Token 无法访问该仓库，可能 Token 权限不足或仓库不存在。"})
            sys.exit(0)
        return True  # 其他错误放过，尝试 clone
    except Exception:
        return True


def pull_or_clone(repo_url: str, workdir: str, token: str = None) -> str:
    """拉取 GitHub 仓库代码，自动处理缓存和 Token 鉴权"""
    hash_id = hashlib.md5(repo_url.encode()).hexdigest()[:8]
    cache_dir = os.path.join(workdir, "temp_repo", f"github_{hash_id}")

    # 组装带鉴权的 clone URL
    clone_url = repo_url
    if token and "://" in repo_url:
        parts = repo_url.split("://", 1)
        if "@" not in parts[1]:
            clone_url = f"{parts[0]}://oauth2:{token}@{parts[1]}"

    is_git_dir = os.path.exists(os.path.join(cache_dir, ".git"))

    try:
        if is_git_dir:
            res = subprocess.run(
                ["git", "pull", "--depth", "1"],
                cwd=cache_dir, capture_output=True, text=True,
                timeout=60, encoding='utf-8'
            )
            if res.returncode != 0:
                raise Exception(f"Pull failed: {res.stderr}")
        else:
            if os.path.exists(cache_dir):
                shutil.rmtree(cache_dir)
            os.makedirs(cache_dir, exist_ok=True)
            res = subprocess.run(
                ["git", "clone", "--depth", "1", clone_url, cache_dir],
                capture_output=True, text=True, timeout=120, encoding='utf-8'
            )
            if res.returncode != 0:
                err_msg = res.stderr.replace(token, "***") if token else res.stderr
                if "Authentication failed" in err_msg or "could not read Username" in err_msg:
                    reason = "auth_invalid" if token else "auth_required"
                    msg = ("Git 鉴权失败，当前 Token 无效或已过期，请提供新的有效令牌。"
                           if token else "该仓库需要身份验证，请提供 GitHub Personal Access Token。")
                    emit_json({"status": "error", "reason": reason, "message": msg})
                    sys.exit(0)
                raise Exception(f"Clone failed: {err_msg}")
    except Exception as e:
        if is_git_dir:
            shutil.rmtree(cache_dir, ignore_errors=True)
            return pull_or_clone(repo_url, workdir, token)  # 降级重试一次
        else:
            emit_json({"status": "error", "reason": "git_error",
                        "message": f"GitHub Clone 异常: {e}"})
            sys.exit(0)

    return cache_dir


def parse_github(repo_url: str, workdir: str, token: str = None):
    """GitHub 仓库解析入口"""
    owner, repo = get_repo_info_from_url(repo_url)
    if not owner or not repo:
        emit_json({"status": "error", "reason": "invalid_url",
                    "message": "缺少仓库地址参数或 URL 不合法。"})
        return

    # API 容量预检
    if not check_repo_size(owner, repo, token):
        emit_json({
            "status": "error", "reason": "too_large",
            "message": "仓库体积过大，当前 AI 窗口无法完整加载。超大工程的 RAG 支持正在开发中，敬请期待。"
        })
        return

    # Clone 并执行通用解析流程
    cache_dir = pull_or_clone(repo_url, workdir, token)
    if cache_dir:
        process_cloned_repo(cache_dir, f"{owner}/{repo}", "GitHub Repository Directory Map")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DevNexus GitHub 仓库解析工具")
    parser.add_argument("url", help="GitHub 仓库 URL")
    parser.add_argument("--workdir", required=True, help="temp_repo 输出目录（必填）")
    args = parser.parse_args()

    workdir = validate_workdir(args.workdir)
    # Token 注入：环境变量 > 凭证缓存 > 无
    auth_token = os.getenv("GITHUB_TOKEN") or get_credential("github.com")
    parse_github(args.url, workdir, auth_token)
