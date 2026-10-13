"""Shared contracts for the local H3 tools (Python 3.11+)."""
import argparse
import copy
import http.client
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'config/h3_models.manifest.json'
WORKFLOW = ROOT / 'workflows/minimax_h3_t2v_api.json'
NODE_SHA = 'ab1756d571ebb14fed3168354dae42966a04348b'
NODE_REPO = 'https://github.com/Argus-AiTeam/ComfyUI-MiniMax-H3-MLX.git'
NODE_DIR = 'ComfyUI-MiniMax-H3-MLX'
NAME = 'minimax-h3-t2v'
QWEN = 'qwen3.8:27b-mlx'
PUBLIC = ('prompt', 'width', 'height', 'duration_seconds', 'steps', 'seed')
NODES = ('MiniMaxH3ModelLoader', 'MiniMaxH3Generate',
         'MiniMaxH3ResultToComfyUI', 'MiniMaxH3SaveVideo')
MODELS = [
    dict(key='base', repo='MiniMaxAI/MiniMax-H3',
         revision='42ed227ee7df40d41602854ae760620d6eb651fe', local_dir='MiniMax-H3',
         include=['FL2VA/model_index.json', 'FL2VA/tokenizer/**', 'FL2VA/processor/**',
                  'FL2VA/text_encoder/**', 'FL2VA/video_vae/**', 'FL2VA/audio_vae/**']),
    dict(key='int8', repo='water1234/MiniMax-H3-MLX-Argus-Calibrated-INT8',
         revision='70505b09c80e298e684d798d8e0f946937dcfad4',
         local_dir='MiniMax-H3-MLX-Argus-Calibrated-INT8', include=['**']),
    dict(key='turbo', repo='water1234/MiniMax-H3-Turbo-v4-step600-EMA-MLX',
         revision='9771f9c606a50671bb94ee57191461602f02d1fc',
         local_dir='MiniMax-H3-Turbo-v4-step600-EMA-MLX', include=['**']),
]
REPAIR = '本人が対象データを退避してから再実行（自動修復なし）'
REREGISTER = 'Harness の ComfyUI パネルで既存項目を削除してから登録し直す'


class H3Error(Exception):
    def __init__(self, code, item, cause, remedy):
        self.code, self.item, self.cause, self.remedy = code, item, cause, remedy
        super().__init__(cause)


def fail(code, item, cause, remedy='入力・配置を確認'):
    raise H3Error(code, item, cause, remedy)


def display(value):
    return str(value).replace(str(Path.home()), '~')


def cli(main):
    try:
        return main() or 0
    except H3Error as exc:
        print(display(f'{exc.item}: {exc.cause}; 対処: {exc.remedy}'), file=sys.stderr)
        return exc.code
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        print('処理: 入力またはファイルの読取/書込に失敗; 対処: 配置・権限・形式を確認', file=sys.stderr)
        return 1


def positive(value):
    try:
        number = float(value)
        if not math.isfinite(number) or number <= 0:
            raise ValueError
        return number
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError('正の有限数を指定') from None


def nonnegative(value):
    try:
        number = int(value)
        if number < 0:
            raise ValueError
        return number
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError('非負整数を指定') from None


def add_paths(parser, names):
    defaults = dict(instance='~/ComfyUI-Installs/ComfyUI',
                    comfy_root='<instance>/ComfyUI', venv='<comfy-root>/.venv',
                    models_dir='~/ComfyUI-Shared/models/minimax_h3',
                    output_dir='~/ComfyUI-Shared/output', manifest=str(MANIFEST),
                    data_dir='~/.dsh/data/dsh-comfyui')
    for name in names:
        parser.add_argument('--' + name.replace('_', '-'), help='既定: ' + display(defaults[name]))


def parse(parser):
    """Parse after making --help the reference for every default value."""
    for action in parser._actions:
        default = action.default
        # Identity checks: a default of 0 (e.g. --seed) is a real default and must be shown.
        if default is None or default is False or default is argparse.SUPPRESS or '既定' in (action.help or ''):
            continue
        if isinstance(default, (list, tuple)):
            default = ' '.join(str(v) for v in default)
        shown = display(default).replace('%', '%%')
        action.help = (action.help + ' ' if action.help else '') + f'（既定: {shown}）'
    return parser.parse_args()


