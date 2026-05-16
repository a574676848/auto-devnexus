import argparse
import sys
import os
try:
    import utils
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import utils


def get_issue_comments(issue_key: str):
    """
    获取单个工单的评论列表
    """
    response = utils.api_request(f'issue/{issue_key}/comment', method='GET')

    if not response['success']:
        utils.log_to_agent(response)
        sys.exit(0)

    data = response.get('data', {})
    comments = data.get('comments', [])
    clean_comments = []
    for c in comments:
        author = c.get('author', {}) or {}
        update_author = c.get('updateAuthor', {}) or {}
        clean_comments.append({
            'id': c.get('id'),
            'body': c.get('body'),
            'author': author.get('displayName') or author.get('name'),
            'author_key': author.get('name'),
            'update_author': update_author.get('displayName') or update_author.get('name'),
            'created': c.get('created'),
            'updated': c.get('updated')
        })

    utils.log_to_agent({
        'success': True,
        'issue': issue_key,
        'total_comments': len(clean_comments),
        'comments': clean_comments
    })


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='查看 Jira 7.5.2 单个工单评论')
    parser.add_argument('--issue', type=str, required=True, help='工单编号 (如 TEST-101)')
    parser.add_argument('--workdir', type=str, required=True, help='工作目录(用户空间tmp路径)')

    args = parser.parse_args()
    utils.validate_workdir(args.workdir)
    utils.set_workdir(args.workdir)
    get_issue_comments(args.issue)
