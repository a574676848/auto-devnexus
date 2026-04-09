import os
import re
from collections import Counter
from typing import Any, Dict, List

import openpyxl

try:
    import review_common
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import review_common


def parse_testcase_files(workdir: str) -> Dict[str, Any]:
    entries = os.listdir(workdir)
    excel_files = [os.path.join(workdir, name) for name in entries if name.lower().endswith('.xlsx') and '测试用例' in name]
    markdown_files = [os.path.join(workdir, name) for name in entries if name.lower().endswith('.md')]

    cases: List[Dict[str, Any]] = []
    for path in excel_files:
        wb = openpyxl.load_workbook(path, data_only=True)
        for ws in wb.worksheets:
            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                continue
            header = [str(cell).strip() if cell is not None else '' for cell in rows[0]]
            index_map = {name: idx for idx, name in enumerate(header)}
            for row in rows[1:]:
                if not any(row):
                    continue
                case_name = row[index_map.get('用例名称', 0)] if '用例名称' in index_map else ''
                module = row[index_map.get('所属模块', 1)] if '所属模块' in index_map else ''
                priority = row[index_map.get('用例等级', 10)] if '用例等级' in index_map else ''
                status = row[index_map.get('用例状态', 8)] if '用例状态' in index_map else ''
                steps = row[index_map.get('步骤描述', 4)] if '步骤描述' in index_map else ''
                expected = row[index_map.get('预期结果', 5)] if '预期结果' in index_map else ''
                owner = row[index_map.get('责任人', 9)] if '责任人' in index_map else ''
                cases.append({
                    'case_name': str(case_name or '').strip(),
                    'module': str(module or '').strip(),
                    'priority': str(priority or '').strip(),
                    'status': str(status or '').strip(),
                    'steps': str(steps or '').strip(),
                    'expected': str(expected or '').strip(),
                    'owner': str(owner or '').strip(),
                    'source': os.path.basename(path),
                    'sheet': ws.title,
                })

    requirement_docs = []
    for path in markdown_files:
        if '测试用例' in os.path.basename(path):
            continue
        try:
            text = open(path, 'r', encoding='utf-8').read()
            requirement_docs.append({'path': path, 'content': text})
        except Exception:
            continue

    return {
        'testcase_files': excel_files,
        'requirement_docs': [doc['path'] for doc in requirement_docs],
        'cases': cases,
    }


def normalize_module(module: str) -> str:
    if not module:
        return '未识别模块'
    module = module.replace('\\', '/').strip()
    parts = [part for part in module.split('/') if part]
    if not parts:
        return '未识别模块'
    leaf = parts[-1]
    if '尺码' in leaf:
        return '尺码主数据'
    if '工服配饰' in leaf or '配饰' in leaf:
        return '工服配饰管理'
    if '统计' in leaf:
        return '工服领用统计表'
    if '明细' in leaf:
        return '工服领用明细表'
    if '我的工服' in leaf:
        return '我的工服'
    if '申领' in leaf or '审批' in leaf:
        return '工服申领与审批'
    return leaf


def infer_bug_module(summary: str) -> str:
    if '尺码' in summary:
        return '尺码主数据'
    if '配饰' in summary or '工服配饰' in summary:
        return '工服配饰管理'
    if '统计表' in summary:
        return '工服领用统计表'
    if '明细表' in summary:
        return '工服领用明细表'
    if '我的工服' in summary:
        return '我的工服'
    if '申领' in summary or '审批' in summary or '发货' in summary or '收货' in summary:
        return '工服申领与审批'
    if '移动端' in summary or 'ios' in summary.lower() or '安卓' in summary:
        return '移动端'
    return '未识别模块'


def analyze_quality(bundle: Dict[str, Any], testcase_data: Dict[str, Any]) -> Dict[str, Any]:
    issues = [bundle['main_issue']] + bundle['related_issues']
    bugs = [issue for issue in issues if review_common.get_issue_type(issue) == '故障']
    cases = testcase_data['cases']

    module_counter = Counter()
    priority_counter = Counter()
    status_counter = Counter()
    for case in cases:
        module_counter[normalize_module(case['module'])] += 1
        priority_counter[case['priority'] or '未标记'] += 1
        status_counter[case['status'] or '未标记'] += 1

    bug_matches = []
    unmatched_bugs = []
    one_q_bugs = []
    pre_bugs = []
    bug_module_counter = Counter()
    for bug in bugs:
        summary = (bug.get('fields', {}).get('summary') or '')
        comments = '\n'.join(comment.get('body') or '' for comment in review_common.comments_of(bug))
        text = summary + '\n' + comments
        bug_module = infer_bug_module(summary)
        bug_module_counter[bug_module] += 1
        if any(keyword in text for keyword in ['【pre】', 'pre', 'PRE']):
            pre_bugs.append(bug)
        if any(keyword in text for keyword in ['1Q', '首轮', '第一轮', '首次提测', '冒烟', '首次验证']):
            one_q_bugs.append(bug)
        matched = []
        for case in cases:
            module = normalize_module(case['module'])
            if module != '未识别模块' and module == bug_module:
                matched.append(case['case_name'])
                continue
            name = case['case_name']
            key_terms = re.split(r'[-—（）()、，,\s]+', name)
            key_terms = [term for term in key_terms if len(term) >= 2]
            if any(term in summary for term in key_terms[:4]):
                matched.append(name)
        if matched:
            bug_matches.append({'key': bug['key'], 'summary': summary, 'matched_cases': matched[:5]})
        else:
            unmatched_bugs.append({'key': bug['key'], 'summary': summary})

    quality = {
        'testcase_total': len(cases),
        'testcase_modules': module_counter.most_common(12),
        'bug_modules': bug_module_counter.most_common(12),
        'priority_distribution': priority_counter.most_common(),
        'status_distribution': status_counter.most_common(),
        'bug_total': len(bugs),
        'pre_bug_total': len(pre_bugs),
        'one_q_bug_total': len(one_q_bugs),
        'bug_case_mapping_count': len(bug_matches),
        'bug_case_mapping_rate': round(len(bug_matches) / len(bugs) * 100, 2) if bugs else 0.0,
        'unmatched_bug_count': len(unmatched_bugs),
        'matched_samples': bug_matches[:10],
        'unmatched_samples': unmatched_bugs[:10],
        'coverage_judgement': '测试用例已覆盖主数据与基础交互，但从 BUG 分布看，复杂流程、移动端兼容、审批节点字段回写、地址/门店同步等闭环场景仍是质量薄弱区。',
    }
    return quality
