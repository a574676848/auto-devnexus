import argparse
import os
import sys

try:
    import utils
    import review_common
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import utils
    import review_common


def fetch_issue(issue_key: str) -> dict:
    fields = '*all'
    expand = 'names,schema'
    response = utils.api_request(f'issue/{issue_key}', method='GET', params={'fields': fields, 'expand': expand})
    if not response['success']:
        utils.log_to_agent(response)
        sys.exit(0)
    issue = response['data']
    issue['fields']['comment'] = fetch_comments(issue_key)
    issue['fields']['worklog'] = fetch_worklogs(issue_key)
    return issue


def fetch_comments(issue_key: str) -> dict:
    start_at = 0
    max_results = 100
    comments = []
    total = None
    while total is None or start_at < total:
        response = utils.api_request(f'issue/{issue_key}/comment', method='GET', params={'startAt': start_at, 'maxResults': max_results})
        if not response['success']:
            utils.log_to_agent(response)
            sys.exit(0)
        data = response['data']
        total = data.get('total', 0)
        comments.extend(data.get('comments', []))
        start_at += data.get('maxResults', max_results)
    return {'startAt': 0, 'maxResults': len(comments), 'total': len(comments), 'comments': comments}


def fetch_worklogs(issue_key: str) -> dict:
    start_at = 0
    max_results = 100
    worklogs = []
    total = None
    while total is None or start_at < total:
        response = utils.api_request(f'issue/{issue_key}/worklog', method='GET', params={'startAt': start_at, 'maxResults': max_results})
        if not response['success']:
            utils.log_to_agent(response)
            sys.exit(0)
        data = response['data']
        total = data.get('total', 0)
        worklogs.extend(data.get('worklogs', []))
        start_at += data.get('maxResults', max_results)
    return {'startAt': 0, 'maxResults': len(worklogs), 'total': len(worklogs), 'worklogs': worklogs}


def search_related_keys(issue_key: str, max_results: int = 100) -> list:
    jql = f'parent = {issue_key} OR issue in linkedIssues("{issue_key}")'
    start_at = 0
    keys = []
    total = None
    while total is None or start_at < total:
        response = utils.api_request('search', method='GET', params={
            'jql': jql,
            'startAt': start_at,
            'maxResults': max_results,
            'fields': 'key'
        })
        if not response['success']:
            utils.log_to_agent(response)
            sys.exit(0)
        data = response['data']
        total = data.get('total', 0)
        keys.extend(issue.get('key') for issue in data.get('issues', []))
        start_at += data.get('maxResults', max_results)
    return keys


def export_bundle(issue_key: str, workdir: str) -> dict:
    main_issue = fetch_issue(issue_key)
    related_keys = search_related_keys(issue_key)
    related_issues = [fetch_issue(key) for key in related_keys]
    bundle = {
        'issue_key': issue_key,
        'exported_at': review_common.now_compact(),
        'main_issue': main_issue,
        'related_keys': related_keys,
        'related_total': len(related_issues),
        'related_issues': related_issues,
        'description_urls': review_common.extract_urls_from_issue(main_issue),
    }
    output_path = review_common.bundle_path(workdir, issue_key)
    review_common.save_json(output_path, bundle)
    return {'bundle_path': output_path, 'bundle': bundle}


if __name__ == '__main__':
    utils.ensure_utf8_stdio()
    parser = argparse.ArgumentParser(description='导出 Jira 项目复盘数据包（UTF-8）')
    parser.add_argument('--issue', type=str, required=True, help='主工单 KEY')
    parser.add_argument('--workdir', type=str, required=True, help='工作目录')
    args = parser.parse_args()
    utils.validate_workdir(args.workdir)
    utils.set_workdir(args.workdir)
    result = export_bundle(args.issue, args.workdir)
    utils.log_to_agent({'success': True, 'issue_key': args.issue, 'bundle_path': result['bundle_path'], 'related_total': result['bundle']['related_total'], 'description_urls': result['bundle']['description_urls']})
