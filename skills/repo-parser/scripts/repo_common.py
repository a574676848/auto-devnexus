# -*- coding: utf-8 -*-
"""
Repo-Parser 共用模块
提供常量定义、工具函数和核心解析逻辑，供 parse_github.py 和 parse_local_git.py 共用。
"""
import os
import sys
import json
import subprocess
import shutil
import hashlib
from typing import Dict, List, Tuple, Optional
from collections import Counter
from datetime import datetime

# === 凭证缓存路径（用户主目录，与技能目录分离） ===
REPO_PARSER_HOME = os.path.join(os.path.expanduser("~"), ".repo-parser")
CREDENTIAL_CACHE_FILE = os.path.join(REPO_PARSER_HOME, "credential_cache.json")

# === 阈值配置 ===
MAX_TOTAL_FILE_BYTES = 500 * 1024 * 1024  # 熔断大小 500MB
MAX_PART_SIZE_BYTES = 500 * 1024         # 每片最大约 500KB
MAX_SINGLE_FILE_BYTES = 3 * 1024 * 1024  # 单文件上限 3MB

# === 忽略规则 ===
IGNORED_DIRS = {
    ".git", ".github", ".gitlab", "bin", "obj", "node_modules", "dist", "out",
    "venv", ".vs", ".idea", "__pycache__", "build", ".husky", ".venv",
    "coverage", ".nyc_output", ".pytest_cache", ".mypy_cache", "packages",
    "TestResults", ".angular", ".next", ".nuxt", "target", ".gradle",
}
IGNORED_EXTS = {
    # 图像/流媒体
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp", ".bmp", ".tiff",
    ".mp4", ".mp3", ".wav", ".avi", ".mov", ".flac", ".ogg",
    # 字体
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    # 档案/打包
    ".zip", ".tar", ".gz", ".rar", ".7z", ".pdf", ".iso", ".apk", ".ipa", ".nupkg",
    # 编译或二进制
    ".exe", ".dll", ".so", ".dylib", ".pdb", ".bin", ".class", ".o", ".a", ".lib",
    ".wasm",
    # 其他杂项
    ".lock", ".suo", ".user", ".pyc", ".pyo", ".DS_Store", ".map",
}
IGNORED_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "composer.lock",
    "Cargo.lock", "Gemfile.lock", "poetry.lock", ".DS_Store", "Thumbs.db",
}

# === 语言映射表（扩展名 → Markdown 代码块标识）===
EXT_TO_LANG = {
    ".py": "python", ".pyw": "python",
    ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".tsx": "tsx", ".jsx": "jsx",
    ".cs": "csharp",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin", ".kts": "kotlin",
    ".scala": "scala",
    ".c": "c", ".h": "c",
    ".cpp": "cpp", ".cxx": "cpp", ".cc": "cpp", ".hpp": "cpp",
    ".html": "html", ".htm": "html",
    ".css": "css", ".scss": "scss", ".sass": "sass", ".less": "less",
    ".json": "json",
    ".xml": "xml", ".xsl": "xml", ".xsd": "xml",
    ".yaml": "yaml", ".yml": "yaml",
    ".toml": "toml",
    ".ini": "ini", ".cfg": "ini",
    ".sql": "sql",
    ".sh": "bash", ".bash": "bash", ".zsh": "bash",
    ".ps1": "powershell", ".psm1": "powershell",
    ".bat": "batch", ".cmd": "batch",
    ".md": "markdown",
    ".r": "r", ".R": "r",
    ".dart": "dart",
    ".lua": "lua",
    ".pl": "perl", ".pm": "perl",
    ".ex": "elixir", ".exs": "elixir",
    ".erl": "erlang",
    ".hs": "haskell",
    ".vue": "vue",
    ".svelte": "svelte",
    ".tf": "hcl", ".hcl": "hcl",
    ".proto": "protobuf",
    ".graphql": "graphql", ".gql": "graphql",
    ".razor": "razor",
    ".dockerfile": "dockerfile",
}
# 特殊文件名 → 语言映射
FILENAME_TO_LANG = {
    "Dockerfile": "dockerfile",
    "Makefile": "makefile",
    "CMakeLists.txt": "cmake",
    "Jenkinsfile": "groovy",
    "Vagrantfile": "ruby",
    ".gitignore": "gitignore",
    ".env": "dotenv",
    ".editorconfig": "ini",
}

