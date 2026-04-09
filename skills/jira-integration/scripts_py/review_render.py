import argparse
import os
import sys
from typing import Any, Dict, List, Tuple

try:
    import utils
    import review_common
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import utils
    import review_common


def mermaid_pie(title: str, data: Dict[str, float]) -> str:
    lines = ['```mermaid', 'pie showData', f'    title {title}']
    for key, value in data.items():
        lines.append(f'    "{key}" : {value}')
    lines.append('```')
    return '\n'.join(lines)


def mermaid_mindmap(title: str, lines_data: List[str]) -> str:
    lines = ['```mermaid', 'mindmap', f'  root(({title}))']
    for item in lines_data:
        lines.append(f'    {item}')
    lines.append('```')
    return '\n'.join(lines)


def mermaid_journey(title: str, timeline: List[Dict[str, str]]) -> str:
    lines = ['```mermaid', 'journey', f'    title {title}']
    for item in timeline:
        if item['from'] == item['to']:
            section = item['from']
        else:
            section = f"{item['from']} ~ {item['to']}"
        lines.append(f'    section {section}')
        lines.append(f"      {item['stage']}: 3: 项目")
    lines.append('```')
    return '\n'.join(lines)


def mermaid_flow(pairs: List[Tuple[str, str]], direction: str = 'TB') -> str:
    lines = ['```mermaid', f'flowchart {direction}']
    node_index = 0
    for left, right in pairs:
        a = f'N{node_index}'
        b = f'N{node_index + 1}'
        node_index += 2
        lines.append(f'    {a}[{left}] --> {b}[{right}]')
    lines.append('```')
    return '\n'.join(lines)


def table(headers: List[str], rows: List[List[str]]) -> str:
    head = '| ' + ' | '.join(headers) + ' |'
    split = '| ' + ' | '.join(['---'] * len(headers)) + ' |'
    body = ['| ' + ' | '.join(row) + ' |' for row in rows] or ['| ' + ' | '.join(['无'] * len(headers)) + ' |']
    return '\n'.join([head, split] + body)


def build_role_hours_pie(role_hours: Dict[str, Dict[str, float]]) -> Dict[str, float]:
    return {role: data['hours'] for role, data in role_hours.items() if data['hours'] > 0}


def build_top_author_mindmap(top_authors: List[Dict[str, object]]) -> List[str]:
    return [f"{item['name']} {item['hours']}h {item['role']}/{item.get('specialty', item['role'])}" for item in top_authors]


def build_dim_pie_data(dim_hours: Dict[str, Dict[str, float]]) -> Dict[str, float]:
    return {name: data['hours'] for name, data in dim_hours.items() if data['hours'] > 0}


def filter_display_biz_lines(biz_lines: List[Dict[str, str]]) -> str:
    hidden = {'业务条线'}
    values = [str(biz.get('biz_line_name')) for biz in biz_lines if biz.get('biz_line_name') and biz.get('biz_line_name') not in hidden]
    return '、'.join(values) or '未识别业务线'


