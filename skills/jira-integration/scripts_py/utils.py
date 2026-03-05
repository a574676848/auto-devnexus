import os
import sys
import json
import base64
import urllib.request
import urllib.error
import urllib.parse

# 默认域名不再硬编码，改为 None 或从环境变量读取
JIRA_DOMAIN = os.environ.get('JIRA_DOMAIN')
_global_workdir = None

# Jira 7.5.2 使用 rest/api/2
API_VERSION = "2"

def set_workdir(workdir: str):
    global _global_workdir
    _global_workdir = workdir

def get_credentials_file() -> str:
    """获取凭证文件的保存路径。如果设置了 workdir，则保存在 workdir 目录下。"""
    if _global_workdir:
        return os.path.join(_global_workdir, '.jira_credentials.json')
    return os.path.expanduser('~/.jira_credentials.json')

def validate_workdir(workdir: str):
    """验证工作目录。"""
    if not workdir or not workdir.strip():
        log_to_human("❌ 缺少必填参数: --workdir", "ERROR")
        log_to_agent({
            "success": False,
            "error_type": "MISSING_WORKDIR",
            "message": "必须提供 --workdir <用户工作空间tmp路径>"
        })
        sys.exit(1)
        
    workdir = os.path.abspath(workdir)
    if not os.path.isdir(workdir):
        try:
            os.makedirs(workdir, exist_ok=True)
        except Exception as e:
            log_to_human(f"无法创建工作目录 '{workdir}': {e}", "ERROR")
            log_to_agent({
                "success": False,
                "error_type": "INVALID_WORKDIR",
                "message": f"无法创建工作目录 '{workdir}': {e}"
            })
            sys.exit(1)
            
    return workdir

def log_to_agent(data: dict):
    """
    格式化并输出给大模型的纯净 JSON (Standard Output)
    必须保证 stdout 里没有人类看的啰嗦字符。
    """
    # 设置 UTF-8 编码
    sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(data, ensure_ascii=False, indent=2))
    sys.stdout.flush()

def log_to_human(message: str, msg_type: str = 'INFO'):
    """
    输出人类或错误诊断信息的日志 (Standard Error)
    不会干扰大模型的 JSON 解析。
    """
    print(f"[{msg_type}] {message}", file=sys.stderr)
    sys.stderr.flush()

def get_credentials():
    """从本地文件或环境变量获取凭证和域名"""
    user = os.environ.get('JIRA_USER')
    token = os.environ.get('JIRA_API_TOKEN')
    domain = os.environ.get('JIRA_DOMAIN')
    
    creds_file = get_credentials_file()
    
    # 优先使用文件凭证
    if os.path.exists(creds_file):
        try:
            with open(creds_file, 'r', encoding='utf-8') as f:
                creds = json.load(f)
                return (
                    creds.get('user', user), 
                    creds.get('token', token), 
                    creds.get('domain', domain)
                )
        except Exception as e:
            log_to_human(f"读取凭证文件失败: {e}", "WARNING")
            
    return user, token, domain

def check_auth():
    """验证必备的凭证和域名"""
    user, token, domain = get_credentials()
    if not user or not token or not domain:
        log_to_agent({
            "success": False,
            "error_type": "MISSING_CREDENTIALS",
            "message": f"缺少必要的配置信息（账号、Token 或 Jira 域名）。请首先调用 IntegrationPlugin.GetDefaultIntegrationAsync(4) 获取 ProjectManagement 类型的默认集成。如果未配置，再向用户询问这三项信息。最后调用 auth.py 存储到 {get_credentials_file()}。"
        })
        sys.exit(0)
    return user, token, domain

def get_base_url():
    """获取格式化后的基础域名"""
    _, _, domain = get_credentials()
    if not domain:
        return ""
    if not domain.startswith('http'):
        domain = f"https://{domain}"
    return domain.rstrip('/')

def get_browse_url(issue_key):
    """生成工单浏览器链接"""
    base = get_base_url()
    if not base:
        return f"/browse/{issue_key}"
    return f"{base}/browse/{issue_key}"

def parse_shared_payload(args):
    """共享的 Payload 解析逻辑，支持 --payload 和 --payload_file"""
    final_payload = None
    if args.payload_file:
        if not os.path.exists(args.payload_file):
             log_to_human(f"找不到 Payload 文件: {args.payload_file}", "ERROR")
             sys.exit(1)
        try:
            with open(args.payload_file, 'r', encoding='utf-8') as f:
                final_payload = json.load(f)
        except Exception as e:
            log_to_human(f"解析 Payload 文件里的 JSON 失败: {e}", "ERROR")
            sys.exit(1)
    elif args.payload:
        try:
            final_payload = json.loads(args.payload)
        except json.JSONDecodeError as e:
             log_to_human(f"--payload 参数未通过 JSON 格式校验: {e}", "ERROR")
             sys.exit(1)
    return final_payload

def api_request(endpoint: str, method: str = 'GET', data: dict = None, params: dict = None) -> dict:
    """
    零依赖的基础 HTTP 请求封装 (urllib)
    """
    user, token, domain = check_auth()
    
    # 自动修正路径：如果是以 /rest/api 开头则保留，否则自动加上版本号前缀
    if not endpoint.startswith('/rest/'):
        endpoint = f"/rest/api/{API_VERSION}/{endpoint.lstrip('/')}"
    
    base_url = get_base_url()
    url = endpoint if endpoint.startswith('http') else f"{base_url}{endpoint}"
    
    if params:
        query_string = urllib.parse.urlencode(params)
        url = f"{url}?{query_string}"
        
    auth_str = f"{user}:{token}"
    b64_auth = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')
    
    headers = {
        'Authorization': f'Basic {b64_auth}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    
    encoded_data = None
    if data is not None:
        encoded_data = json.dumps(data).encode('utf-8')
        
    req = urllib.request.Request(url, data=encoded_data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as response:
            response_body = response.read().decode('utf-8')
            try:
                parsed_data = json.loads(response_body) if response_body else {}
            except json.JSONDecodeError:
                parsed_data = {"raw_text": response_body}
                
            return {
                "success": True,
                "status": response.status,
                "data": parsed_data
            }
            
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        try:
            parsed_error = json.loads(error_body)
        except json.JSONDecodeError:
            parsed_error = {"raw_text": error_body}
            
        if e.code in (401, 403):
            log_to_agent({
                "success": False,
                "error_type": "UNAUTHORIZED",
                "message": "Jira 拒绝访问（状态码 401/403）。凭证无效或过期。请大模型请求新凭证并重新配置。"
            })
            sys.exit(0)
            
        log_to_human(f"API 调用异常: HTTP {e.code}", "ERROR")
        return {
            "success": False,
            "error_type": "JIRA_API_ERROR",
            "status": e.code,
            "message": parsed_error.get('errorMessages', [str(parsed_error)]) if isinstance(parsed_error, dict) else str(parsed_error),
            "raw_error": parsed_error
        }
        
    except urllib.error.URLError as e:
        log_to_human(f"网络连接异常: {e.reason}", "FATAL")
        return {
            "success": False,
            "error_type": "NETWORK_ERROR",
            "message": str(e.reason)
        }
    except Exception as e:
         log_to_human(f"运行时错误: {str(e)}", "FATAL")
         return {
            "success": False,
            "error_type": "RUNTIME_ERROR",
            "message": str(e)
        }
