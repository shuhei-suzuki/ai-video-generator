"""Regenerate metadata for the three pinned revisions; never download weights."""
import argparse
import copy
import fnmatch
import importlib.util
from pathlib import Path
import sys

_spec = importlib.util.spec_from_file_location('h3_common', Path(__file__).resolve().parents[1] / 'scripts/h3_common.py')
c = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(c)


def from_api(model, data):
    if not isinstance(data, dict) or data.get('sha') != model['revision']:
        c.fail(6, 'HF API', '固定 SHA 不一致', '固定リビジョンの応答を確認')
    if not isinstance(data.get('siblings'), list):
        c.fail(2, 'HF API', 'siblings 不正')
    files = []
    names = set()
    for sibling in data['siblings']:
        if not isinstance(sibling, dict):
            c.fail(2, 'HF API', 'ファイル項目不正')
        name = c.relpath(sibling.get('rfilename'))
        size = sibling.get('size')
        if name in names or type(size) is not int or size < 0:
            c.fail(2, 'HF API', '重複パスまたはサイズ不正')
        names.add(name)
        if name != '.gitattributes' and any(fnmatch.fnmatchcase(name, pattern) for pattern in model['include']):
            files.append(dict(path=name, size=size))
    files.sort(key=lambda f: f['path'])
    return dict(**model, files=files, total_bytes=sum(f['size'] for f in files))


def make(args):
    output = Path(args.output).expanduser().absolute()
    c.writable(output)
    snapshot = (output.stat(), output.read_bytes()) if output.exists() else None
    if output.is_symlink():
        c.fail(2, '一覧出力', 'リンクは禁止')
    result = dict(schema=1, models=[])
    for model in c.MODELS:
        url = f"https://huggingface.co/api/models/{model['repo']}/revision/{model['revision']}?blobs=true"
        item = from_api(model, c.request_json(url, timeout=args.http_timeout))
        result['models'].append(item)
        print(f"{model['key']}: {len(item['files'])} 件 {item['total_bytes']} bytes")
    models = c.validate_manifest(result)
    if args.compare_dir:
        rows = c.inspect_models(Path(args.compare_dir).expanduser(), models)
        c.model_summary(rows)
        if any(s != '完了' for _, _, s in rows):
            c.fail(1, '一覧照合', '全件一致せず（出力非変更）', '配置・サイズを確認')
    c.atomic_json(output, result, snapshot)
    print(c.display(f'一覧出力: {output}'))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default=str(c.MANIFEST), help='既定: リポジトリ config の一覧')
    parser.add_argument('--compare-dir', help='任意: ローカル models/minimax_h3 の全件照合')
    parser.add_argument('--http-timeout', type=c.positive, default=30)
    return make(c.parse(parser))


if __name__ == '__main__':
    sys.exit(c.cli(main))