def paths(args):
    def chosen(name, default):
        return Path(getattr(args, name, None) or default).expanduser().absolute()
    instance = chosen('instance', Path.home() / 'ComfyUI-Installs/ComfyUI')
    comfy = chosen('comfy_root', instance / 'ComfyUI')
    return dict(instance=instance, comfy_root=comfy, venv=chosen('venv', comfy / '.venv'),
                models_dir=chosen('models_dir', Path.home() / 'ComfyUI-Shared/models/minimax_h3'),
                output_dir=chosen('output_dir', Path.home() / 'ComfyUI-Shared/output'),
                manifest=chosen('manifest', MANIFEST),
                data_dir=chosen('data_dir', Path.home() / '.dsh/data/dsh-comfyui'))


def existing_ancestor(path):
    """Keep missing components while resolving existing symlink aliases."""
    cursor = Path(path).resolve()
    tail = []
    while True:
        try:
            info = cursor.stat()
            return cursor, info, tuple(reversed(tail))
        except FileNotFoundError:
            if cursor == cursor.parent:
                raise
            tail.append(cursor.name)
            cursor = cursor.parent


def entity_relative(path, root):
    """Containment by device/inode, including mount and case aliases.

    Walk the candidate's ancestors, never the protected root's ancestors.
    Missing root components use casefold as a conservative write boundary.
    """
    _, rootstat, missing = existing_ancestor(root)
    cursor, info, tail = existing_ancestor(path)
    parts = list(tail)
    while True:
        if os.path.samestat(info, rootstat):
            if tuple(p.casefold() for p in parts[:len(missing)]) == tuple(p.casefold() for p in missing):
                return tuple(parts[len(missing):])
            return None
        if cursor == cursor.parent:
            return None
        parts.insert(0, cursor.name)
        cursor = cursor.parent
        info = cursor.stat()


def inside(path, root):
    return entity_relative(path, root) is not None


def writable(path, library=False):
    """Protect Harness configuration, including aliases resolving into it."""
    home = Path.home() / '.dsh'
    allowed = home / 'data/dsh-comfyui'
    if library and any(p.is_symlink() for p in (allowed.parent, allowed)):
        fail(2, '書込先', '~/.dsh のライブラリ用ディレクトリのリンクは禁止', 'リンクを本人が確認')
    if inside(path, home):
        if not library or not any(entity_relative(path, p) == () for p in (allowed, allowed / 'workflows.json')):
            fail(2, '書込先', '~/.dsh の許可範囲外', '設定は本人が手で追記')


def relpath(value):
    if not isinstance(value, str) or not value or '\\' in value or '\x00' in value:
        fail(2, 'パス', '相対POSIXパスが不正')
    if value.startswith('/') or any(p in ('', '.', '..') for p in value.split('/')):
        fail(2, 'パス', '絶対パスまたは逸脱要素')
    return value


def safe_model_path(root, relative):
    relpath(relative)
    root = root.resolve()
    candidate = root / relative
    if not inside(candidate, root):
        fail(2, 'モデル', 'ルート外への逸脱')
    cursor = root
    for part in relative.split('/'):
        cursor = cursor / part
        if cursor.is_symlink():
            fail(5, 'モデル', 'モデル配下のリンク', REPAIR)
    return candidate


def json_loads(data):
    def bad_constant(_):
        raise ValueError
    try:
        result = json.loads(data, parse_constant=bad_constant)
        def finite(value):
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError
            if isinstance(value, dict):
                for child in value.values():
                    finite(child)
            elif isinstance(value, list):
                for child in value:
                    finite(child)
        finite(result)
        return result
    except (ValueError, TypeError, UnicodeError, RecursionError):
        fail(2, 'JSON', 'JSON の形式不正', '原本を保持して形式を確認')


def read_json(path):
    try:
        return json_loads(path.read_bytes())
    except OSError:
        fail(2, 'JSON', 'ファイルの読取不能', '配置・権限を確認')


