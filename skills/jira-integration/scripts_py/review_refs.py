import argparse
import os
import sys
import urllib.request

try:
    import utils
    import review_common
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import utils
    import review_common


def read_local_file(path: str) -> dict:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {'source': 'local_file', 'path': path, 'success': True, 'content': content}
    except Exception as e:
        return {'source': 'local_file', 'path': path, 'success': False, 'error': str(e)}


def read_url(url: str) -> dict:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode('utf-8', errors='replace')
        lower = raw.lower()
        is_login_page = '统一身份认证' in raw or 'sign in' in lower or 'login' in lower and 'dingtalk' in lower
        is_shell_page = 'mockplus' in lower and '<html' in lower
        valid = not is_login_page and not is_shell_page
        note = ''
        if is_login_page:
            note = '抓到的是登录页，未获取正文。若当前环境支持 openclaw browser，应尝试 browser 打开后读取正文。'
        elif is_shell_page:
            note = '抓到的是原型站壳页，未直接提取到业务正文。若当前环境支持 openclaw browser，应尝试 browser 读取。'
        return {
            'source': 'url',
            'url': url,
            'success': True,
            'content': raw,
            'fetch_mode': 'urllib',
            'is_valid_reference': valid,
            'note': note,
        }
    except Exception as e:
        return {'source': 'url', 'url': url, 'success': False, 'error': str(e), 'suggestion': '如果当前环境支持 openclaw browser，建议后续补充 browser 读取；若仍失败，请让用户上传参考资料。'}


def collect_refs(issue_key: str, workdir: str, local_files: list, urls: list) -> dict:
    bundle = review_common.load_json(review_common.bundle_path(workdir, issue_key))
    description_urls = bundle.get('description_urls', [])
    results = []
    for file_path in local_files:
        results.append(read_local_file(file_path))
    merged_urls = []
    seen = set()
    for url in urls + description_urls:
        if url not in seen:
            seen.add(url)
            merged_urls.append(url)
    for url in merged_urls:
        results.append(read_url(url))
    refs = {
        'issue_key': issue_key,
        'local_files': local_files,
        'input_urls': urls,
        'description_urls': description_urls,
        'items': results,
        'has_reference_material': any(item.get('success') and item.get('content') and item.get('is_valid_reference', True) for item in results),
        'guidance': '若参考资料读取失败，优先建议用户上传原始文档；若没有参考资料，则仅基于 Jira 数据继续分析。'
    }
    output_path = review_common.refs_path(workdir, issue_key)
    review_common.save_json(output_path, refs)
    return {'refs_path': output_path, 'refs': refs}


if __name__ == '__main__':
    utils.ensure_utf8_stdio()
    parser = argparse.ArgumentParser(description='收集项目复盘参考资料（UTF-8）')
    parser.add_argument('--issue', type=str, required=True, help='主工单 KEY')
    parser.add_argument('--workdir', type=str, required=True, help='工作目录')
    parser.add_argument('--file', action='append', default=[], help='本地参考文件路径，可重复传入')
    parser.add_argument('--url', action='append', default=[], help='参考资料 URL，可重复传入')
    args = parser.parse_args()
    utils.validate_workdir(args.workdir)
    utils.set_workdir(args.workdir)
    result = collect_refs(args.issue, args.workdir, args.file, args.url)
    utils.log_to_agent({'success': True, 'issue_key': args.issue, 'refs_path': result['refs_path'], 'has_reference_material': result['refs']['has_reference_material'], 'description_urls': result['refs']['description_urls']})
