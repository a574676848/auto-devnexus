import argparse
import os
import re
import sys
from collections import Counter, defaultdict

try:
    import utils
    import review_common
    import review_identity
    import review_bizline
    import review_testquality
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import utils
    import review_common
    import review_identity
    import review_bizline
    import review_testquality


ESTIMATE_FIELD_ALIASES = [
    '产品预估工时',
    '业务net预估工时',
    '业务java预估工时',
    '前端预估工时',
    'QA测试粗估',
]

ROLE_FIELD_ALIASES = ['责任人', 'BUG制造者']
TOPIC_WORDS = ['项目地图', '点评人', '规则', '状态', '匹配', '模板', '完成条件', '截止时间', '报错', '重算', '消息', '结束时间', '页面', '字段', '审批', '上传', '排序', '地址', '权限', '日志', '收货', '尺码', '门店', '配饰']
INVALID_ESTIMATE_VALUES = {888.0, 999.0, 9999.0}
BUG_CATEGORY_RULES = {
    '展示与交互': ['页面', '显示', '展示', '弹窗', '排序', '日志', '尺码', '配饰'],
    '字段与数据同步': ['字段', '地址', '门店', '同步', '取值', '数据'],
    '审批与流程': ['审批', '收货', '发货', '状态', '流程'],
    '权限与配置': ['权限', '配置', '数据权限'],
    '上传与兼容': ['上传', '图片', '视频', 'ios', '安卓'],
    '查询与搜索': ['搜索', '查询', '编号', '匹配'],
}


def cleanup_reason_text(value: str) -> str:
    if not value:
        return ''
    value = value.replace('【问题原因】', '').replace('【解决方案】', '').replace('【影响范围】', '')
    value = value.replace('*问题原因*', '').replace('*解决方案*', '')
    value = re.sub(r'!image-[^!]+!', '', value)
    value = re.sub(r'\{code:[^}]+\}', '', value)
    value = re.sub(r'\s+', ' ', value).strip(' ：:')
    return value[:160]
ESTIMATE_FIELD_FUZZY = {
    '产品预估工时': ['产品', '预估', '工时'],
    '业务net预估工时': ['业务', 'net', '预估'],
    '业务java预估工时': ['业务', 'java', '预估'],
    '前端预估工时': ['前端', '预估'],
    'QA测试粗估': ['qa', '测试', '粗估'],
}
ROLE_FIELD_FUZZY = {
    '责任人': ['责任人'],
    'BUG制造者': ['bug', '制造者'],
}


def build_field_alias_map(issue: dict) -> dict:
    names = issue.get('names') or {}
    aliases = {}
    for field_id, field_name in names.items():
        aliases[field_name] = field_id
    return aliases


def resolve_field_id(field_map: dict, target_name: str, fuzzy_rules: dict) -> str:
    if target_name in field_map:
        return field_map[target_name]
    keywords = fuzzy_rules.get(target_name, [])
    for field_name, field_id in field_map.items():
        lower_name = field_name.lower()
        if all(keyword.lower() in lower_name for keyword in keywords):
            return field_id
    return ''


def load_role_mapping(role_args: list) -> dict:
    mapping = {}
    for item in role_args:
        if '=' not in item:
            continue
        name, role = item.split('=', 1)
        mapping[name.strip()] = role.strip()
    return mapping


MANUAL_ARCHITECT_OVERRIDE = set()


def collect_user_candidates(issues: list) -> list:
    users = {}
    for issue in issues:
        fields = issue.get('fields', {})
        for user in [fields.get('assignee'), fields.get('reporter')]:
            if isinstance(user, dict):
                username = user.get('name') or user.get('key') or ''
                display_name = user.get('displayName') or username
                if username:
                    users[display_name] = {'username': username, 'displayName': display_name}
        for worklog in review_common.worklogs_of(issue):
            author = worklog.get('author') or {}
            username = author.get('name') or author.get('key') or ''
            display_name = author.get('displayName') or username
            if username:
                users[display_name] = {'username': username, 'displayName': display_name}
    return list(users.values())


