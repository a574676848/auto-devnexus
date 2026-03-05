import argparse
import sys
import json
import os
try:
    import utils
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import utils

def update_issue(issue_key: str, payload: dict):
    """
    接收组装好的局部更新 payload，发送修改请求
    """
    response = utils.api_request(f'issue/{issue_key}', method='PUT', data=payload)
    
    if response['success'] and response['status'] in (200, 204):
        utils.log_to_agent({
            "success": True,
            "message": f"工单 {issue_key} 更新成功！"
        })
    else:
        hint_msg = f"工单 {issue_key} 更新失败。"
        if response.get('status') == 400:
            hint_msg += "请检查 payload 格式或流程限制。Jira 7.x 中人员字段请使用 name 或 key 属性。"
            
        utils.log_to_agent({
            "success": False,
            "error_type": "UPDATE_ISSUE_FAILED",
            "message": hint_msg,
            "details": response.get('message'),
            "raw_response": response.get('raw_error')
        })

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="更新 Jira 工单字段 (Jira 7.5.2)")
    parser.add_argument('--issue', type=str, required=True, help="工单编号")
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--payload', type=str, help="JSON payload")
    group.add_argument('--payload_file', type=str, help="从文件读取 payload")
    parser.add_argument('--workdir', type=str, required=True, help="工作目录(用户空间tmp路径)")
    
    args = parser.parse_args()
    utils.validate_workdir(args.workdir)
    utils.set_workdir(args.workdir)
    final_payload = utils.parse_shared_payload(args)
             
    update_issue(args.issue, final_payload)
