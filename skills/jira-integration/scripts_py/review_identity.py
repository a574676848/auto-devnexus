import argparse
import os
import sys
from typing import Dict, List, Optional

try:
    import utils
    import review_common
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import utils
    import review_common


ROLE_DEFINITIONS = {
    'product': {'name_zh': '产品'},
    'qa': {'name_zh': 'QA'},
    'rd': {'name_zh': '研发'},
    'architect': {'name_zh': '架构'},
    'unknown': {'name_zh': '未知'},
}

BIZLINE_DEFINITIONS = {
    'org-biz-od': {'name_zh': '组织发展'},
    'org-biz-io': {'name_zh': '激励运营'},
    'org-biz-ai': {'name_zh': 'AI业务'},
    'org-biz-co': {'name_zh': '共用业务'},
    'org-biz-bo': {'name_zh': '业务运营'},
    'org-business': {'name_zh': '业务条线'},
    'org-sp': {'name_zh': '技术支持'},
    'org-epaas': {'name_zh': '架构'},
}

SPECIALTY_DEFINITIONS = {
    'product_manager': {'name_zh': '产品经理', 'main_role_code': 'product'},
    'qa_engineer': {'name_zh': '测试', 'main_role_code': 'qa'},
    'frontend_native': {'name_zh': '原生', 'main_role_code': 'rd'},
    'frontend_h5': {'name_zh': '前端', 'main_role_code': 'rd'},
    'frontend': {'name_zh': '前端', 'main_role_code': 'rd'},
    'backend_net': {'name_zh': '后端.NET', 'main_role_code': 'rd'},
    'backend_java': {'name_zh': '后端Java', 'main_role_code': 'rd'},
    'backend': {'name_zh': '后端', 'main_role_code': 'rd'},
    'architect': {'name_zh': '架构', 'main_role_code': 'architect'},
    'rd_general': {'name_zh': '研发', 'main_role_code': 'rd'},
    'unknown': {'name_zh': '未知', 'main_role_code': 'unknown'},
}

GROUP_DEFINITIONS = {
    'auth-nolimit': {'name_zh': '无限权认证', 'category': 'permission'},
    'jira-administrators': {'name_zh': 'Jira 管理员', 'category': 'permission'},
    'jira-software-users': {'name_zh': 'Jira 软件用户', 'category': 'permission'},
    'business r&d': {'name_zh': '业务研发', 'category': 'role'},
    'org-business': {'name_zh': '业务条线', 'category': 'biz'},
    'org-biz-od': {'name_zh': '组织发展', 'category': 'biz'},
    'org-biz-io': {'name_zh': '激励运营', 'category': 'biz'},
    'org-biz-ai': {'name_zh': 'AI业务', 'category': 'biz'},
    'org-biz-co': {'name_zh': '共用业务', 'category': 'biz'},
    'org-biz-bo': {'name_zh': '业务运营', 'category': 'biz'},
    'org-pd': {'name_zh': '产研中心', 'category': 'org'},
    'org-pd-coder': {'name_zh': '研发编码岗', 'category': 'role'},
    'org-pd-dev': {'name_zh': '研发开发岗', 'category': 'role'},
    'org-pd-frontside': {'name_zh': '前端', 'category': 'specialty'},
    'org-pd-frontside-h5': {'name_zh': '前端H5', 'category': 'specialty'},
    'org-pd-frontside-h5-1': {'name_zh': '前端H5', 'category': 'specialty'},
    'org-pd-frontside-native': {'name_zh': '原生', 'category': 'specialty'},
    'org-pd-serverside': {'name_zh': '后端', 'category': 'specialty'},
    'org-pd-serverside-a': {'name_zh': '后端A组', 'category': 'specialty'},
    'org-pd-serverside-b': {'name_zh': '后端B组', 'category': 'specialty'},
    'org-pd-serverside-b-net': {'name_zh': '后端.NET', 'category': 'specialty'},
    'org-pd-serverside-b-java': {'name_zh': '后端Java', 'category': 'specialty'},
    'org-pd-product': {'name_zh': '产品', 'category': 'specialty'},
    'org-pd-product-pm': {'name_zh': '产品经理', 'category': 'specialty'},
    'org-pd-qa': {'name_zh': '测试', 'category': 'specialty'},
    'org-pd-leader': {'name_zh': '产研负责人', 'category': 'org'},
    'org-pd-sp': {'name_zh': '服务端平台', 'category': 'specialty'},
    'org-epaas': {'name_zh': '架构', 'category': 'biz'},
    'org-sp': {'name_zh': '技术支持', 'category': 'biz'},
    'org-pm': {'name_zh': '项目管理', 'category': 'specialty'},
    'org-pm-fz': {'name_zh': '项目管理负责人', 'category': 'org'},
    'org-pm-cmg': {'name_zh': '项目管理组', 'category': 'org'},
    'product team': {'name_zh': '产品团队', 'category': 'specialty'},
}