def infer_roles(issues: list, field_map: dict, explicit_mapping: dict) -> dict:
    resolved = {}
    identity_data = review_identity.fetch_identity(collect_user_candidates(issues))
    identity_users = identity_data['users']
    for display_name, item in identity_users.items():
        if display_name in explicit_mapping:
            resolved[display_name] = {
                'main_role_code': 'manual',
                'main_role_name': explicit_mapping[display_name],
                'specialty_code': 'manual',
                'specialty_name': explicit_mapping[display_name],
                'source': 'manual',
            }
            continue
        if display_name in MANUAL_ARCHITECT_OVERRIDE:
            cloned = dict(item)
            cloned['main_role_code'] = 'architect'
            cloned['main_role_name'] = '架构'
            cloned['specialty_code'] = 'architect'
            cloned['specialty_name'] = '架构'
            cloned['source'] = 'manual_architect_override'
            resolved[display_name] = cloned
            continue
        if item.get('main_role_code') != 'unknown':
            resolved[display_name] = item
    qa_keywords = ['测试', '冒烟', '用例', '验证', 'pre', '提测']
    product_keywords = ['需求', '答疑', '传达', '分析', '评审', '工时粗估', '需求同步', '方案']
    dev_keywords = ['开发', '封装', '功能', '搭建', '处理', 'hotfix', '发布', '联调', '接口', '修复']
    person_scores = defaultdict(lambda: Counter())

    def add_score(name: str, role: str, score: int):
        if not name or name == 'Unassigned':
            return
        if name in explicit_mapping:
            return
        person_scores[name][role] += score

    def extract_people(raw_value, source_hint: str, summary: str, issue_type: str, is_main_issue: bool):
        people = []
        if isinstance(raw_value, dict):
            people.append(raw_value.get('displayName') or raw_value.get('name'))
        elif isinstance(raw_value, list):
            for item in raw_value:
                if isinstance(item, dict):
                    people.append(item.get('displayName') or item.get('name'))
                elif item:
                    people.append(str(item))
        elif raw_value:
            text = review_common.stringify_field_value(raw_value)
            people.extend([v.strip() for v in re.split(r'[、,，/\s]+', text) if v.strip()])
        for person in people:
            if source_hint == 'bug_owner':
                add_score(person, '研发', 4)
            elif source_hint == 'owner_field':
                if is_main_issue and len(people) > 1:
                    add_score(person, '研发', 1)
                elif any(k in summary for k in qa_keywords):
                    add_score(person, 'QA', 2)
                elif any(k in summary for k in product_keywords):
                    add_score(person, '产品', 2)
                elif any(k in summary for k in dev_keywords) or issue_type in {'故障', '子任务'}:
                    add_score(person, '研发', 2)
        return [person for person in people if person]

    for issue in issues:
        issue_type = review_common.get_issue_type(issue)
        summary = (issue.get('fields', {}).get('summary') or '')
        fields = issue.get('fields', {})
        assignee = review_common.get_issue_assignee(issue)
        reporter = ((fields.get('reporter') or {}).get('displayName')) or ((fields.get('reporter') or {}).get('name')) or ''
        summary_lower = summary.lower()

        is_main_issue = issue.get('key') == issues[0].get('key')
        if assignee not in resolved and (any(k in summary for k in qa_keywords) or 'pre' in summary_lower or 'dev' in summary_lower):
            add_score(assignee, 'QA', 3)
        elif assignee not in resolved and any(k in summary for k in product_keywords):
            add_score(assignee, '产品', 3)
        elif assignee not in resolved and any(k in summary for k in dev_keywords):
            add_score(assignee, '研发', 3)
        elif assignee not in resolved and issue_type == '故障':
            add_score(assignee, 'QA', 1)
        elif assignee not in resolved:
            add_score(assignee, '研发', 1)

        if reporter and reporter == assignee and reporter not in resolved and any(k in summary for k in product_keywords):
            add_score(reporter, '产品', 2)

        field_name = 'BUG制造者' if issue_type == '故障' else '责任人'
        field_id = resolve_field_id(field_map, field_name, ROLE_FIELD_FUZZY)
        raw_value = (issue.get('fields') or {}).get(field_id) if field_id else None
        extract_people(raw_value, 'bug_owner' if issue_type == '故障' else 'owner_field', summary, issue_type, is_main_issue)

        for worklog in review_common.worklogs_of(issue):
            author = ((worklog.get('author') or {}).get('displayName')) or ((worklog.get('author') or {}).get('name')) or ''
            if author in resolved:
                continue
            if any(k in summary for k in qa_keywords) or 'pre' in summary_lower or 'dev' in summary_lower:
                add_score(author, 'QA', 2)
            elif any(k in summary for k in product_keywords):
                add_score(author, '产品', 1)
            elif any(k in summary for k in dev_keywords) or issue_type in {'故障', '子任务'}:
                add_score(author, '研发', 2)
            if issue_type == '故障':
                add_score(author, '研发', 1)

    for name, score_counter in person_scores.items():
        if name in resolved:
            continue
        if not score_counter:
            resolved[name] = {
                'main_role_code': 'unknown',
                'main_role_name': '未知',
                'specialty_code': 'unknown',
                'specialty_name': '未知',
                'source': 'heuristic_unknown',
            }
            continue
        role_name = score_counter.most_common(1)[0][0]
        role_code = 'rd' if role_name == '研发' else 'product' if role_name == '产品' else 'qa' if role_name == 'QA' else 'unknown'
        resolved[name] = {
            'main_role_code': role_code,
            'main_role_name': role_name,
            'specialty_code': 'unknown',
            'specialty_name': role_name,
            'source': 'heuristic',
        }
    return {'identities': resolved, 'definitions': identity_data}