def validate_manifest(data):
    if not isinstance(data, dict) or type(data.get('schema')) is not int or data['schema'] != 1:
        fail(2, '一覧', 'schema 不正')
    entries = data.get('models')
    if not isinstance(entries, list) or len(entries) != 3:
        fail(2, '一覧', '3モデルが必要')
    seen = set()
    for model in entries:
        if not isinstance(model, dict) or not isinstance(model.get('key'), str) or model['key'] not in {m['key'] for m in MODELS}:
            fail(2, '一覧', 'モデル項目不正')
        if model['key'] in seen:
            fail(2, '一覧', 'モデル重複')
        seen.add(model['key'])
        expected = next(m for m in MODELS if m['key'] == model['key'])
        for field in ('repo', 'revision', 'local_dir', 'include'):
            if model.get(field) != expected[field]:
                fail(2, '一覧', '固定 ' + field + ' 不一致')
        relpath(model['local_dir'])
        files = model.get('files')
        if not isinstance(files, list) or not files:
            fail(2, '一覧', 'files 不正')
        found = set()
        for item in files:
            if not isinstance(item, dict):
                fail(2, '一覧', 'ファイル項目不正')
            name = relpath(item.get('path'))
            if name in found or type(item.get('size')) is not int or item['size'] < 0:
                fail(2, '一覧', '重複パスまたはサイズ不正')
            found.add(name)
        total = model.get('total_bytes')
        if type(total) is not int or total != sum(f['size'] for f in files):
            fail(2, '一覧', '合計サイズ不一致')
    return entries


def inspect_models(root, models):
    """Missing files can be acquired; partial/conflicting data cannot."""
    result = []
    for model in models:
        base = safe_model_path(root, model['local_dir'])
        if base.exists() and not base.is_dir():
            fail(5, 'モデル', 'モデルディレクトリ不正', REPAIR)
        # Also check extra/cache entries; incomplete takes precedence over extras.
        if base.exists():
            for directory, dirs, files in os.walk(base, followlinks=False, onerror=lambda _: fail(5, 'モデル', '走査不能', REPAIR)):
                for name in dirs + files:
                    entry = Path(directory) / name
                    if entry.is_symlink():
                        fail(5, 'モデル', 'モデル配下のリンク', REPAIR)
                    if name.endswith('.incomplete') and inside(entry, base / '.cache/huggingface/download'):
                        result.append((model, {'path': str(entry.relative_to(base)), 'size': 0}, '途中'))
        for item in model['files']:
            target = safe_model_path(root, model['local_dir'] + '/' + item['path'])
            try:
                info = target.stat()
            except FileNotFoundError:
                state = '未取得'
            except OSError:
                fail(5, 'モデル', '必須ファイルの読取不能', REPAIR)
            else:
                if not stat.S_ISREG(info.st_mode):
                    state = '不正'
                else:
                    size = info.st_size
                    state = '完了' if size == item['size'] else ('途中' if size < item['size'] else '不一致')
            result.append((model, item, state))
    return result


def model_summary(rows, verbose=False):
    for key in dict.fromkeys(m['key'] for m, _, _ in rows):
        group = [s for m, _, s in rows if m['key'] == key]
        model = next(m for m, _, _ in rows if m['key'] == key)
        print(f'{key}: 完了 {group.count("完了")} / 全 {len(model["files"])} 件')
    for model, item, state in rows:
        if verbose or state != '完了':
            print(display(f"{model['key']} {model['revision']} {item['path']} {item['size']} bytes: {state}"))


def executable(value, search=False, item='実行ファイル'):
    if not value or not isinstance(value, (str, Path)):
        fail(1, item, '指定なし', '導入・パスを確認')
    raw = str(value)
    if search and not Path(raw).is_absolute():
        raw = shutil.which(raw) or ''
    path = Path(raw).expanduser()
    if not raw or not path.is_absolute() or not path.is_file() or not os.access(path, os.X_OK):
        fail(1, item, '絶対パスの通常実行ファイルが必要', '導入・パス・実行権限を確認')
    # Retain the invoked venv/bin/python alias: resolving it before invocation loses venv discovery.
    return path.absolute()


