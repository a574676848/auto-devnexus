import argparse
import sys
import os
try:
    import utils
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import utils

def delete_issue(issue_key: str):
    """
    删除指定的 Jira 工单
    """
    response = utils.api_request(f'issue/{issue_key}', method='DELETE')
    
    if response['success'] and response['status'] in (200, 204):
        utils.log_to_agent({
            "success": True,
            "message": f"工单 {issue_key} 删除成功！"
        })
    else:
        utils.log_to_agent({
            "success": False,
            "error_type": "DELETE_ISSUE_FAILED",
            "message": f"无法删除工单 {issue_key}，请检查权限或关联子任务。",
            "details": response.get('message'),
            "raw_response": response.get('raw_error')
        })

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="删除 Jira 工单 (Jira 7.5.2)")
    parser.add_argument('--issue', type=str, required=True, help="工单编号")
    parser.add_argument('--workdir', type=str, required=True, help="工作目录(用户空间tmp路径)")
    
    args = parser.parse_args()
    utils.validate_workdir(args.workdir)
    utils.set_workdir(args.workdir)
    delete_issue(args.issue)