def extract_estimate(refs: dict, main_issue: dict, field_map: dict) -> dict:
    for item in refs.get('items', []):
        if item.get('success') and item.get('content'):
            rows = review_common.parse_markdown_table_hours(item['content'])
            if rows:
                total = round(sum(row['hours'] for row in rows), 2)
                return {'source': item.get('path') or item.get('url') or item.get('source'), 'mode': 'reference_material', 'rows': rows, 'total_hours': total}
    rows = []
    total = 0.0
    for alias in ESTIMATE_FIELD_ALIASES:
        field_id = resolve_field_id(field_map, alias, ESTIMATE_FIELD_FUZZY)
        value = (main_issue.get('fields') or {}).get(field_id) if field_id else None
        hours = review_common.normalize_hours(value)
        if hours is not None and hours not in INVALID_ESTIMATE_VALUES:
            rows.append({'owner': alias, 'hours': hours, 'raw': value})
            total += hours
    return {'source': 'jira_custom_fields' if rows else 'none', 'mode': 'jira_field', 'rows': rows, 'total_hours': round(total, 2), 'invalid_placeholder_filtered': True}


def build_timeline(main_issue: dict, issues: list) -> list:
    stage_ranges = defaultdict(list)
    main_created = review_common.parse_jira_datetime((main_issue.get('fields') or {}).get('created') or '')
    for issue in sorted(issues, key=lambda x: (x.get('fields', {}).get('created') or '')):
        fields = issue.get('fields', {})
        summary = fields.get('summary') or ''
        issue_type = review_common.get_issue_type(issue)
        status = review_common.get_issue_status(issue)
        created = review_common.parse_jira_datetime(fields.get('created') or '')
        updated = review_common.parse_jira_datetime(fields.get('updated') or '') or created
        if not created:
            continue
        summary_lower = summary.lower()
        if issue_type == '故障' and ('dev' in summary_lower or 'pre' in summary_lower or '测试' in summary):
            stage = '测试收敛'
        elif issue_type == '故障':
            stage = '缺陷修复'
        elif any(k in summary for k in ['协同', '验收', '发布', 'hotfix', '跟进']):
            stage = '项目推进'
        else:
            stage = review_common.infer_stage_name(summary, issue_type)
        if issue_type == '服务工单' and created < main_created:
            continue
        stage_ranges[stage].append((created, updated, summary, status))
    ordered = ['需求澄清', '开发推进', '测试收敛', '缺陷修复', '项目推进']
    timeline = []
    for stage in ordered:
        records = stage_ranges.get(stage, [])
        if not records:
            continue
        if stage == '项目推进' and len(records) <= 3:
            continue
        start = min(record[0] for record in records).strftime('%Y-%m-%d')
        end = max(record[1] for record in records).strftime('%Y-%m-%d')
        timeline.append({'stage': stage, 'from': start, 'to': end, 'count': len(records)})
    if main_created:
        timeline.insert(0, {'stage': '需求启动', 'from': main_created.strftime('%Y-%m-%d'), 'to': main_created.strftime('%Y-%m-%d'), 'count': 1})
    return timeline


