"""Register the repository workflow without overwriting existing entries."""
import argparse
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import stat
import sys
import uuid

_spec = importlib.util.spec_from_file_location('h3_common', Path(__file__).with_name('h3_common.py'))
c = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(c)

DESCRIPTION = (
    'MiniMax H3 text-to-video with stereo audio, MLX on Apple Silicon. '
    'Use comfyui_workflow with action: run, this library id and parameters; use mode: sync. '
    'Async is unverified in this configuration. Write the prompt in English, describing the scene and sounds. '
    'Width and height must be multiples of 32; verified sizes are 768x448 (landscape) and 448x768 (portrait). '
    'Use duration_seconds up to 15. Defaults: 768x448, 5 seconds, steps 9, seed 0 (random). '
    'Approximate generation times: 768x448 / 5 seconds takes 10-14 minutes; '
    '448x768 / 15 seconds takes 48 minutes; 64x64 / 1 second / steps 5 takes about 1 minute. '
    'Set timeout_ms longer than generation: 1800000 for 5 seconds, 4200000 for 15 seconds. '
    'The default 900000 may time out the chat before a long generation finishes; '
    'ComfyUI continues generating, so do not resubmit. Run only one generation at a time. '
    'Videos are saved under minimax_h3/ in the ComfyUI output directory. '
    'Do not change model paths or ffmpeg_path.'
)
TAGS = ['video', 'minimax-h3']


def differences(old, new, prefix=''):
    if isinstance(old, dict) and isinstance(new, dict):
        result = []
        for key in sorted(set(old) | set(new)):
            path = prefix + '/' + key
            if key not in old or key not in new:
                result.append(path)
            else:
                result.extend(differences(old[key], new[key], path))
        return result
    if old != new:
        return [prefix]
    return []


def register(args):
    graph = c.load_graph()
    newparams = c.parameters(graph)
    c.parameter_contract(newparams)
    data = c.paths(args)['data_dir']
    path = data / 'workflows.json'
    c.writable(data, library=True)
    c.writable(path, library=True)
    # Snapshot BEFORE parsing, so a change during the read is detected before replace.
    if path.is_symlink():
        c.fail(2, 'ライブラリ', 'リンクは禁止')
    snapshot = (path.stat(), path.read_bytes()) if path.exists() else None
    entries, match = c.read_library(path)
    if match:
        try:
            oldparams = c.parameter_contract(match.get('parameters'))
        except c.H3Error:
            oldparams = None
        changes = differences(match['workflow'], graph, 'workflow')
        changes.extend(differences(match.get('description'), DESCRIPTION, 'description'))
        changes.extend(differences(match.get('tags'), TAGS, 'tags'))
        if oldparams != c.parameter_contract(newparams):
            if isinstance(match.get('parameters'), list):
                for i, p in enumerate(match['parameters']):
                    if isinstance(p, dict):
                        new = next((n for n in newparams if n['name'] == p.get('name')), {})
                        changes.extend(differences({k: v for k, v in p.items() if k != 'id'},
                                                   {k: v for k, v in new.items() if k != 'id'},
                                                   'parameters/' + str(i)))
            changes.append('parameters')
        if changes:
            print('差分所在: ' + c.json.dumps(changes, ensure_ascii=True))
            c.fail(5, '登録', '同名別内容（原本保持）', c.REREGISTER)
        print(f'{c.NAME}: 変更なし id=' + c.json.dumps(match['id'], ensure_ascii=True))
        return 0
    ps = c.executable(args.ps, search=True, item='ps')
    process = c.command([ps, '-axo', 'comm='], timeout=30).stdout
    if any(Path(line.strip()).name == args.harness_process for line in process.splitlines()):
        print('警告: Harness 起動中。同時更新は保証しない。終了してからの登録を推奨', file=sys.stderr)
    entry = dict(id=str(uuid.uuid4()), name=c.NAME,
                 description=DESCRIPTION,
                 workflow=graph, parameters=newparams, tags=TAGS,
                 updatedAt=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'))
    entries.append(entry)
    mode = stat.S_IMODE(snapshot[0].st_mode) if snapshot else 0o600
    c.atomic_json(path, entries, snapshot, mode)
    print(c.display(f'登録: {c.NAME} id={entry["id"]} -> {path}'))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    c.add_paths(parser, ('data_dir',))
    parser.add_argument('--harness-process', default='DeepSeek Harness', help='既定: DeepSeek Harness（完全名）')
    parser.add_argument('--ps', default='ps', help='既定: PATH から絶対パス解決')
    return register(c.parse(parser))


if __name__ == '__main__':
    sys.exit(c.cli(main))
