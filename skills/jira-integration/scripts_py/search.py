import argparse
import sys
import os
try:
    import utils
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import utils

def search_issues(jql: str, max_results: int = 50):
    """
    通过 JQL 查询 Jira 并只返回核心数据
    """
    params = {
        'jql': jql,
        'maxResults': max_results,
        'fields': 'summary,status,assignee,priority,created'
    }
    
    # utils 内部会自动补全 /rest/api/2/search
    response = utils.api_request('search', method='GET', params=params)
    
    if not response['success']:
        utils.log_to_agent(response)
        sys.exit(0)
        
    data = response['data']
    total = data.get('total', 0)
    issues_raw = data.get('issues', [])
    
    clean_issues = []
    
    for issue in issues_raw:
        fields = issue.get('fields', {})
        assignee = fields.get('assignee')
        status = fields.get('status')
        priority = fields.get('priority')
        
        clean_issue = {
            "key": issue.get('key'),
            "summary": fields.get('summary'),
            "status": status.get('name') if status else "Unknown",
            "assignee": assignee.get('displayName') if assignee else "Unassigned",
            "priority": priority.get('name') if priority else "Default",
            "created": fields.get('created'),
            "link": utils.get_browse_url(issue.get('key'))
        }
        clean_issues.append(clean_issue)
        
    utils.log_to_agent({
        "success": True,
        "total_matches": total,
        "returned_count": len(clean_issues),
        "issues": clean_issues
    })

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="通过 JQL 搜索工单 (Jira 7.5.2)")
    parser.add_argument('--jql', type=str, required=True, help="标准的 JQL 查询语句")
    parser.add_argument('--max', type=int, default=50, help="最大返回数量 (默认 50)")
    parser.add_argument('--workdir', type=str, required=True, help="工作目录(用户空间tmp路径)")
    
    args = parser.parse_args()
    utils.validate_workdir(args.workdir)
    utils.set_workdir(args.workdir)
    search_issues(args.jql, args.max)
