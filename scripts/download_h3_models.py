"""Acquire only missing files, after the owner's license consent."""
import argparse
import importlib.util
import math
import os
from pathlib import Path
import shutil
import sys

_spec = importlib.util.spec_from_file_location('h3_common', Path(__file__).with_name('h3_common.py'))
c = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(c)


def consent(accepted):
    print('ライセンス原文（確認日 2026-10-12、要約は非正本。原文優先）:')
    for m in c.MODELS:
        filename = 'README.md' if m['key'] == 'turbo' else 'LICENSE'
        print(f"https://huggingface.co/{m['repo']}/blob/{m['revision']}/{filename}")
    print('Turbo の apache-2.0 表示の原文: https://www.apache.org/licenses/LICENSE-2.0')
    print('H3: 米国・EU・英国・韓国は利用対象外。年商2,000万USD超は別途許諾。')
    print('派生 INT8 / Turbo にも H3 条件が及ぶ前提。本人だけが同意・取得する。')
    if accepted:
        return
    if sys.stdin.isatty():
        try:
            if input('原文を読んだ本人の同意: yes と入力: ').strip() == 'yes':
                return
        except EOFError:
            pass
    c.fail(3, '同意', '未同意', '原文を読んだ本人が yes または --accept-license を指定')


def capacity(root, remaining, limit):
    existing = root.resolve()
    while not existing.exists():
        existing = existing.parent
    real = shutil.disk_usage(existing).free
    free = real if limit is None else min(real, limit)
    margin = max(1024 ** 3, (remaining + 19) // 20)
    needed = remaining + margin
    print(f'容量: R={remaining} 余裕={margin} 必要={needed} 実測free={real} 有効free={free} N={limit} bytes')
    print(f'必要={needed / 1e9:.3f} GB / {needed / 1024**3:.3f} GiB')
    if free < needed:
        c.fail(4, '容量', '配置先ボリュームの空き不足', '不要なデータを本人が退避。Qwen/キャッシュ/生成物分も確保')


def hub_client():
    # Must run before importing hub/constants, in an isolated process environment.
    isolated = c.child_env('hub')
    os.environ.clear()
    os.environ.update(isolated)
    try:
        import huggingface_hub
    except ImportError:
        c.fail(1, 'huggingface_hub', '未導入', 'ComfyUI 仮想環境の Python -I を使用（追加導入しない）')
    try:
        version = tuple(int(p) for p in huggingface_hub.__version__.split('.')[:2])
        if version < (1, 0):
            raise ValueError
    except (AttributeError, ValueError):
        c.fail(1, 'huggingface_hub', '1.0以上が必要', '指定の ComfyUI 仮想環境を確認')
    return huggingface_hub.hf_hub_download


def acquire(args):
    p = c.paths(args)
    root = p['models_dir'].resolve()
    c.writable(root)
    models = [m for m in c.validate_manifest(c.read_json(p['manifest'])) if m['key'] in args.models]
    print(c.display(f'配置先: {root}'))
    rows = c.inspect_models(root, models)
    c.model_summary(rows)
    if any(state not in ('未取得', '完了') for _, _, state in rows):
        c.fail(5, 'モデル', '取得途中・サイズ不一致・不正データ', c.REPAIR)
    pending = [(m, f) for m, f, state in rows if state == '未取得']
    if not pending:
        print('すべて完了済み。変更なし')
        return 0
    consent(args.accept_license)
    remaining = sum(f['size'] for _, f in pending)
    capacity(root, remaining, args.test_free_bytes)
    download = hub_client()
    root.mkdir(parents=True, exist_ok=True)
    capacity(root, remaining, args.test_free_bytes)
    for m, f in pending:
        current = c.inspect_models(root, models)
        if any(s not in ('未取得', '完了') for _, _, s in current):
            c.fail(5, 'モデル', '取得直前に状態変化', c.REPAIR)
        state = next(s for mm, ff, s in current if mm['key'] == m['key'] and ff['path'] == f['path'])
        remaining = sum(ff['size'] for _, ff, s in current if s == '未取得')
        if state == '完了':
            continue
        capacity(root, remaining, args.test_free_bytes)
        c.safe_model_path(root, m['local_dir'] + '/' + f['path'])
        try:
            download(repo_id=m['repo'], filename=f['path'], revision=m['revision'],
                     local_dir=str(root / m['local_dir']), token=False)
        except Exception:
            c.fail(6, '取得', '標準 hub 転送に失敗（途中データを保持）', c.REPAIR)
    final = c.inspect_models(root, models)
    c.model_summary(final)
    if any(s != '完了' for _, _, s in final):
        c.fail(6, '取得', '取得後のサイズ照合に失敗', c.REPAIR)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    c.add_paths(parser, ('models_dir', 'manifest'))
    parser.add_argument('--models', nargs='+', choices=('base', 'int8', 'turbo'), default=['base', 'int8', 'turbo'])
    parser.add_argument('--accept-license', action='store_true', help='原文を読んだ本人の同意。エージェントは使用しない')
    parser.add_argument('--test-free-bytes', type=c.nonnegative, help='有効free=min(実測,N)。容量不足の再現用')
    return acquire(c.parse(parser))


if __name__ == '__main__':
    sys.exit(c.cli(main))