# === 重要文件优先级（数字越小越靠前）===
PRIORITY_PATTERNS = {
    "README": 1, "readme": 1,
    "CHANGELOG": 2, "changelog": 2,
    "LICENSE": 3, "license": 3,
    ".csproj": 10, ".fsproj": 10, ".vbproj": 10, ".sln": 10,
    "package.json": 10, "tsconfig.json": 11,
    "pyproject.toml": 10, "setup.py": 10, "setup.cfg": 10, "requirements.txt": 11,
    "Cargo.toml": 10,
    "go.mod": 10,
    "pom.xml": 10, "build.gradle": 10,
    "Gemfile": 10,
    "Dockerfile": 12, "docker-compose": 12,
    "Makefile": 13, "CMakeLists.txt": 13,
    ".env.example": 14,
    "appsettings": 15, "config": 15,
    "Program.cs": 16, "Startup.cs": 16, "main.": 16,
    "index.": 17, "app.": 17, "App.": 17,
}

# === 项目类型检测特征文件 ===
PROJECT_SIGNATURES = {
    ".csproj": (".NET (C#)", "🟣"),
    ".fsproj": (".NET (F#)", "🟣"),
    ".sln": (".NET Solution", "🟣"),
    "package.json": ("Node.js / JavaScript", "🟢"),
    "tsconfig.json": ("TypeScript", "🔵"),
    "pyproject.toml": ("Python", "🐍"),
    "setup.py": ("Python", "🐍"),
    "requirements.txt": ("Python", "🐍"),
    "Cargo.toml": ("Rust", "🦀"),
    "go.mod": ("Go", "🔵"),
    "pom.xml": ("Java (Maven)", "☕"),
    "build.gradle": ("Java/Kotlin (Gradle)", "☕"),
    "Gemfile": ("Ruby", "💎"),
    "composer.json": ("PHP", "🐘"),
    "pubspec.yaml": ("Dart/Flutter", "🎯"),
    "Package.swift": ("Swift", "🍎"),
    "Dockerfile": ("Docker 容器化", "🐳"),
    "docker-compose.yml": ("Docker Compose", "🐳"),
    "docker-compose.yaml": ("Docker Compose", "🐳"),
}


# ============================================================
# 凭证管理（读写 %USERPROFILE%\.repo-parser\credential_cache.json）
# ============================================================

def _ensure_repo_parser_home():
    """确保 ~/.repo-parser 目录存在"""
    os.makedirs(REPO_PARSER_HOME, exist_ok=True)