def filter_bizline_hours(bizline_hours: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    hidden = {'业务条线'}
    return {name: data for name, data in bizline_hours.items() if name not in hidden}


def build_topic_mindmap(topic_counter: List[List[object]]) -> List[str]:
    return [f'{name} {count}' for name, count in topic_counter]


def build_bug_category_mindmap(category_counter: List[List[object]]) -> List[str]:
    return [f'{name} {count}' for name, count in category_counter]


def build_bug_root_mindmap() -> List[str]:
    return [
        '规则匹配与异动补偿',
        '状态机与时间边界',
        '消息待办与路由契约',
        '模板与历史数据兼容',
        '报表字段口径不一致',
    ]


def build_quality_note(refs_summary: Dict[str, object], estimate: Dict[str, object]) -> List[str]:
    notes = []
    if not refs_summary.get('has_reference_material'):
        notes.append('未获取有效参考资料，本次复盘更偏 Jira 执行过程分析')
    if estimate.get('source') == 'jira_custom_fields':
        notes.append('粗估来自 Jira 自定义字段，若有原始估时文档建议后续补充校准')
    if estimate.get('invalid_placeholder_filtered'):
        notes.append('已自动过滤 888/999 等占位粗估值，避免污染偏差分析')
    if not notes:
        notes.append('已获取参考资料与 Jira 全量数据，复盘口径相对完整')
    return notes


def build_management_summary(analysis: Dict[str, Any]) -> List[str]:
    stats: Dict[str, Any] = analysis['stats']
    insights: Dict[str, Any] = analysis.get('insights', {})
    bug_count = insights.get('bug_issue_count', 0)
    total = stats.get('issue_count', 0) or 1
    bug_ratio = round((bug_count / total) * 100, 2)
    lines = [
        f'BUG占比 {bug_ratio}%',
        f"粗估偏差 {insights.get('estimate_gap_hours', 0)}h",
        f"实际总工时 {stats.get('worklog_hours_total', 0)}h",
    ]
    if bug_ratio >= 50:
        lines.append('后期问题收敛成本高')
    if insights.get('estimate_gap_hours', 0) > 0:
        lines.append('实际投入明显高于粗估')
    title = str(analysis.get('main_summary', ''))
    if 'hotfix' in title.lower():
        lines.append('项目经历 hotfix 发布，说明后期修复收口压力较大')
    if any(word in title for word in ['审批', '申请']):
        lines.append('业务主线涉及申请与审批链路，流程一致性要求高')
    bizline = dict(analysis.get('bizline', {}))
    if bizline.get('biz_line'):
        lines.append(f"业务线 {bizline.get('biz_line')}")
    return lines


def build_tech_card_mindmap() -> List[str]:
    return [
        '状态机复杂',
        '规则引擎复杂',
        '配置与历史兼容',
        '消息待办联动',
        '报表追踪放大问题',
    ]


def build_summary_pairs(estimate_total: float, actual_total: float) -> List[Tuple[str, str]]:
    return [
        (f'粗估 {estimate_total}h', f'实际 {actual_total}h'),
        ('复杂规则型项目', '主风险在规则与状态一致性'),
        ('后期成本高', '集中在联动验证与回归修复'),
    ]


def render_report(issue_key: str, workdir: str) -> dict:
    analysis = review_common.load_json(review_common.analysis_path(workdir, issue_key))
    stats = analysis['stats']
    estimate = analysis['estimate']
    top_authors = analysis['top_authors']
    role_hours = analysis['role_hours']
    specialty_hours = analysis.get('specialty_hours', {})
    bizline_hours = filter_bizline_hours(analysis.get('bizline_hours', {}))
    bug_roots = analysis['bug_roots']
    test_quality = analysis.get('test_quality', {})
    timeline = analysis['timeline']
    issue_types = analysis['issue_types']
    statuses = analysis['statuses']
    refs_summary = analysis['refs_summary']
    insights = analysis.get('insights', {})
    quality_notes = build_quality_note(refs_summary, estimate)
    management_notes = build_management_summary(analysis)
    bizline = analysis.get('bizline', {})
    bug_count = insights.get('bug_issue_count', 0)
    total_count = stats.get('issue_count', 0)

    estimate_total = estimate.get('total_hours', 0.0)
    actual_total = stats.get('worklog_hours_total', 0.0)

    role_rows = [[role, str(data['hours']), str(data['issue_count'])] for role, data in role_hours.items()]
    estimate_rows = [[str(row['owner']), str(row['hours'])] for row in estimate.get('rows', [])]
    bug_rows = [[
        sample.get('key', ''),
        sample.get('summary', '') or '',
        sample.get('reason', '') or '未明确',
        sample.get('solution', '') or '未明确',
    ] for sample in bug_roots.get('samples', [])]
    bug_category_rows = [[str(name), str(count)] for name, count in bug_roots.get('category_counter', [])]
    testcase_module_rows = [[str(name), str(count)] for name, count in test_quality.get('testcase_modules', [])]
    bug_module_rows = [[str(name), str(count)] for name, count in test_quality.get('bug_modules', [])]
    testcase_priority_rows = [[str(name), str(count)] for name, count in test_quality.get('priority_distribution', [])]
    quality_match_rows = [[item['key'], item['summary'], '；'.join(item['matched_cases'])] for item in test_quality.get('matched_samples', [])]

    timeline_rows = [[
        item['stage'],
        item['from'] if item['from'] == item['to'] else f"{item['from']} ~ {item['to']}",
        str(item.get('count', '')),
    ] for item in timeline]

    top_author_rows = [[
        item['name'],
        str(item['hours']),
        item['role'],
        item.get('specialty', item['role']),
        filter_display_biz_lines(item.get('biz_lines', []))
    ] for item in top_authors]
    specialty_rows = [[name, str(data['hours']), str(data['issue_count'])] for name, data in specialty_hours.items()]
    bizline_rows = [[name, str(data['hours']), str(data['issue_count'])] for name, data in bizline_hours.items()]

    content = f"""# {issue_key} 项目复盘报告

> 适用场景：项目复盘会、阶段性管理汇报、跨团队经验复用分享

---

## 01 项目概况

### 项目名称

`{issue_key} {analysis['main_summary']}`

### 数据口径

- 数据来源：Jira 主单、子任务、关联单、完整评论、完整工时
- 编码口径：UTF-8 全量导出
- 参考资料：{'已获取' if refs_summary['has_reference_material'] else '未获取，仅基于 Jira 数据'}
- 业务线：`{bizline.get('biz_line') or '未识别'}`{'（字段：' + bizline.get('source_field', '') + '）' if bizline.get('biz_line') else ''}

### 核心指标

{table(['指标', '数值'], [
    ['总工单数', str(stats['issue_count'])],
    ['关联单数', str(stats['related_count'])],
    ['评论总数', str(stats['comment_total'])],
    ['工时记录数', str(stats['worklog_count'])],
    ['实际总工时(h)', str(actual_total)],
])}

{mermaid_mindmap('项目概况', [
    f"总工单 {stats['issue_count']}",
    f"关联单 {stats['related_count']}",
    f"评论 {stats['comment_total']}",
    f"工时记录 {stats['worklog_count']}",
    f"实际工时 {actual_total}h",
])}

- BUG 单数量：`{insights.get('bug_issue_count', 0)}`
- 子任务数量：`{insights.get('subtask_issue_count', 0)}`

---

## 02 项目画像

{mermaid_pie('工单类型结构', issue_types)}

{table(['类型', '数量'], [[k, str(v)] for k, v in issue_types.items()])}

{mermaid_pie('工单状态分布', statuses)}

{table(['状态', '数量'], [[k, str(v)] for k, v in statuses.items()])}

- 工单结构判断：{'缺陷驱动型项目' if bug_count and total_count and bug_count / total_count >= 0.4 else '功能交付型项目'}

---

## 03 项目阶段节奏

{mermaid_journey('项目复盘路径（含时间轴）', timeline or [{'stage': '项目推进', 'from': '未知', 'to': '未知'}])}

{table(['阶段', '时间范围', '工单数'], timeline_rows)}

---

## 04 人员投入结构

{mermaid_mindmap('核心成员工时', build_top_author_mindmap(top_authors) or ['暂无工时'])}

{mermaid_pie('角色工时占比', build_role_hours_pie(role_hours) or {'未知': 0})}

{mermaid_pie('技术方向工时占比', build_dim_pie_data(specialty_hours) or {'未知': 0})}

{mermaid_pie('业务线工时占比', build_dim_pie_data(bizline_hours) or {'未识别业务线': 0})}

{table(['人员', '工时(h)', '主角色', '技术方向', '业务线'], top_author_rows)}

{table(['角色', '工时(h)', '涉及工单数'], role_rows)}

{table(['技术方向', '工时(h)', '涉及工单数'], specialty_rows)}

{table(['业务线', '工时(h)', '涉及工单数'], bizline_rows)}

---

## 05 粗估与实际偏差

- 粗估来源：`{estimate.get('source', 'none')}`
- 粗估模式：`{estimate.get('mode', 'unknown')}`
- 粗估偏差：`{insights.get('estimate_gap_hours', 0)}h`

{mermaid_flow(build_summary_pairs(estimate_total, actual_total))}

{table(['粗估项', '工时(h)'], estimate_rows)}

- 偏差解读：{'当前无有效粗估数据，无法准确评估偏差' if estimate_total == 0 else '当前粗估与实际存在明显差距，建议结合原始估时文档和需求变更记录复核'}

---

## 06 BUG 全景分析

{mermaid_mindmap('BUG高频主题', build_topic_mindmap(bug_roots.get('topic_counter', [])) or ['暂无明显主题'])}

{mermaid_mindmap('BUG问题分类', build_bug_category_mindmap(bug_roots.get('category_counter', [])) or ['暂无明显分类'])}

{mermaid_mindmap('BUG根因模型', build_bug_root_mindmap())}

{table(['主题', '命中次数'], [[str(name), str(count)] for name, count in bug_roots.get('topic_counter', [])])}

{table(['问题分类', '数量'], bug_category_rows)}

{table(['工单', '现象', '原因', '解决方案'], bug_rows)}

- BUG 根因提取优先基于评论中的“问题原因/解决方案/影响范围”等模式句；若评论不规范，则回退为摘要提取。
- 若 BUG 数量较少，当前结论偏向“代表性问题”复盘，而非全面故障画像。

---

## 07 测试与质量复盘

- 测试用例总数：`{test_quality.get('testcase_total', 0)}`
- BUG 总数：`{test_quality.get('bug_total', 0)}`
- PRE 阶段问题数：`{test_quality.get('pre_bug_total', 0)}`
- 1Q 问题数：`{test_quality.get('one_q_bug_total', 0)}`
- BUG-用例映射率：`{test_quality.get('bug_case_mapping_rate', 0)}%`

{mermaid_mindmap('测试与质量观察', [
    f"测试用例 {test_quality.get('testcase_total', 0)} 条",
    f"PRE问题 {test_quality.get('pre_bug_total', 0)} 个",
    f"1Q问题 {test_quality.get('one_q_bug_total', 0)} 个",
    f"映射覆盖率 {test_quality.get('bug_case_mapping_rate', 0)}%",
    test_quality.get('coverage_judgement', '暂无额外质量结论'),
])}

{table(['用例模块', '数量'], testcase_module_rows)}

{table(['BUG模块', '数量'], bug_module_rows)}

{table(['用例优先级', '数量'], testcase_priority_rows)}

{table(['已映射BUG', '摘要', '匹配用例'], quality_match_rows)}

- 1Q问题优先按 `1Q / 首轮 / 第一轮 / 首次提测 / 冒烟` 关键词识别；若案例中未显式标注，则当前结果可能偏保守。
- 该板块用于判断问题是否前移暴露、用例是否覆盖高风险模块、以及测试是否集中在基础场景而遗漏复杂闭环。
- 当前模块映射优先按测试用例模块与 BUG 摘要关键词进行关联，已比纯关键词匹配更稳，但仍建议后续补充 case id 或模块字段做强映射。

---

## 08 技术卡点

{mermaid_mindmap('技术卡点', build_tech_card_mindmap())}

- 项目真正难点不是单页面实现，而是多实体、多规则、多状态、多系统联动。
- 一旦规则没有前移显式建模，问题会在后期以大量 BUG 的方式集中暴露。
- 对于字段/审批/展示类项目，卡点通常集中在配置一致性、字段同步和终端表现差异。

---

## 09 管理结论

{mermaid_flow([
    ('复杂规则型项目', '主风险在规则一致性与状态一致性'),
    ('成本大头', '联动验证、回归修复、规则补偿'),
    ('团队投入', '产品/研发/QA 均需深度协同'),
    ('后续方向', '前移规则建模并补齐自动化验证'),
])}

{mermaid_mindmap('管理观察', management_notes)}

- 本次复盘优先依赖全量 Jira 数据；若参考资料不足，结论更偏执行过程与问题结构分析。
- 若补充更完整的需求文档、项目计划或会议纪要，可进一步增强粗估偏差和阶段目标分析。

## 10 复盘口径与质量说明

{mermaid_mindmap('复盘口径与质量说明', quality_notes)}

- 角色识别优先使用用户显式映射，其次使用 `责任人` / `BUG制造者` / assignee 推断。
- 当前版本已优先使用 Jira 用户组识别角色，其次才回退到 Jira 字段与工单语义推断。
- 身份基础设施已直接输出角色编码、中文映射、主角色和技术方向，供复盘分析统一消费。
- 若外部文档只抓到登录页或壳页，不视为有效参考资料，会自动回退到 Jira 数据分析。
"""

    output_path = review_common.review_output_path(workdir, issue_key, '项目复盘报告', 'md')
    review_common.save_text(output_path, content)
    return {'output_path': output_path}


if __name__ == '__main__':
    utils.ensure_utf8_stdio()
    parser = argparse.ArgumentParser(description='渲染项目复盘报告（UTF-8 Markdown）')
    parser.add_argument('--issue', type=str, required=True, help='主工单 KEY')
    parser.add_argument('--workdir', type=str, required=True, help='工作目录')
    args = parser.parse_args()
    utils.validate_workdir(args.workdir)
    utils.set_workdir(args.workdir)
    result = render_report(args.issue, args.workdir)
    utils.log_to_agent({'success': True, 'issue_key': args.issue, 'output_path': result['output_path']})
