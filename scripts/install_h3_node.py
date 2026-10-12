"""Install the pinned node, preserving installed distributions and existing links."""
import argparse
import importlib.util
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

_spec = importlib.util.spec_from_file_location('h3_common', Path(__file__).with_name('h3_common.py'))
c = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(c)


def normalized(name):
    return re.sub(r'[-_.]+', '-', name).lower()


def pip_json(data):
    try:
        return c.json_loads(data)
    except c.H3Error:
        c.fail(1, 'pip', '計画/一覧の JSON 形式不明', '変更せず pip の形式を確認')


def distributions(data):
    if not isinstance(data, list):
        c.fail(1, 'pip', 'パッケージ一覧の形式不明', '仮想環境の pip を確認')
    result = {}
    for item in data:
        if not isinstance(item, dict) or not isinstance(item.get('name'), str) or not isinstance(item.get('version'), str):
            c.fail(1, 'pip', 'パッケージ項目の形式不明')
        name = normalized(item['name'])
        if name in result:
            c.fail(1, 'pip', 'パッケージ名の重複')
        result[name] = item['version']
    return result


def requirements(path):
    # Names + version/extras + PEP 508 platform markers only. No URLs/options/includes.
    pattern = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]*(?:\[[A-Za-z0-9_,.-]+\])?'
                         r'(?:\s*(?:===|==|!=|~=|>=|<=|>|<)\s*[A-Za-z0-9.*+_-]+(?:\s*,\s*(?:==|!=|~=|>=|<=|>|<)\s*[A-Za-z0-9.*+_-]+)*)?'
                         r'(?:\s*;\s*[A-Za-z0-9_\s"\x27().<>=!]+)?')
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.split('#', 1)[0].strip()
        if line and not pattern.fullmatch(line):
            c.fail(2, 'requirements', 'URL/VCS/index/他ファイル参照または形式不正', '固定ノードの requirements を確認')


def check_plan(report, before):
    if not isinstance(report, dict) or not isinstance(report.get('install'), list):
        c.fail(1, 'pip計画', '形式不明', '導入せず pip を確認')
    additions = {}
    for item in report['install']:
        if not isinstance(item, dict):
            c.fail(1, 'pip計画', '形式不明')
        metadata = item.get('metadata', {})
        if not isinstance(metadata, dict) or not isinstance(metadata.get('name'), str) or not isinstance(metadata.get('version'), str):
            c.fail(1, 'pip計画', '形式不明')
        name, version = normalized(metadata['name']), metadata['version']
        print(f'pip計画: {name} {version}')
        if name in before:
            c.fail(5, 'pip計画', f'既存配布物 {name} の入れ替え計画', '既存環境は非変更。対応版・専用環境を確認')
        additions[name] = version
    return additions


def check_link(path, target):
    if path.exists() or path.is_symlink():
        if not path.exists() or c.entity_relative(path, target) != ():
            c.fail(5, '補助リンク', '既存の別実体・切れたリンク', c.REPAIR)
        return False
    return True


def check_permission(path):
    parent = path
    while not parent.exists():
        parent = parent.parent
    if not parent.is_dir() or not os.access(parent, os.W_OK | os.X_OK):
        c.fail(1, '配置', '書込権限不足', '配置先と権限を確認（管理者権限は要求しない）')


def check_checkout(git, target, timeout):
    if target.is_symlink() or not target.is_dir():
        c.fail(5, 'ノード', '非 Git または不正配置', c.REPAIR)
    try:
        head = c.command([git, '-C', target, 'rev-parse', 'HEAD'], timeout, 'git').stdout.strip()
        dirty = c.command([git, '-C', target, 'status', '--porcelain', '--untracked-files=no'], timeout, 'git').stdout.strip()
    except c.H3Error as exc:
        if exc.code == 7:
            raise
        c.fail(5, 'ノード', '非 Git または読取不能', c.REPAIR)
    if head != c.NODE_SHA or dirty:
        c.fail(5, 'ノード', '固定 HEAD 不一致または追跡変更あり', c.REPAIR)


def install(args):
    progress = dict(stage='事前検査', changed=False)
    try:
        return install_steps(args, progress)
    except (c.H3Error, OSError, ValueError, TypeError, KeyError) as exc:
        changed = progress['changed']
        state = '変更済み（途中の可能性あり）' if changed else '未変更'
        retry = ('そのまま再実行しない。本人が pip check・配布物差分・配置を確認後に再実行'
                 if changed else '原因への対処後に再実行可')
        if isinstance(exc, c.H3Error):
            code, cause, remedy = exc.code, exc.cause, exc.remedy
        else:
            code, cause, remedy = 1, '入力またはファイル処理に失敗', '配置・権限・形式を確認'
        c.fail(code, 'install ' + progress['stage'], f'{cause}; 仮想環境: {state}; {retry}', remedy)