def build_bug_roots(issues: list) -> dict:
    bugs = [issue for issue in issues if review_common.get_issue_type(issue) == '故障']
    categories = Counter()
    category_counter = Counter()
    samples = []
    for issue in bugs:
        summary = (issue.get('fields', {}).get('summary') or '')
        text = summary + '\n' + '\n'.join(comment.get('body') or '' for comment in review_common.comments_of(issue))
        for word in TOPIC_WORDS:
            if word in text:
                categories[word] += 1
        matched_category = None
        for category, keywords in BUG_CATEGORY_RULES.items():
            if any(keyword in text for keyword in keywords):
                category_counter[category] += 1
                if matched_category is None:
                    matched_category = category
        bodies = [comment.get('body') or '' for comment in review_common.comments_of(issue)]
        reason = ''
        solution = ''
        impact = ''
        for body in bodies:
            if not reason:
                match = re.search(r'(问题原因|原因)[:：]\s*(.+)', body)
                if match:
                    reason = match.group(2).strip()
            if not solution:
                match = re.search(r'(解决方案|解决问题)[:：]\s*(.+)', body)
                if match:
                    solution = match.group(2).strip()
            if not impact:
                match = re.search(r'(影响范围|影响)[:：]\s*(.+)', body)
                if match:
                    impact = match.group(2).strip()
        if not reason and bodies:
            candidate = (bodies[-1] or '').replace('\r', ' ').replace('\n', ' ')
            candidate = re.sub(r'\{code:[^}]+\}.*', '', candidate)
            candidate = candidate.replace('*问题原因*', '').replace('*解决方案*', '')
            candidate = re.sub(r'<[^>]+>', ' ', candidate)
            candidate = re.sub(r'\s+', ' ', candidate).strip()
            reason = candidate[:120]
        if reason.startswith('解决') and not solution:
            solution = reason
            reason = ''
        reason = cleanup_reason_text(reason)
        solution = cleanup_reason_text(solution)
        impact = cleanup_reason_text(impact)
        if reason or solution or impact:
            samples.append({'key': issue.get('key'), 'summary': issue.get('fields', {}).get('summary'), 'reason': reason, 'solution': solution, 'impact': impact, 'category': matched_category or '其他'})
    return {'topic_counter': categories.most_common(12), 'category_counter': category_counter.most_common(), 'samples': samples[:10]}


