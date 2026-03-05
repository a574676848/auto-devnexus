import argparse
import sys
import os
import json
try:
    import utils
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import utils

def get_cache_file_path() -> str:
    filename = '.jira_all_users_dict.json'
    if utils._global_workdir:
        return os.path.join(utils._global_workdir, filename)
    return os.path.expanduser(f'~/{filename}')

def fetch_and_cache_users(keyword: str = "") -> list:
    """ Jira 7.x 搜索用户建议带上 username 关键词 """
    utils.log_to_human(f"正在从 Jira API (v2) 搜索用户 '{keyword}'...", "INFO")
    
    # params 适配 Jira 7.x
    params = {
        'username': keyword,
        'maxResults': 100
    }
    
    response = utils.api_request('user/search', method='GET', params=params)
    
    if not response['success']:
        utils.log_to_agent(response)
        sys.exit(0)
        
    cleaned = []
    for u in response['data']:
        cleaned.append({
            "name": u.get("name"),   # Jira 7.x 登录名，提单必填
            "key": u.get("key"),     # 内部 ID
            "displayName": u.get("displayName"),
            "emailAddress": u.get("emailAddress")
        })
    return cleaned

def search_users_dict(keyword: str = None, force_refresh: bool = False):
    """
    Jira 7.x 搜索用户，建议每次都实时查，因为 Server 版用户通常很多且接口限制翻页
    """
    if not keyword:
        utils.log_to_agent({"success": False, "message": "Jira 7.x 必须提供 --keyword (用户名、全名或邮箱) 进行搜索。"})
        return
        
    results = fetch_and_cache_users(keyword)
    utils.log_to_agent({
        "success": True,
        "results": results,
        "hint": "Jira 7.x 创建或指派工单时，请使用 `{'name': '这里返回的name'}`。"
    })

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="查询 Jira 7.5.2 用户字典")
    parser.add_argument('--keyword', type=str, required=True, help="搜索关键词")
    parser.add_argument('--refresh', action='store_true') # 保留参数兼容性
    parser.add_argument('--workdir', type=str, required=True, help="工作目录(用户空间tmp路径)")
    
    args = parser.parse_args()
    utils.validate_workdir(args.workdir)
    utils.set_workdir(args.workdir)
    search_users_dict(args.keyword, args.refresh)
    
