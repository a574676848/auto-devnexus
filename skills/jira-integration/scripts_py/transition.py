import argparse
import sys
import os
import json
try:
    import utils
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import utils

def list_transitions(issue_key: str):
    """
    获取工单当前可用的状态流转动作
    """
    response = utils.api_request(f'issue/{issue_key}/transitions', method='GET')
    
    if not response['success']:
        utils.log_to_agent(response)
        sys.exit(0)
        
    transitions = []
    for t in response['data'].get('transitions', []):
        transitions.append({
            "id": t.get('id'),
            "name": t.get('name'),
            "to_status": t.get('to', {}).get('name')
        })
        
    utils.log_to_agent({
        "success": True,
        "issue_key": issue_key,
        "available_transitions": transitions,
        "hint": "根据 ID 选择一个 transition 进行流转。调用时请使用 `--id <TransitionID>`。"
    })

def do_transition(issue_key: str, transition_id: str, fields: dict = None):
    """
    执行工单流转
    """
    payload = {
        "transition": {
            "id": transition_id
        }
    }
    if fields:
        payload["fields"] = fields
        
    response = utils.api_request(f'issue/{issue_key}/transitions', method='POST', data=payload)
    
    if response['success'] and response['status'] in (200, 204):
        utils.log_to_agent({
            "success": True,
            "message": f"工单 {issue_key} 状态成功流转到目标状态。"
        })
    else:
        utils.log_to_agent({
            "success": False,
            "error_type": "TRANSITION_FAILED",
            "message": f"状态流转失败。ID {transition_id} 可能已失效或缺少必填字段。",
            "details": response.get('message'),
            "raw_response": response.get('raw_error')
        })

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Jira 7.5.2 工单状态流转控制")
    parser.add_argument('--issue', type=str, required=True, help="工单编号")
    parser.add_argument('--list', action='store_true', help="列出当前可用的流转操作")
    parser.add_argument('--id', type=str, help="要执行的 Transition ID")
    parser.add_argument('--fields', type=str, help="流转时需要填写的字段 (JSON)")
    parser.add_argument('--workdir', type=str, required=True, help="工作目录(用户空间tmp路径)")
    
    args = parser.parse_args()
    utils.validate_workdir(args.workdir)
    utils.set_workdir(args.workdir)
    
    if args.list:
        list_transitions(args.issue)
    elif args.id:
        extra_fields = json.loads(args.fields) if args.fields else None
        do_transition(args.issue, args.id, extra_fields)
    else:
        parser.print_help()