def analyze(issue_key: str, workdir: str, role_args: list) -> dict:
    bundle = review_common.load_json(review_common.bundle_path(workdir, issue_key))
    refs_file = review_common.refs_path(workdir, issue_key)
    refs = review_common.load_json(refs_file) if os.path.exists(refs_file) else {'items': [], 'has_reference_material': False}
    main_issue = bundle['main_issue']
    issues = [main_issue] + bundle['related_issues']
    field_map = build_field_alias_map(main_issue)
    explicit_roles = load_role_mapping(role_args)
    identity_result = infer_roles(issues, field_map, explicit_roles)
    role_mapping = identity_result['identities']
    bizline = review_bizline.detect_bizline(issue_key, workdir)['result']
    estimate = extract_estimate(refs, main_issue, field_map)
    timeline = build_timeline(main_issue, issues)
    bug_roots = build_bug_roots(issues)
    testcase_data = review_testquality.parse_testcase_files(workdir)
    quality_analysis = review_testquality.analyze_quality(bundle, testcase_data)

    issue_types = Counter(review_common.get_issue_type(issue) for issue in issues)
    statuses = Counter(review_common.get_issue_status(issue) for issue in issues)
    author_hours = defaultdict(int)
    role_hours = defaultdict(int)
    specialty_hours = defaultdict(int)
    bizline_hours = defaultdict(int)
    issue_count_by_role = defaultdict(set)
    issue_count_by_specialty = defaultdict(set)
    issue_count_by_bizline = defaultdict(set)
    for issue in issues:
        for worklog in review_common.worklogs_of(issue):
            author = ((worklog.get('author') or {}).get('displayName')) or ((worklog.get('author') or {}).get('name')) or 'Unknown'
            seconds = worklog.get('timeSpentSeconds') or 0
            author_hours[author] += seconds
            identity = role_mapping.get(author, {'main_role_name': '未知'})
            role = identity.get('main_role_name', '未知')
            specialty = identity.get('specialty_name', role)
            biz_lines = identity.get('biz_lines') or []
            role_hours[role] += seconds
            specialty_hours[specialty] += seconds
            issue_count_by_role[role].add(issue.get('key'))
            issue_count_by_specialty[specialty].add(issue.get('key'))
            if biz_lines:
                for biz in biz_lines:
                    biz_name = biz.get('biz_line_name') or '未识别业务线'
                    bizline_hours[biz_name] += seconds
                    issue_count_by_bizline[biz_name].add(issue.get('key'))
            else:
                bizline_hours['未识别业务线'] += seconds
                issue_count_by_bizline['未识别业务线'].add(issue.get('key'))

    total_worklog_hours = review_common.format_hours(sum(review_common.sum_worklog_seconds(issue) for issue in issues))

    analysis = {
        'issue_key': issue_key,
        'main_summary': main_issue.get('fields', {}).get('summary'),
        'stats': {
            'issue_count': len(issues),
            'related_count': len(bundle['related_issues']),
            'comment_total': sum(len(review_common.comments_of(issue)) for issue in issues),
            'worklog_count': sum(len(review_common.worklogs_of(issue)) for issue in issues),
            'worklog_hours_total': total_worklog_hours,
        },
        'issue_types': dict(issue_types),
        'statuses': dict(statuses),
        'role_mapping': role_mapping,
        'identity_definitions': identity_result['definitions'],
        'estimate': estimate,
        'bizline': bizline,
        'timeline': timeline,
        'bug_roots': bug_roots,
        'test_quality': quality_analysis,
        'field_map': field_map,
        'top_authors': sorted([
            {
                'name': name,
                'hours': review_common.format_hours(seconds),
                'role': (role_mapping.get(name) or {}).get('main_role_name', '未知'),
                'specialty': (role_mapping.get(name) or {}).get('specialty_name', '未知'),
                'biz_lines': (role_mapping.get(name) or {}).get('biz_lines', []),
            }
            for name, seconds in author_hours.items()
        ], key=lambda x: (-x['hours'], x['name']))[:12],
        'role_hours': {
            role: {
                'hours': review_common.format_hours(seconds),
                'issue_count': len(issue_count_by_role[role]),
            }
            for role, seconds in role_hours.items()
        },
        'specialty_hours': {
            specialty: {
                'hours': review_common.format_hours(seconds),
                'issue_count': len(issue_count_by_specialty[specialty]),
            }
            for specialty, seconds in specialty_hours.items()
        },
        'bizline_hours': {
            bizline: {
                'hours': review_common.format_hours(seconds),
                'issue_count': len(issue_count_by_bizline[bizline]),
            }
            for bizline, seconds in bizline_hours.items()
        },
        'refs_summary': {
            'has_reference_material': refs.get('has_reference_material', False),
            'description_urls': refs.get('description_urls', bundle.get('description_urls', [])),
            'reference_count': len(refs.get('items', [])),
        },
        'insights': {
            'estimate_gap_hours': round(total_worklog_hours - estimate['total_hours'], 2),
            'has_estimate': estimate['total_hours'] > 0,
            'bug_issue_count': issue_types.get('故障', 0),
            'subtask_issue_count': issue_types.get('子任务', 0),
            'bug_category_count': len(bug_roots.get('category_counter', [])),
        },
    }
    output_path = review_common.analysis_path(workdir, issue_key)
    review_common.save_json(output_path, analysis)
    return {'analysis_path': output_path, 'analysis': analysis}


if __name__ == '__main__':
    utils.ensure_utf8_stdio()
    parser = argparse.ArgumentParser(description='分析 Jira 项目复盘数据（UTF-8）')
    parser.add_argument('--issue', type=str, required=True, help='主工单 KEY')
    parser.add_argument('--workdir', type=str, required=True, help='工作目录')
    parser.add_argument('--role', action='append', default=[], help='角色映射，格式 姓名=角色，可重复传入')
    args = parser.parse_args()
    utils.validate_workdir(args.workdir)
    utils.set_workdir(args.workdir)
    result = analyze(args.issue, args.workdir, args.role)
    utils.log_to_agent({'success': True, 'issue_key': args.issue, 'analysis_path': result['analysis_path'], 'stats': result['analysis']['stats'], 'estimate_source': result['analysis']['estimate']['source']})
