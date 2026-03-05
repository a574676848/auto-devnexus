import argparse
import sys
import json
import os
try:
    import utils
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import utils

def create_issue(payload: dict):
    """
    接收组装好的 payload，发送提单请求给 Jira API
    """
    response = utils.api_request('issue', method='POST', data=payload)
    
    if response['success']:
        # Jira 7.x 返回 id, key 和 self
        utils.log_to_agent({
            "success": True,
            "message": f"工单创建成功！",
            "issue_key": response['data'].get('key'),
            "issue_id": response['data'].get('id'),
            "link": utils.get_browse_url(response['data'].get('key'))
        })
    else:
        hint_msg = "工单创建失败。请检查 Jira 返回的详细字段错误提示。"
        
        if response.get('status') == 400:
             hint_msg += (
                 "这通常是因为 payload 结构有误或填写了无效的 option 值。 "
                 "对于 Jira 7.5.x，账号映射使用的是 name 而非 accountId。 "
                 "【👉 纠错指南】：1. 调用 schema.py 并 refresh。 2. 检查人名映射。"
             )
             
        utils.log_to_agent({
            "success": False,
            "error_type": "CREATE_ISSUE_FAILED",
            "message": hint_msg,
            "details": response.get('message'),
            "raw_response": response.get('raw_error')
        })

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="在 Jira 里创建新工单 (Jira 7.5.2)")
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--payload', type=str, help="JSON 字符串 payload")
    group.add_argument('--payload_file', type=str, help="JSON payload 文件")
    parser.add_argument('--workdir', type=str, required=True, help="工作目录(用户空间tmp路径)")
    
    args = parser.parse_args()
    utils.validate_workdir(args.workdir)
    utils.set_workdir(args.workdir)
    final_payload = utils.parse_shared_payload(args)
             
    create_issue(final_payload)
