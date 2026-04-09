import argparse
import os
import sys

try:
    import utils
    import review_export
    import review_refs
    import review_analyze
    import review_render
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import utils
    import review_export
    import review_refs
    import review_analyze
    import review_render


def generate(issue_key: str, workdir: str, files: list, urls: list, roles: list) -> dict:
    export_result = review_export.export_bundle(issue_key, workdir)
    refs_result = review_refs.collect_refs(issue_key, workdir, files, urls)
    analyze_result = review_analyze.analyze(issue_key, workdir, roles)
    render_result = review_render.render_report(issue_key, workdir)
    return {
        'bundle_path': export_result['bundle_path'],
        'refs_path': refs_result['refs_path'],
        'analysis_path': analyze_result['analysis_path'],
        'output_path': render_result['output_path'],
        'has_reference_material': refs_result['refs']['has_reference_material'],
    }


if __name__ == '__main__':
    utils.ensure_utf8_stdio()
    parser = argparse.ArgumentParser(description='一键生成 Jira 项目复盘报告（UTF-8）')
    parser.add_argument('--issue', type=str, required=True, help='主工单 KEY')
    parser.add_argument('--workdir', type=str, required=True, help='工作目录')
    parser.add_argument('--file', action='append', default=[], help='本地参考文件路径，可重复传入')
    parser.add_argument('--url', action='append', default=[], help='参考资料 URL，可重复传入')
    parser.add_argument('--role', action='append', default=[], help='角色映射，格式 姓名=角色，可重复传入')
    args = parser.parse_args()

    utils.validate_workdir(args.workdir)
    utils.set_workdir(args.workdir)
    result = generate(args.issue, args.workdir, args.file, args.url, args.role)
    utils.log_to_agent({
        'success': True,
        'issue_key': args.issue,
        'bundle_path': result['bundle_path'],
        'refs_path': result['refs_path'],
        'analysis_path': result['analysis_path'],
        'output_path': result['output_path'],
        'has_reference_material': result['has_reference_material'],
    })
