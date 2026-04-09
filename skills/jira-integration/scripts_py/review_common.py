import os
import re
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import utils
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import utils


def load_json(path: str) -> Any:
    return utils.read_json_utf8(path)


def save_json(path: str, data: Any):
    utils.write_json_utf8(path, data)


def save_text(path: str, content: str):
    utils.write_text_utf8(path, content)


def now_compact() -> str:
    return datetime.now().strftime('%Y%m%d-%H%M%S')


def review_output_path(workdir: str, issue_key: str, suffix: str, ext: str) -> str:
    filename = f'{issue_key}-{suffix}-{now_compact()}.{ext}'
    return utils.get_work_file_path(workdir, filename)


def bundle_path(workdir: str, issue_key: str) -> str:
    return utils.get_work_file_path(workdir, f'review_bundle_{issue_key}.json')


def refs_path(workdir: str, issue_key: str) -> str:
    return utils.get_work_file_path(workdir, f'review_refs_{issue_key}.json')


def analysis_path(workdir: str, issue_key: str) -> str:
    return utils.get_work_file_path(workdir, f'review_analysis_{issue_key}.json')


def get_issue_type(issue: Dict[str, Any]) -> str:
    return (((issue.get('fields') or {}).get('issuetype') or {}).get('name')) or 'Unknown'


def get_issue_status(issue: Dict[str, Any]) -> str:
    return (((issue.get('fields') or {}).get('status') or {}).get('name')) or 'Unknown'


def get_issue_assignee(issue: Dict[str, Any]) -> str:
    assignee = ((issue.get('fields') or {}).get('assignee')) or {}
    return assignee.get('displayName') or assignee.get('name') or 'Unassigned'


def get_custom_field_by_name(issue: Dict[str, Any], field_map: Dict[str, str], field_name: str) -> Any:
    field_id = field_map.get(field_name)
    if not field_id:
        return None
    return ((issue.get('fields') or {}).get(field_id))


def normalize_hours(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    match = re.search(r'-?\d+(?:\.\d+)?', text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except Exception:
        return None


def worklogs_of(issue: Dict[str, Any]) -> List[Dict[str, Any]]:
    return (((issue.get('fields') or {}).get('worklog') or {}).get('worklogs')) or []


def comments_of(issue: Dict[str, Any]) -> List[Dict[str, Any]]:
    return (((issue.get('fields') or {}).get('comment') or {}).get('comments')) or []


def sum_worklog_seconds(issue: Dict[str, Any]) -> int:
    return sum((w.get('timeSpentSeconds') or 0) for w in worklogs_of(issue))


def format_hours(seconds: int) -> float:
    return round(seconds / 3600, 2)


def clean_text(value: Any) -> str:
    if value is None:
        return ''
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def extract_urls_from_issue(issue: Dict[str, Any]) -> List[str]:
    fields = issue.get('fields') or {}
    text_parts = [clean_text(fields.get('description')), clean_text(fields.get('summary'))]
    return utils.extract_urls('\n'.join(text_parts))


def field_names_map(issue: Dict[str, Any]) -> Dict[str, str]:
    names = issue.get('names') or {}
    return {v: k for k, v in names.items() if isinstance(v, str)}


def first_non_empty(values: List[Any]) -> Optional[Any]:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, (list, dict)) and not value:
            continue
        return value
    return None


def stringify_field_value(value: Any) -> str:
    if value is None:
        return ''
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, dict):
        return first_non_empty([
            value.get('displayName'),
            value.get('name'),
            value.get('value'),
            value.get('label'),
            value.get('key'),
        ]) or json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        parts = [stringify_field_value(item) for item in value]
        return '、'.join([part for part in parts if part])
    return json.dumps(value, ensure_ascii=False)


def parse_jira_datetime(value: str) -> Optional[datetime]:
    if not value:
        return None
    for fmt in ('%Y-%m-%dT%H:%M:%S.%f%z', '%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%d'):
        try:
            return datetime.strptime(value, fmt)
        except Exception:
            continue
    return None


def parse_markdown_table_hours(text: str) -> List[Dict[str, Any]]:
    lines = [line.rstrip() for line in text.splitlines() if line.strip().startswith('|')]
    rows: List[Dict[str, Any]] = []
    for line in lines:
        cols = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cols) < 2:
            continue
        if all(set(col) <= {'-', ':'} for col in cols):
            continue
        hour_idx = None
        for idx, col in enumerate(cols):
            if '工时' in col or '小时' in col or col.lower() == 'h':
                hour_idx = idx
                break
        if hour_idx is None:
            for idx, col in enumerate(cols):
                if normalize_hours(col) is not None:
                    hour_idx = idx
                    break
        if hour_idx is None:
            continue
        hours = normalize_hours(cols[hour_idx])
        if hours is None:
            continue
        owner = ''
        for idx, col in enumerate(cols):
            if idx != hour_idx and col and '工时' not in col and '小时' not in col:
                owner = col
                break
        if owner:
            rows.append({'owner': owner, 'hours': hours, 'raw': cols})
    return rows


def infer_stage_name(summary: str, issue_type: str) -> str:
    text = f'{summary} {issue_type}'
    if any(k in text for k in ['需求传达', '答疑', '调研', '分析会', '对齐']):
        return '需求澄清'
    if any(k in text for k in ['系统分析', '服务搭建', '开发', '封装', '处理', '功能']):
        return '开发推进'
    if any(k in text for k in ['测试', '冒烟', 'dev', 'pre', '用例']):
        return '测试收敛'
    if issue_type == '故障':
        return '缺陷修复'
    return '项目推进'