def install_steps(args, progress):
    p = c.paths(args)
    comfy, venv, models = p['comfy_root'], p['venv'], p['models_dir'].resolve()
    target = comfy / 'custom_nodes' / c.NODE_DIR
    entrance = comfy / 'models/minimax_h3'
    for path in (target, venv, models, entrance, venv / 'bin/ffmpeg', venv / 'bin/ffprobe'):
        c.writable(path)
    if not (comfy / 'custom_nodes').is_dir() or not (comfy / 'main.py').is_file():
        c.fail(1, 'ComfyUI', '本体の構成が無い', 'Comfy Desktop の初回 GUI 起動と --comfy-root を確認')
    python = c.executable(venv / 'bin/python', item='venv Python')
    if not (venv / 'pyvenv.cfg').is_file():
        c.fail(1, 'venv', '仮想環境の構成が無い', 'Comfy Desktop の初回 GUI 起動と --venv を確認')
    git = c.executable(args.git, search=True, item='git')
    graph = c.load_graph()
    ffmpeg, ffprobe = c.video_tools(graph)
    links = [(venv / 'bin/ffmpeg', ffmpeg), (venv / 'bin/ffprobe', ffprobe), (entrance, models)]
    for path in (target.parent, venv / 'bin', models, entrance.parent):
        check_permission(path)
    # All conflicts are checked before acquisition/pip changes.
    needed_links = [(link, real) for link, real in links if check_link(link, real)]
    if models.exists() and not models.is_dir():
        c.fail(5, 'モデル', '共有先がディレクトリ以外', c.REPAIR)
    if target.exists() or target.is_symlink():
        check_checkout(git, target, args.command_timeout)
    pip = [python, '-I', '-m', 'pip', '--isolated']
    c.command(pip + ['--version'], args.command_timeout, 'pip', code=1)
    try:
        c.command(pip + ['check'], args.command_timeout, 'pip')
    except c.H3Error as exc:
        if exc.code == 7:
            raise
        c.fail(5, 'pip事前検査', '既存環境の不整合を先に解消', '本人が pip check と既存依存を確認')
    before = distributions(pip_json(c.command(pip + ['list', '--format=json'], args.command_timeout, 'pip').stdout))
    print('ComfyUI を停止してから導入する。既存パッケージを入れ替える計画は拒否する。')
    with tempfile.TemporaryDirectory(prefix='h3-install-') as temporary:
        temporary = Path(temporary)
        staging = temporary / 'node'
        source = target if target.exists() else staging
        if source == staging:
            progress['stage'] = '取得'
            c.command([git, 'init', staging], args.command_timeout, 'git')
            c.command([git, '-C', staging, 'fetch', '--depth=1', c.NODE_REPO, c.NODE_SHA], args.command_timeout, 'git')
            c.command([git, '-C', staging, 'checkout', '--detach', 'FETCH_HEAD'], args.command_timeout, 'git')
            check_checkout(git, staging, args.command_timeout)
        req = source / 'requirements.txt'
        progress['stage'] = '計画'
        requirements(req)
        report = temporary / 'pip-report.json'
        install_args = ['install', '--only-binary', ':all:', '--index-url', 'https://pypi.org/simple', '-r', req]
        try:
            c.command(pip + install_args + ['--dry-run', '--report', report], args.command_timeout, 'pip')
        except c.H3Error as exc:
            if exc.code == 7:
                raise
            c.fail(1, 'pip計画', 'この環境向けの wheel が無い依存がある、または計画に失敗', 'wheel の対応環境・取得先への接続を確認（ソースからビルドしない）')
        try:
            planned = check_plan(pip_json(report.read_bytes()), before)
        except OSError:
            c.fail(1, 'pip計画', 'report 読取不能', '導入せず pip の出力を確認')
        if planned:
            progress.update(stage='依存導入', changed=True)
            c.command(pip + install_args, args.command_timeout, 'pip')
        progress['stage'] = '事後検査'
        c.command(pip + ['check'], args.command_timeout, 'pip')
        after = distributions(pip_json(c.command(pip + ['list', '--format=json'], args.command_timeout, 'pip').stdout))
        if any(after.get(name) != version for name, version in before.items()):
            progress['changed'] = True
            c.fail(6, 'pip事後検査', '既存版の変化', '自動巻戻しなし。本人が pip check と差分を確認')
        if any(after.get(name) != version for name, version in planned.items()):
            c.fail(6, 'pip事後検査', '計画した新規依存が不一致', '本人が pip check を確認')
        print('既存版不変 / pip check PASS')
        print('追加配布物: ' + (', '.join(sorted(set(after) - set(before))) or '（なし）'))
        # Recheck checkout and links immediately before publishing into the instance.
        progress['stage'] = '配置'
        check_checkout(git, source, args.command_timeout)
        for link, real in links:
            check_link(link, real)
        if source == staging:
            if target.exists() or target.is_symlink():
                c.fail(5, 'ノード', '導入中に配置先が出現', c.REPAIR)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(staging), str(target))
        models.mkdir(parents=True, exist_ok=True)
        progress['stage'] = 'リンク'
        for link, real in needed_links:
            if check_link(link, real):
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(real)
    print(c.display(f'導入完了: {target}。ComfyUI を再起動して4ノードを診断'))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    c.add_paths(parser, ('instance', 'comfy_root', 'venv', 'models_dir'))
    parser.add_argument('--git', default='git', help='既定: PATH から絶対パス解決')
    parser.add_argument('--command-timeout', type=c.positive, default=1800)
    return install(c.parse(parser))


if __name__ == '__main__':
    sys.exit(c.cli(main))