def load_credentials() -> Dict[str, str]:
    """
    加载所有域名的凭证缓存，返回 {domain: token} 字典。
    文件不存在时返回空字典。
    """
    if not os.path.exists(CREDENTIAL_CACHE_FILE):
        return {}
    try:
        with open(CREDENTIAL_CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        result = {}
        for cred in data.get("credentials", []):
            domain = cred.get("domain", "")
            token = cred.get("token", "")
            if domain and token:
                result[domain] = token
        return result
    except Exception:
        return {}


def get_credential(domain: str) -> Optional[str]:
    """根据域名获取缓存凭证"""
    creds = load_credentials()
    return creds.get(domain)


def save_credential(domain: str, token: str, note: str = ""):
    """保存或更新凭证到缓存（追加或覆盖同名域名）"""
    _ensure_repo_parser_home()
    data = {"credentials": []}
    if os.path.exists(CREDENTIAL_CACHE_FILE):
        try:
            with open(CREDENTIAL_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {"credentials": []}

    # 更新已存在的域名记录，或追加新的
    found = False
    for cred in data["credentials"]:
        if cred.get("domain") == domain:
            cred["token"] = token
            cred["note"] = note or cred.get("note", "")
            cred["updated_at"] = datetime.now().astimezone().isoformat()
            found = True
            break
    if not found:
        data["credentials"].append({
            "domain": domain,
            "token": token,
            "note": note,
            "updated_at": datetime.now().astimezone().isoformat()
        })

    with open(CREDENTIAL_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ============================================================
# 工具函数
# ============================================================

def emit_json(data: Dict):
    """标准 JSON 输出（供 AI 读取提取参数）"""
    sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(data, ensure_ascii=False))


def get_lang_for_file(filename: str) -> str:
    """根据文件名/扩展名获取 Markdown 代码块语言标识"""
    if filename in FILENAME_TO_LANG:
        return FILENAME_TO_LANG[filename]
    ext = os.path.splitext(filename)[1].lower()
    return EXT_TO_LANG.get(ext, "")


def get_file_priority(rel_path: str) -> int:
    """计算文件的优先级分数，数字越小越优先"""
    filename = os.path.basename(rel_path)
    for pattern, priority in PRIORITY_PATTERNS.items():
        if pattern in filename or pattern in rel_path:
            return priority
    return 100  # 默认普通优先级


def detect_project_types(filenames: set) -> List[Tuple[str, str]]:
    """基于特征文件检测项目类型，返回 [(类型名, emoji), ...]"""
    detected = []
    seen_types = set()
    for filename, (proj_type, emoji) in PROJECT_SIGNATURES.items():
        if filename in filenames and proj_type not in seen_types:
            detected.append((proj_type, emoji))
            seen_types.add(proj_type)
    return detected


def count_lines(filepath: str) -> int:
    """快速统计文件行数"""
    try:
        with open(filepath, "rb") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def format_size(size_bytes: int) -> str:
    """将字节大小格式化为人类可读（KB/MB）"""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f}MB"


def validate_workdir(workdir: str):
    """
    验证并准备工作目录。
    workdir 为必填参数，如果路径不合法或无法创建则报错退出。
    """
    if not workdir or not workdir.strip():
        msg = (
            "❌ 缺少必填参数: --workdir\n\n"
            "原因: 该脚本的代码下载目录(B)必须与脚本存项目目录(A)分离。\n"
            "解决: 请传入用户工作空间的 tmp 路径。例如:\n"
            "      --workdir \"E:\\zbg\\DevNexus-AI\\src\\backend\\DevNexus.ApiService\\wwwroot\\tmp\\user-uuid\""
        )
        emit_json({
            "status": "error",
            "reason": "missing_workdir",
            "message": msg
        })
        sys.exit(1)

    workdir = os.path.abspath(workdir)

    if not os.path.isdir(workdir):
        try:
            os.makedirs(workdir, exist_ok=True)
        except OSError as e:
            emit_json({
                "status": "error",
                "reason": "invalid_workdir",
                "message": f"无法创建工作目录 '{workdir}': {e}"
            })
            sys.exit(1)

    return workdir


# ============================================================
# 核心解析逻辑
# ============================================================

def _ensure_git_suffix(url: str) -> str:
    """确保 HTTPS/HTTP 类型的仓库 URL 以 .git 结尾（GitLab 鉴权要求）"""
    if "://" in url and not url.rstrip("/").endswith(".git"):
        return url.rstrip("/") + ".git"
    return url


def git_clone_with_retry(repo_url: str, cache_dir: str, token: str = None) -> bool:
    """
    通用 Git Clone 逻辑，支持多方案鉴权尝试：
    1. 方案 A: 传统的 Basic Auth (oauth2:token@url.git)
    2. 方案 B: 现代 Header Auth (http.extraHeader="PRIVATE-TOKEN: <token>")
    """
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
    os.makedirs(cache_dir, exist_ok=True)

    # 统一确保 .git 后缀（GitLab 对不带后缀的 URL 不接受 oauth2 鉴权）
    clone_url = _ensure_git_suffix(repo_url)

    # --- 尝试方案 A: Basic Auth ---
    if token and "://" in clone_url:
        parts = clone_url.split("://", 1)
        if "@" not in parts[1]:
            clone_url = f"{parts[0]}://oauth2:{token}@{parts[1]}"

    cmd_a = ["git", "clone", "--depth", "1", clone_url, cache_dir]
    res_a = subprocess.run(cmd_a, capture_output=True, text=True, timeout=120, encoding='utf-8')

    if res_a.returncode == 0:
        return True

    # 如果是网络等客观错误，直接失败
    stderr_lower = res_a.stderr.lower()
    if "could not resolve host" in stderr_lower or "timed out" in stderr_lower:
        return False

    # --- 尝试方案 B: Header Auth (PRIVATE-TOKEN) ---
    if token:
        shutil.rmtree(cache_dir)
        os.makedirs(cache_dir)
        # 注意：PRIVATE-TOKEN 是 GitLab 常用 Header，如果是 GitHub 则通常不需要此步
        header_config = ["-c", f"http.extraHeader=PRIVATE-TOKEN: {token}"]
        cmd_b = ["git"] + header_config + ["clone", "--depth", "1", _ensure_git_suffix(repo_url), cache_dir]
        res_b = subprocess.run(cmd_b, capture_output=True, text=True, timeout=120, encoding='utf-8')
        if res_b.returncode == 0:
            return True

    return False

def build_tree_and_files(src_dir: str, tree_title: str = "Repository Directory Map") -> tuple:
    """
    遍历目录，生成增强型树状纲要（含行数/大小/项目类型检测），
    并返回按优先级排序的有效文件路径列表。

    返回: (tree_str, valid_files, total_size)
        - valid_files: [(abs_path, rel_path, size, line_count), ...] 已按优先级排序
    """
    tree_lines = []
    valid_files = []
    total_size = 0
    all_filenames = set()
    lang_counter = Counter()

    for root, dirs, files in os.walk(src_dir):
        # 过滤并排序子目录
        dirs[:] = sorted([d for d in dirs if d not in IGNORED_DIRS and not d.startswith('.')])

        rel_path = os.path.relpath(root, src_dir)
        level = 0 if rel_path == "." else rel_path.count(os.sep) + 1
        indent = "  " * level

        if rel_path != ".":
            tree_lines.append(f"{indent}📁 {os.path.basename(root)}/")

        for f in sorted(files):
            ext = os.path.splitext(f)[1].lower()
            if ext in IGNORED_EXTS or f.startswith('.') or f in IGNORED_FILES:
                continue

            file_path = os.path.join(root, f)
            try:
                size = os.path.getsize(file_path)
                if size > MAX_SINGLE_FILE_BYTES:
                    continue
                lines = count_lines(file_path)
                total_size += size
                file_rel = os.path.relpath(file_path, src_dir)
                valid_files.append((file_path, file_rel, size, lines))
                all_filenames.add(f)

                lang = get_lang_for_file(f)
                if lang:
                    lang_counter[lang] += 1

                tree_lines.append(f"{indent}  📄 {f} ({lines}行, {format_size(size)})")
            except OSError:
                pass

    # 检测项目类型
    project_types = detect_project_types(all_filenames)

    # 构建增强版目录树头部
    header_lines = [f"# {tree_title}\n"]
    if project_types:
        type_str = " | ".join([f"{emoji} {name}" for name, emoji in project_types])
        header_lines.append(f"**检测到的技术栈**: {type_str}\n")
    if lang_counter:
        top_langs = lang_counter.most_common(8)
        lang_str = ", ".join([f"{lang}({count})" for lang, count in top_langs])
        header_lines.append(f"**主要语言分布**: {lang_str}\n")
    header_lines.append(f"**文件总计**: {len(valid_files)} 个文件, {format_size(total_size)}\n")
    header_lines.append("---\n")

    full_tree = "\n".join(header_lines + tree_lines)

    # 按优先级排序文件列表（重要文件靠前）
    valid_files.sort(key=lambda x: get_file_priority(x[1]))

    return full_tree, valid_files, total_size


def write_output_files(cache_dir: str, files: list, repo_label: str) -> Dict:
    """
    将文件列表分卷切分写入 Markdown 文件，并返回标准 JSON 输出。
    这是两个脚本共享的最终输出逻辑。

    参数:
        cache_dir: 仓库缓存目录（输出文件也写在此处）
        files: [(abs_path, rel_path, size, line_count), ...] 已排序
        repo_label: 仓库标签（用于 JSON 输出的 repo 字段）
    """
    tree_str, _, total_size = None, None, None
    # 重新计算 total_size（因为调用方可能已做过熔断检查）
    total_size = sum(f[2] for f in files)

    # 分卷切分读取（带语言感知代码块）
    output_files = []
    part_idx = 1
    current_chunk = []
    current_size = 0
    total_lines = 0

    for abs_path, rel_path, file_size, line_count in files:
        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                # 剔除明显的 Null Bytes 二进制特征
                if '\x00' in content:
                    continue

                lang = get_lang_for_file(os.path.basename(abs_path))
                lang_tag = lang if lang else ""
                file_md = f"\n\n### File: {rel_path} ({line_count}行, {format_size(file_size)})\n```{lang_tag}\n{content}\n```\n"
                chunk_bytes_len = len(file_md.encode('utf-8'))

                current_chunk.append(file_md)
                current_size += chunk_bytes_len
                total_lines += line_count

                if current_size >= MAX_PART_SIZE_BYTES:
                    part_name = os.path.join(cache_dir, f"REPO_CONTENT_PART_{part_idx}.md")
                    with open(part_name, "w", encoding="utf-8") as out_f:
                        out_f.write("".join(current_chunk))
                    output_files.append(part_name)

                    part_idx += 1
                    current_chunk = []
                    current_size = 0
        except Exception:
            continue

    # 写入最后一块
    if current_chunk:
        part_name = os.path.join(cache_dir, f"REPO_CONTENT_PART_{part_idx}.md")
        with open(part_name, "w", encoding="utf-8") as out_f:
            out_f.write("".join(current_chunk))
        output_files.append(part_name)

    return {
        "status": "success",
        "repo": repo_label,
        "tree_file": os.path.join(cache_dir, "REPO_TREE_OUTPUT.md"),
        "output_files": output_files,
        "total_files": len(files),
        "total_lines": total_lines,
        "total_size": format_size(total_size),
        "message": f"解析成功。提取 {len(files)} 个文件 ({total_lines} 行)。请先阅读 tree_file。"
    }


def process_cloned_repo(cache_dir: str, repo_label: str, tree_title: str):
    """
    通用的仓库解析处理流程（clone 之后调用）：
    构建目录树 → 尺寸熔断检查 → 分卷切分 → 输出 JSON。
    """
    tree_str, files, total_size = build_tree_and_files(cache_dir, tree_title)

    # 尺寸熔断
    if total_size > MAX_TOTAL_FILE_BYTES:
        emit_json({
            "status": "error",
            "reason": "too_large",
            "message": "仓库体积过大，当前 AI 窗口无法完整加载。超大工程的 RAG 支持正在开发中，请使用局部问题代替全库审计。"
        })
        return

    # 保存目录树文件
    tree_file = os.path.join(cache_dir, "REPO_TREE_OUTPUT.md")
    with open(tree_file, "w", encoding="utf-8") as f:
        f.write(tree_str)
        f.write("\n\n---\n*Note: Use this overview to understand architecture. Read specific part files for contents.*\n")

    # 分卷切分并输出最终 JSON
    result = write_output_files(cache_dir, files, repo_label)
    emit_json(result)
