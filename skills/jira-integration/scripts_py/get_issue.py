import argparse
import sys
import os
try:
    import utils
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import utils

def get_issue(issue_key: str):
    """
    获取单个工单的详细信息
    """
    response = utils.api_request(f'issue/{issue_key}', method='GET')
    
    if not response['success']:
        utils.log_to_agent(response)
        sys.exit(0)
        
    issue = response['data']
    fields = issue.get('fields', {})
    
    # 提取核心信息给 AI
    clean_data = {
        "key": issue.get('key'),
        "summary": fields.get('summary'),
        "description": fields.get('description'),
        "status": fields.get('status', {}).get('name'),
        "assignee": fields.get('assignee', {}).get('displayName') if fields.get('assignee') else "Unassigned",
        "reporter": fields.get('reporter', {}).get('displayName'),
        "priority": fields.get('priority', {}).get('name') if fields.get('priority') else None,
        "issuetype": fields.get('issuetype', {}).get('name'),
        "created": fields.get('created'),
        "updated": fields.get('updated'),
        "link": utils.get_browse_url(issue.get('key'))
    }
    
    # 包含所有自定义字段，以便 AI 能够看到它们的值
    custom_fields = {k: v for k, v in fields.items() if k.startswith('customfield_')}
    clean_data['custom_fields'] = custom_fields
    
    utils.log_to_agent({
        "success": True,
        "issue": clean_data
    })

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="查看 Jira 7.5.2 单个工单详情")
    parser.add_argument('--issue', type=str, required=True, help="工单编号 (如 TEST-101)")
    parser.add_argument('--workdir', type=str, required=True, help="工作目录(用户空间tmp路径)")
    
    args = parser.parse_args()
    utils.validate_workdir(args.workdir)
    utils.set_workdir(args.workdir)
    get_issue(args.issue)
