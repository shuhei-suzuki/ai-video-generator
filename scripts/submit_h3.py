"""Submit the fixed graph or verify history, then inspect the saved video."""
import argparse
import copy
import importlib.util
from pathlib import Path
import re
import sys
import time

_spec = importlib.util.spec_from_file_location('h3_common', Path(__file__).with_name('h3_common.py'))
c = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(c)


def history_graph(entry):
    try:
        prompt = entry['prompt']
        if not isinstance(prompt, list) or len(prompt) < 3:
            raise ValueError
        return prompt[2]
    except (KeyError, TypeError, ValueError):
        c.fail(8, '履歴', '実投入グラフが不明', '同じ ComfyUI 起動中の履歴を確認')


def wait_history(base, prompt_id, deadline, http_timeout, poll, require_present=False):
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            c.fail(7, '生成', '期限超過（サーバー生成は継続しうる）', '再投入せず履歴・出力を確認')
        try:
            response = c.request_json(base + '/history/' + prompt_id, timeout=min(http_timeout, remaining))
        except c.H3Error:
            # A request cut short by the overall deadline is a timeout, not an API failure.
            if time.monotonic() >= deadline:
                c.fail(7, '生成', '期限超過（サーバー生成は継続しうる）', '再投入せず履歴・出力を確認')
            raise
        if not isinstance(response, dict):
            c.fail(6, '履歴', '応答構造不正', 'API を確認')
        entry = response.get(prompt_id)
        if entry is None and require_present:
            c.fail(2, '履歴', '履歴に無い ID。実行中・待機中の可能性（完了後に再実行）、または ComfyUI の再起動で履歴が消えた',
                   '再投入しない。出力ディレクトリと ComfyUI の画面で状態を確認')
        if entry is not None:
            if not isinstance(entry, dict) or not isinstance(entry.get('status'), dict):
                c.fail(6, '履歴', '状態構造不正', '履歴を確認')
            status = entry['status']
            if status.get('status_str') == 'error' or any(isinstance(m, list) and m and m[0] == 'execution_error' for m in status.get('messages', [])):
                c.fail(6, '生成', '実行エラー（応答本文は非表示）', 'ComfyUI の画面・ローカル履歴で原因を確認')
            if status.get('completed') is True:
                if time.monotonic() >= deadline:
                    c.fail(7, '生成', '期限超過', '履歴・出力を確認')
                return entry
        time.sleep(min(poll, max(0, deadline - time.monotonic())))


def verify_entry(entry, repository, registered, output_dir, command_timeout, submitted=None):
    actual = history_graph(entry)
    try:
        values = c.validate_public({k: actual['2']['inputs'].get(k) for k in c.PUBLIC})
    except (c.H3Error, KeyError, TypeError, AttributeError):
        c.fail(8, '履歴照合', '履歴の公開値の型が不正', '履歴の公開6項目を確認。外部コマンドは起動しない')
    # Both comparisons happen before output inspection or ANY external execution.
    c.compare_graph(actual, repository)
    if registered is not None:
        c.compare_graph(actual, registered['workflow'])
    if submitted is not None:
        c.compare_graph(actual, submitted)
        if any(actual['2']['inputs'][k] != submitted['2']['inputs'][k] for k in c.PUBLIC):
            c.fail(8, '履歴照合', '直接投入の公開値が不一致', '対象 prompt_id を確認')
    print(c.display('履歴公開6項目: ' + c.json.dumps(values, ensure_ascii=False)))
    other = '登録項目 id=' + c.json.dumps(registered.get('id'), ensure_ascii=True) if registered is not None else '登録項目なし'
    print('履歴照合 PASS: ノード構成・固定入力 / リポジトリのワークフロー / ' + other)
    video = c.output_video(entry, output_dir)
    print(c.display(f'保存先（存在確認済み）: {video}'))
    # Never derive executables from the library or history.
    c.inspect_video(video, values['width'], values['height'], repository, command_timeout)
    return 0


def submit(args):
    base = c.local_url(args.comfy_url)
    p = c.paths(args)
    graph = c.load_graph()
    registered = None
    if args.verify_history:
        _, registered = c.read_library(p['data_dir'] / 'workflows.json')
    started = time.monotonic()
    deadline = started + args.timeout
    submitted = None
    if args.verify_history:
        prompt_id = args.verify_history
    else:
        values = c.validate_public(dict(prompt=args.prompt, width=args.width, height=args.height,
                                       duration_seconds=args.seconds, steps=args.steps, seed=args.seed))
        submitted = copy.deepcopy(graph)
        submitted['2']['inputs'].update(values)
        c.compare_graph(submitted, graph)
        c.video_tools(graph)  # prerequisite before submitting a generation
        response = c.request_json(base + '/prompt', {'prompt': submitted},
                                  min(args.http_timeout, args.timeout))
        if not isinstance(response, dict) or response.get('node_errors') or response.get('error'):
            c.fail(6, '投入', '拒否・node_errors', 'ComfyUI の画面で原因を確認')
        prompt_id = response.get('prompt_id')
    if not isinstance(prompt_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', prompt_id):
        c.fail(2 if args.verify_history else 6, 'prompt_id', 'ID 形式不正')
    print('prompt_id=' + prompt_id, flush=True)
    entry = wait_history(base, prompt_id, deadline, args.http_timeout, args.poll_interval,
                         require_present=bool(args.verify_history))
    print(f'完了までの経過時間: {time.monotonic() - started:.1f} 秒（キャッシュの可能性あり）')
    return verify_entry(entry, graph, registered, p['output_dir'], args.command_timeout, submitted)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    c.add_paths(parser, ('output_dir', 'data_dir'))
    defaults = c.read_json(c.WORKFLOW)['2']['inputs']
    parser.add_argument('--prompt', default=defaults['prompt'])
    parser.add_argument('--width', type=int, default=64)
    parser.add_argument('--height', type=int, default=64)
    parser.add_argument('--seconds', type=float, default=1.0)
    parser.add_argument('--steps', type=int, default=5)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--verify-history', metavar='ID', help='新規投入なしで登録項目とリポジトリ双方に照合')
    parser.add_argument('--comfy-url', default='http://127.0.0.1:8188')
    parser.add_argument('--http-timeout', type=c.positive, default=30)
    parser.add_argument('--timeout', type=c.positive, default=7200)
    parser.add_argument('--poll-interval', type=c.positive, default=2)
    parser.add_argument('--command-timeout', type=c.positive, default=300)
    return submit(c.parse(parser))


if __name__ == '__main__':
    sys.exit(c.cli(main))