SPECIALTY_GROUP_RULES = [
    ('product_manager', ['org-pd-product', 'org-pd-product-pm', 'product team', 'org-pm', 'org-pm-fz', 'org-pm-cmg']),
    ('qa_engineer', ['org-pd-qa']),
    ('frontend_native', ['org-pd-frontside-native']),
    ('frontend_h5', ['org-pd-frontside-h5']),
    ('frontend', ['org-pd-frontside']),
    ('backend_net', ['org-pd-serverside-b-net']),
    ('backend_java', ['org-pd-serverside-b-java']),
    ('backend', ['org-pd-serverside', 'org-pd-serverside-a', 'org-pd-serverside-b']),
    ('architect', ['org-epaas']),
    ('rd_general', ['business r&d', 'org-pd-coder', 'org-pd-dev', 'org-pd-sp']),
]


def get_user_details(username: str) -> dict:
    response = utils.api_request('user', method='GET', params={'username': username, 'expand': 'groups'})
    if not response['success']:
        return {'success': False, 'username': username, 'error': response}
    return {'success': True, 'data': response['data']}


def resolve_specialty(groups: List[str]) -> str:
    lowered = [group.lower() for group in groups]
    for specialty_code, candidates in SPECIALTY_GROUP_RULES:
        for candidate in candidates:
            if candidate.lower() in lowered:
                return specialty_code
    if 'org-pd' in lowered:
        return 'rd_general'
    return 'unknown'


def build_identity(display_name: str, username: str, groups: List[str]) -> dict:
    specialty_code = resolve_specialty(groups)
    specialty = SPECIALTY_DEFINITIONS[specialty_code]
    main_role = ROLE_DEFINITIONS[specialty['main_role_code']]
    group_mappings = []
    biz_lines = []
    for group in groups:
        meta = GROUP_DEFINITIONS.get(group.lower(), {'name_zh': group, 'category': 'unknown'})
        group_mappings.append({
            'group_name': group,
            'group_name_zh': meta['name_zh'],
            'group_category': meta['category'],
        })
        bizline_meta = BIZLINE_DEFINITIONS.get(group.lower())
        if bizline_meta:
            biz_lines.append({
                'group_name': group,
                'biz_line_name': bizline_meta['name_zh'],
            })
    return {
        'username': username,
        'display_name': display_name,
        'groups': groups,
        'group_mappings': group_mappings,
        'biz_lines': biz_lines,
        'main_role_code': specialty['main_role_code'],
        'main_role_name': main_role['name_zh'],
        'specialty_code': specialty_code,
        'specialty_name': specialty['name_zh'],
        'source': 'jira_user_groups',
    }


def fetch_identity(users: List[Dict[str, str]], workdir: Optional[str] = None) -> Dict[str, dict]:
    result: Dict[str, dict] = {}
    for user in users:
        username = user.get('username') or user.get('name') or ''
        display_name = user.get('displayName') or user.get('display_name') or username
        if not username:
            continue
        detail = get_user_details(username)
        if not detail['success']:
            result[display_name] = {
                'username': username,
                'display_name': display_name,
                'groups': [],
                'main_role_code': 'unknown',
                'main_role_name': ROLE_DEFINITIONS['unknown']['name_zh'],
                'specialty_code': 'unknown',
                'specialty_name': SPECIALTY_DEFINITIONS['unknown']['name_zh'],
                'source': 'jira_user_api_failed',
            }
            continue
        data = detail['data']
        groups = [item.get('name') for item in ((data.get('groups') or {}).get('items') or []) if item.get('name')]
        result[data.get('displayName') or display_name] = build_identity(
            data.get('displayName') or display_name,
            data.get('name') or username,
            groups,
        )
    output = {
        'role_definitions': ROLE_DEFINITIONS,
        'specialty_definitions': SPECIALTY_DEFINITIONS,
        'bizline_definitions': BIZLINE_DEFINITIONS,
        'group_definitions': GROUP_DEFINITIONS,
        'users': result,
    }
    if workdir:
        output_path = utils.get_work_file_path(workdir, 'review_identity_cache.json')
        review_common.save_json(output_path, output)
    return output


if __name__ == '__main__':
    utils.ensure_utf8_stdio()
    parser = argparse.ArgumentParser(description='基于 Jira 用户组识别角色与技术方向（UTF-8）')
    parser.add_argument('--workdir', type=str, required=True, help='工作目录')
    parser.add_argument('--user', action='append', default=[], help='用户，格式 username:displayName，可重复传入')
    args = parser.parse_args()
    utils.validate_workdir(args.workdir)
    utils.set_workdir(args.workdir)
    users = []
    for item in args.user:
        if ':' in item:
            username, display_name = item.split(':', 1)
            users.append({'username': username, 'displayName': display_name})
        else:
            users.append({'username': item, 'displayName': item})
    result = fetch_identity(users, args.workdir)
    utils.log_to_agent({'success': True, 'results': result})
