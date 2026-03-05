import argparse
import sys
import os
import json
try:
    import utils
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import utils

def get_cache_file_path(project_key: str, issuetype_name: str) -> str:
    safe_type_name = "".join([c if c.isalnum() else "_" for c in issuetype_name])
    filename = f'.jira_schema_cache_{project_key.upper()}_{safe_type_name}.json'
    if utils._global_workdir:
        return os.path.join(utils._global_workdir, filename)
    return os.path.expanduser(f'~/{filename}')

def load_from_cache(cache_path: str):
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return None

def save_to_cache(cache_path: str, data: dict):
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        utils.log_to_human(f"⚠️ 无法保存 Schema 缓存: {e}", "WARNING")

def get_issue_schema(project_key: str, issuetype_name: str, force_refresh: bool = False):
    """
    针对 Jira 7.5.2 获取打单元数据 (createmeta)
    """
    cache_path = get_cache_file_path(project_key, issuetype_name)
    
    if not force_refresh:
        cached_data = load_from_cache(cache_path)
        if cached_data:
            cached_data["hint"] += f" (来自本地缓存 {cache_path})"
            utils.log_to_agent(cached_data)
            return

    utils.log_to_human(f"正在从 Jira API (v2) 拉取 {project_key}-{issuetype_name} 的 Schema...", "INFO")
    
    params = {
        'projectKeys': project_key,
        'issuetypeNames': issuetype_name,
        'expand': 'projects.issuetypes.fields'
    }
    
    response = utils.api_request('issue/createmeta', method='GET', params=params)
    
    if not response['success']:
        utils.log_to_agent(response)
        sys.exit(0)
        
    projects = response['data'].get('projects', [])
    if not projects:
        utils.log_to_agent({"success": False, "message": f"未找到项目: {project_key}"})
        sys.exit(0)
        
    project = projects[0]
    issuetypes = project.get('issuetypes', [])
    # Jira 7.x 有时会返回issuetype ID匹配但不匹配名称，需过滤
    target_type = next((it for it in issuetypes if it.get('name') == issuetype_name), None)
    if not target_type:
         # 尝试模糊匹配或取第一个
         target_type = issuetypes[0] if issuetypes else None

    if not target_type:
         utils.log_to_agent({"success": False, "message": f"未找到工单类型: {issuetype_name}"})
         sys.exit(0)
         
    fields = target_type.get('fields', {})
    required_fields = {}
    optional_fields = {}
    
    for field_key, field_def in fields.items():
        is_required = field_def.get('required', False)
        clean_def = {
            "name": field_def.get('name'),
            "type": field_def.get('schema', {}).get('type'),
            "operations": field_def.get('operations', [])
        }
        if 'allowedValues' in field_def:
            clean_def['allowedValues'] = [{"value": opt.get('value') or opt.get('name'), "id": opt.get('id')} for opt in field_def['allowedValues'] if isinstance(opt, dict)]
        
        if is_required:
            required_fields[field_key] = clean_def
        else:
            optional_fields[field_key] = clean_def
            
    pruned_result = {
        "success": True,
        "hint": "Jira 7.5.2 Schema。注意：人员字段请使用 `{'name': '用户名'}`。",
        "required_fields": required_fields,
        "optional_fields": optional_fields
    }
    
    save_to_cache(cache_path, pruned_result)
    utils.log_to_agent(pruned_result)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="获取 Jira 7.5.2 打单 Schema")
    parser.add_argument('--project', type=str, required=True)
    parser.add_argument('--issuetype', type=str, required=True)
    parser.add_argument('--refresh', action='store_true')
    parser.add_argument('--workdir', type=str, required=True, help="工作目录(用户空间tmp路径)")
    
    args = parser.parse_args()
    utils.validate_workdir(args.workdir)
    utils.set_workdir(args.workdir)
    get_issue_schema(args.project, args.issuetype, args.refresh)
