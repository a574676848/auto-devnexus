import argparse
import os
import sys
from typing import Any, Dict, List, Optional

try:
    import utils
    import review_common
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import utils
    import review_common


BIZLINE_FIELD_NAMES = ['业务线', '产品线', '所属业务线', '业务条线']


def resolve_field(issue: dict) -> Optional[Dict[str, Any]]:
    names = issue.get('names') or {}
    fields = issue.get('fields') or {}
    for target in BIZLINE_FIELD_NAMES:
        for field_id, field_name in names.items():
            if field_name == target:
                value = fields.get(field_id)
                text = review_common.stringify_field_value(value)
                if text:
                    return {
                        'field_id': field_id,
                        'field_name': field_name,
                        'value': text,
                        'raw': value,
                    }
    for field_id, field_name in names.items():
        if any(target in str(field_name) for target in BIZLINE_FIELD_NAMES):
            value = fields.get(field_id)
            text = review_common.stringify_field_value(value)
            if text:
                return {
                    'field_id': field_id,
                    'field_name': field_name,
                    'value': text,
                    'raw': value,
                }
    return None


def detect_bizline(issue_key: str, workdir: str) -> Dict[str, Any]:
    bundle = review_common.load_json(review_common.bundle_path(workdir, issue_key))
    main_issue = bundle['main_issue']
    match = resolve_field(main_issue)
    result = {
        'issue_key': issue_key,
        'biz_line': match.get('value') if match else '',
        'source_field': match.get('field_name') if match else '',
        'field_id': match.get('field_id') if match else '',
    }
    output_path = utils.get_work_file_path(workdir, f'review_bizline_{issue_key}.json')
    review_common.save_json(output_path, result)
    return {'output_path': output_path, 'result': result}


if __name__ == '__main__':
    utils.ensure_utf8_stdio()
    parser = argparse.ArgumentParser(description='识别工单业务线（UTF-8）')
    parser.add_argument('--issue', type=str, required=True, help='主工单 KEY')
    parser.add_argument('--workdir', type=str, required=True, help='工作目录')
    args = parser.parse_args()
    utils.validate_workdir(args.workdir)
    utils.set_workdir(args.workdir)
    result = detect_bizline(args.issue, args.workdir)
    utils.log_to_agent({'success': True, 'issue_key': args.issue, 'biz_line': result['result']['biz_line'], 'source_field': result['result']['source_field'], 'output_path': result['output_path']})