def child_env(kind=None):
    env = {k: v for k, v in os.environ.items()
           if k in ('HOME', 'PATH', 'LANG', 'TMPDIR') or k.startswith('LC_')}
    if kind == 'pip':
        env['PIP_CONFIG_FILE'] = os.devnull
    if kind == 'git':
        env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1', GIT_TERMINAL_PROMPT='0')
    if kind == 'hub':
        env.update(HF_ENDPOINT='https://huggingface.co', HF_HUB_DISABLE_IMPLICIT_TOKEN='1')
    return env


def command(argv, timeout=1800, kind=None, cwd=None, code=6):
    executable(argv[0])
    try:
        result = subprocess.run([str(v) for v in argv], shell=False, env=child_env(kind),
                                cwd=cwd, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        fail(7, kind or '外部処理', '期限超過',
             'pip は変更が途中の可能性あり。本人が pip check を確認' if kind == 'pip' else '期限・状態を確認')
    except OSError:
        fail(code, kind or '外部処理', '起動不能', '実行物・権限を確認')
    if result.returncode:
        fail(code, kind or '外部処理', '非ゼロ終了', '状態を確認。pip は本人が pip check を確認' if kind == 'pip' else '対象の状態・配置を確認')
    return result


def local_url(value, ollama=False):
    try:
        url = urllib.parse.urlsplit(value)
        address = ipaddress.ip_address(url.hostname or '')
        port = url.port if url.port is not None else (443 if url.scheme == 'https' else 80)
        allowed_paths = ('', '/', '/v1') if ollama else ('', '/')
        if (url.scheme not in ('http', 'https') or not address.is_loopback or
                url.username is not None or url.password is not None or
                url.query or url.fragment or url.path not in allowed_paths or not 1 <= port <= 65535):
            raise ValueError
    except (ValueError, TypeError):
        fail(2, 'URL', 'ループバック IP リテラルの URL が必要', 'userinfo/query/fragment を除き接続先を確認')
    return urllib.parse.urlunsplit((url.scheme, url.netloc, '', '', '')).rstrip('/')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request_json(url, payload=None, timeout=30):
    data = None if payload is None else json.dumps(payload, allow_nan=False).encode('utf-8')
    request = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'} if data else {})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    outcome = {}

    def exchange():
        # read() keeps the HTTP layer's own integrity checks (a body shorter than
        # Content-Length raises IncompleteRead); read1() would return the fragment.
        try:
            with opener.open(request, timeout=timeout) as response:
                outcome['body'] = response.read()
        except BaseException as exc:  # handed to the calling thread below
            outcome['error'] = exc

    # The socket timeout only bounds each recv, including those inside chunk parsing.
    # Waiting on a worker bounds the whole exchange; an abandoned daemon worker ends
    # with its socket timeout or with the process.
    worker = threading.Thread(target=exchange, daemon=True)
    worker.start()
    worker.join(timeout)
    if worker.is_alive():
        fail(6, 'HTTP', '無応答・拒否・不正 JSON', 'API 起動・指定 URL・要求を確認（応答本文は非表示）')
    # Read the outcome only after the worker is known to have finished: reading it first
    # could miss an error stored between that read and the liveness check.
    error = outcome.get('error')
    if isinstance(error, (urllib.error.URLError, http.client.HTTPException, OSError)):
        fail(6, 'HTTP', '無応答・拒否・不正 JSON', 'API 起動・指定 URL・要求を確認（応答本文は非表示）')
    if error is not None:
        raise error
    try:
        return json_loads(outcome['body'])
    except H3Error:
        fail(6, 'HTTP', '無応答・拒否・不正 JSON', 'API 起動・指定 URL・要求を確認（応答本文は非表示）')


def validate_public(values):
    if not isinstance(values, dict) or set(values) != set(PUBLIC):
        fail(2, '生成条件', '公開6項目が必要')
    if not isinstance(values['prompt'], str) or not values['prompt'].strip():
        fail(2, 'prompt', '非空文字列が必要')
    for key in ('width', 'height'):
        v = values[key]
        if type(v) is not int or v <= 0 or v % 32:
            fail(2, key, '正の32倍数が必要')
    v = values['duration_seconds']
    try:
        valid = type(v) in (int, float) and math.isfinite(v) and v > 0
    except OverflowError:
        valid = False
    if not valid:
        fail(2, 'duration_seconds', '正の有限数が必要')
    for key, minimum in (('steps', 2), ('seed', 0)):
        if type(values[key]) is not int or values[key] < minimum:
            fail(2, key, f'{minimum}以上の整数が必要')
    return values


def validate_graph(graph):
    if not isinstance(graph, dict) or set(graph) != {'1', '2', '3'}:
        fail(2, 'グラフ', '固定3ノードが必要')
    for key, cls in (('1', NODES[0]), ('2', NODES[1]), ('3', NODES[3])):
        node = graph[key]
        if not isinstance(node, dict) or node.get('class_type') != cls or not isinstance(node.get('inputs'), dict):
            fail(2, 'グラフ', 'ノード構造不正')
    if graph['2']['inputs'].get('pipeline') != ['1', 0] or graph['3']['inputs'].get('result') != ['2', 0]:
        fail(2, 'グラフ', '接続不正')
    validate_public({k: graph['2']['inputs'].get(k) for k in PUBLIC})
    ffmpeg = graph['3']['inputs'].get('ffmpeg_path')
    if not isinstance(ffmpeg, str) or not Path(ffmpeg).is_absolute():
        fail(2, 'グラフ', 'ffmpeg_path は絶対パスが必要')
    relpath(graph['3']['inputs'].get('filename_prefix'))
    return graph


def load_graph():
    return validate_graph(read_json(WORKFLOW))


def graph_contract(graph):
    """Metadata is display-only. All node inputs except the public six are contractual."""
    validate_graph(graph)
    contract = {k: dict(class_type=v['class_type'], inputs=copy.deepcopy(v['inputs'])) for k, v in graph.items()}
    for key in PUBLIC:
        del contract['2']['inputs'][key]
    return contract


def compare_graph(actual, expected):
    try:
        same = graph_contract(actual) == graph_contract(expected)
    except H3Error:
        same = False
    if not same:
        fail(8, '履歴照合', 'ノード構成・固定入力が不一致', '登録項目・リポジトリ・履歴を確認。外部コマンドは起動しない')


def parameters(graph):
    defaults = dict(graph['2']['inputs'], width=768, height=448, duration_seconds=5.0, steps=9, seed=0)
    result = []
    labels = ('Prompt', 'Width', 'Height', 'Duration (s)', 'Steps', 'Seed')
    for name, label in zip(PUBLIC, labels):
        p = dict(id=str(uuid.uuid4()), name=name, label=label,
                 type='string' if name == 'prompt' else 'number', nodeId='2',
                 inputKey=name, default=defaults[name])
        if name != 'prompt':
            p['numberKind'] = 'float' if name == 'duration_seconds' else 'int'
            p['min'] = {'width': 32, 'height': 32, 'duration_seconds': 0.1, 'steps': 2, 'seed': 0}[name]
            if name == 'seed':
                p['random'] = True
            else:
                p['step'] = 32 if name in ('width', 'height') else (0.1 if name == 'duration_seconds' else 1)
        result.append(p)
    return result


def parameter_contract(value):
    if not isinstance(value, list) or len(value) != 6 or any(not isinstance(p, dict) for p in value):
        fail(2, 'parameters', '公開6項目が必要')
    if any(not isinstance(p.get('name'), str) or not isinstance(p.get('inputKey'), str) for p in value):
        fail(2, 'parameters', '名前・入力キーの型不正')
    if {p.get('name') for p in value} != set(PUBLIC) or {p.get('inputKey') for p in value} != set(PUBLIC):
        fail(2, 'parameters', '公開6項目の集合不一致')
    if any(p.get('nodeId') != '2' or p.get('name') != p.get('inputKey') for p in value):
        fail(2, 'parameters', '対象ノード/入力不一致')
    return [{k: v for k, v in p.items() if k != 'id'} for p in value]


def read_library(path):
    if path.is_symlink():
        fail(2, 'ライブラリ', 'リンクは禁止', '通常の workflows.json を使用')
    if not path.exists():
        return [], None
    entries = read_json(path)
    if not isinstance(entries, list):
        fail(2, 'ライブラリ', 'リスト以外', '原本を保持して形式を確認')
    for entry in entries:
        if (not isinstance(entry, dict) or not isinstance(entry.get('id'), str) or
                not isinstance(entry.get('name'), str) or not isinstance(entry.get('workflow'), dict)):
            fail(2, 'ライブラリ', '不正項目', '原本を保持して形式を確認')
        if not entry['workflow'] or any(not isinstance(n, dict) or not isinstance(n.get('class_type'), str) or
                                      not isinstance(n.get('inputs'), dict) for n in entry['workflow'].values()):
            fail(2, 'ライブラリ', '不正ワークフロー', '原本を保持して形式を確認')
    matches = [e for e in entries if e['name'] == NAME]
    if len(matches) > 1:
        fail(2, 'ライブラリ', '対象名の重複', '原本を保持して重複を確認')
    return entries, matches[0] if matches else None


def atomic_json(path, data, snapshot=None, mode=0o600):
    """snapshot=(stat, bytes) for existing files, None for an absent file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.h3-', delete=False) as handle:
            temp = Path(handle.name)
            os.fchmod(handle.fileno(), mode)
            handle.write((json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8'))
            handle.flush()
            os.fsync(handle.fileno())
        if path.is_symlink():
            fail(5, '保存', '原本が変化', '同時更新を止めて再確認')
        if snapshot is None:
            if path.exists():
                fail(5, '保存', '原本が出現', '同時更新を止めて再確認')
        else:
            oldstat, oldbytes = snapshot
            if not path.exists() or file_identity(path.stat()) != file_identity(oldstat) or path.read_bytes() != oldbytes:
                fail(5, '保存', '原本が変化', '同時更新を止めて再確認')
        os.replace(temp, path)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def file_identity(info):
    # Reading the original may update atime; it is not a concurrent content change.
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def video_tools(graph):
    ffmpeg = executable(graph['3']['inputs']['ffmpeg_path'], item='ffmpeg')
    try:
        ffprobe = executable(ffmpeg.parent / 'ffprobe', item='ffprobe')
    except H3Error:
        fail(1, 'ffprobe', '導出先に無い・実行できない', 'ffmpeg と同じ場所に ffprobe があるか確認')
    return ffmpeg, ffprobe


def output_video(entry, root):
    try:
        descriptors = entry['outputs']['3']['minimax_h3_video']
        if not isinstance(descriptors, list) or len(descriptors) != 1:
            raise ValueError
        d = descriptors[0]
        if not isinstance(d, dict) or d.get('type') != 'output':
            raise ValueError
        name = relpath(d.get('filename'))
        if '/' in name or not name.endswith('.mp4'):
            raise ValueError
        sub = d.get('subfolder')
        if not isinstance(sub, str):
            raise ValueError
        if sub:
            relpath(sub)
        path = root / sub / name
        if not inside(path, root) or not path.is_file():
            raise ValueError
        return path.resolve()
    except (KeyError, TypeError, ValueError, H3Error):
        fail(8, '保存先', '出力構造不正・動画不在・ルート逸脱', '履歴と output-dir の通常動画を確認')


def inspect_video(path, width, height, graph, timeout=300):
    ffmpeg, ffprobe = video_tools(graph)
    result = command([ffprobe, '-v', 'error', '-show_streams', '-of', 'json', path], timeout=timeout, code=8)
    try:
        streams = json_loads(result.stdout)['streams']
        video = next(s for s in streams if s.get('codec_type') == 'video')
        audio = next(s for s in streams if s.get('codec_type') == 'audio')
        if video.get('codec_name') != 'h264' or audio.get('codec_name') != 'aac':
            raise ValueError
        if video.get('width') != width or video.get('height') != height:
            raise ValueError
    except (KeyError, TypeError, ValueError, StopIteration, AttributeError, H3Error):
        fail(8, '動画', 'H.264/AAC 両ストリームまたは解像度が不合格', '動画と要求解像度を確認')
    decoded = command([ffmpeg, '-nostdin', '-v', 'error', '-xerror', '-i', path, '-map', '0:v:0',
                       '-map', '0:a:0', '-f', 'null', '-'], timeout=timeout, code=8)
    if decoded.stderr.strip():
        fail(8, '動画', '全フレームデコードにエラー', '動画を確認')
    print(f'動画 PASS: H.264 {width}×{height} / AAC / 全フレームデコード 0')
    return streams
