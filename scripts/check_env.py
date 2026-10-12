"""Read-only D-1..D-9 diagnostics for the actual instance and desktop profile."""
import argparse
import importlib.util
import ipaddress
from pathlib import Path
import re
import sys
import urllib.parse

_spec = importlib.util.spec_from_file_location('h3_common', Path(__file__).with_name('h3_common.py'))
c = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(c)


def status(ok, cause, remedy):
    return ('PASS' if ok else 'FAIL', cause, remedy)


def guarded(fn, unknown=False):
    try:
        return fn()
    except c.H3Error as exc:
        return ('UNKNOWN' if unknown else 'FAIL', exc.cause, exc.remedy)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, RecursionError):
        return ('UNKNOWN' if unknown else 'FAIL', '読取不能または構造不正', '指定先・形式・権限を確認')


def model_diagnostic(p):
    models = c.validate_manifest(c.read_json(p['manifest']))
    rows = c.inspect_models(p['models_dir'], models)
    c.model_summary(rows)
    entrance = p['comfy_root'] / 'models/minimax_h3'
    same = entrance.is_dir() and entrance.resolve() == p['models_dir'].resolve()
    good = all(s == '完了' for _, _, s in rows)
    return status(same and good,
                  ('全必須ファイル一致' if good else '欠落・途中・サイズ不一致') + (' / 入口一致' if same else ' / 入口不在・別実体'),
                  '不足取得・本人による退避・モデル入口を共有先と同じ実体へ修正')


def ffmpeg_diagnostic(data_dir):
    graph = c.load_graph()
    path = graph['3']['inputs']['ffmpeg_path']
    c.executable(path, item='ffmpeg')
    _, registered = c.read_library(data_dir / 'workflows.json')
    if registered is not None:
        try:
            other = registered['workflow']['3']['inputs']['ffmpeg_path']
        except (KeyError, TypeError):
            c.fail(2, 'D-4', '登録項目の Save 固定入力不正', c.REREGISTER)
        c.executable(other, item='登録 ffmpeg')
        if other != path:
            c.fail(1, 'D-4', 'リポジトリと登録固定入力の相違', c.REREGISTER)
    try:
        c.executable(Path(path).parent / 'ffprobe', item='ffprobe')
        probe = 'ffprobe 有り（実行可）'
    except c.H3Error:
        probe = 'ffprobe 無し/実行不可（動画検査前に同じ場所へ導入）'
    return ('PASS', ('登録固定入力一致' if registered else '未登録、リポジトリのみ') + '; ' + probe,
            'ffmpeg 固定入力を確認。登録はチャット経路で別途確認')


class Opaque:
    """Unknown YAML tags have no executable or interpreted value."""


class Ambiguous(dict):
    pass


def read_patch(path):
    try:
        import yaml
    except ImportError:
        c.fail(1, 'PyYAML', '未導入', 'ComfyUI 仮想環境の Python -I を使用（追加導入しない）')

    class Loader(yaml.SafeLoader):
        pass

    def mapping(loader, node, deep=False):
        # YAML merge keys and explicit overrides are ordinary YAML, not duplicate declarations.
        direct = [loader.construct_object(key, deep=deep) for key, _ in node.value
                  if key.tag != 'tag:yaml.org,2002:merge']
        duplicated = len(set(direct)) != len(direct)
        loader.flatten_mapping(node)
        result = {}
        for keynode, valnode in node.value:
            key = loader.construct_object(keynode, deep=deep)
            value = loader.construct_object(valnode, deep=deep)
            result[key] = value
        return Ambiguous(result) if duplicated else result

    Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
    Loader.add_constructor(None, lambda loader, node: Opaque())
    try:
        with path.open(encoding='utf-8') as handle:
            return yaml.load(handle, Loader=Loader)
    except (yaml.YAMLError, OSError, UnicodeError, TypeError):
        c.fail(1, 'profile', '安全な YAML 読取不能', '指定 profile の形式を確認')


def unique_map(value):
    if type(value) is not dict:
        c.fail(1, 'profile', '設定構造不正・重複・不透明な値', '既存設定を保持して手動追記')
    return value


def env_key_resolved(path, key):
    hits = []
    # Match keys FIRST. Never split/retain values of unrelated keys.
    matcher = re.compile(r'^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=')
    with path.open(encoding='utf-8') as handle:
        for line in handle:
            match = matcher.match(line)
            if match is None or match.group(1) != key:
                continue
            value = line[match.end():].strip()
            if value.startswith(('"', "'")):
                quote = value[0]
                end = value.find(quote, 1)
                valid_tail = end >= 1 and (not value[end + 1:].strip() or value[end + 1:].lstrip().startswith('#'))
                value = value[1:end] if valid_tail else ''
            else:
                # A comment starts at '#' at the beginning of the value or after whitespace,
                # so `KEY= # note` is an empty value, not a resolved key.
                value = re.split(r'(?:^|\s+)#', value, maxsplit=1)[0].strip()
            hits.append(bool(value) and not any(ch in value for ch in ('$','`','\\')) and '\n' not in value)
    return len(hits) == 1 and hits[0]


def profile_diagnostic(profile, env_file, ollama_url):
    patch = read_patch(profile / 'cordis.patch.yml')
    if not isinstance(patch, list):
        c.fail(1, 'profile', 'トップレベルはリストが必要')
    targets = {}
    for entry in patch:
        if not isinstance(entry, dict):
            c.fail(1, 'profile', '項目の構造不明')
        if entry.get('id') in ('llm-pi-ai', 'agent-default-model'):
            unique_map(entry)
            if entry['id'] in targets:
                c.fail(1, 'profile', '対象設定の重複')
            targets[entry['id']] = unique_map(entry.get('config'))
    if set(targets) != {'llm-pi-ai', 'agent-default-model'}:
        c.fail(1, 'profile', '対象設定の欠落', '既存項目を保持して例を手動追記')
    providers = unique_map(targets['llm-pi-ai'].get('providers'))
    provider = unique_map(providers.get('ollama'))
    default = targets['agent-default-model']
    if default.get('provider') != 'ollama' or default.get('model') != c.QWEN:
        c.fail(1, 'profile', '既定モデル不一致')
    if provider.get('api') != 'openai-completions' or provider.get('apiKeyEnv') != 'OLLAMA_API_KEY':
        c.fail(1, 'profile', 'API・対象キー参照不一致')
    base = provider.get('baseURL')
    if not isinstance(base, str) or c.local_url(base, ollama=True) != c.local_url(ollama_url, ollama=True) or urllib.parse.urlsplit(base).path != '/v1':
        c.fail(1, 'profile', 'Ollama baseURL 不一致')
    models = provider.get('models')
    if not isinstance(models, list):
        c.fail(1, 'profile', 'モデル定義不明')
    matches = [m for m in models if isinstance(m, dict) and m.get('id') == c.QWEN]
    if len(matches) != 1:
        c.fail(1, 'profile', '対象モデル欠落・重複')
    unique_map(matches[0])
    if not env_key_resolved(env_file, 'OLLAMA_API_KEY'):
        c.fail(1, 'キー', '対象キー未解決・空・重複・展開が必要', '~/.dsh/.env に非秘密ダミー値を手動追記（値は非表示）')
    return ('PASS', 'desktop provider・既定モデル・対象キー存在（全値非表示）', '設定例を保持して運用')


def plugin_diagnostic(profile):
    package = c.read_json(profile / 'node_modules/dsh-comfyui/package.json')
    ok = isinstance(package, dict) and package.get('name') == 'dsh-comfyui' and package.get('version') == '0.5.4'
    return status(ok, 'dsh-comfyui 0.5.4 導入済み' if ok else '未導入・別版',
                  '指定 profile へ手動導入。互換性例外は本人承諾後のみ')


def process_table(ps):
    text = c.command([ps, '-axo', 'pid=,ppid=,pgid=,comm='], timeout=30).stdout
    result = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.strip().split(None, 3)
        if len(parts) != 4 or not all(p.isdigit() for p in parts[:3]):
            c.fail(1, 'ps', '解析不能', '権限・ps 出力を確認')
        pid, parent, group = map(int, parts[:3])
        result[pid] = (parent, group, parts[3])
    if not result:
        c.fail(1, 'ps', 'プロセス確認不能')
    return result


def parse_lsof(text):
    """lsof -FpnT machine records for TCP LISTEN only."""
    pid, addresses = None, {}
    for line in text.splitlines():
        if not line:
            continue
        if line[0] == 'p':
            if not line[1:].isdigit():
                c.fail(1, 'lsof', 'PID 解析不能')
            pid = int(line[1:])
            addresses.setdefault(pid, [])
        elif line[0] == 'n':
            if pid is None:
                c.fail(1, 'lsof', '持ち主解析不能')
            raw = line[1:]
            try:
                host, port = raw.rsplit(':', 1)
                host = host.strip('[]')
                if not port.isdigit() or not 1 <= int(port) <= 65535:
                    raise ValueError
                if host != '*':
                    ipaddress.ip_address(host)
            except ValueError:
                c.fail(1, 'lsof', '待受アドレス解析不能')
            addresses[pid].append((host, int(port)))
        elif line[0] == 'T':
            if line.startswith('TST=') and line != 'TST=LISTEN':
                c.fail(1, 'lsof', 'LISTEN 以外の状態')
        elif line[0] not in 'fcPt':
            c.fail(1, 'lsof', '機械形式解析不能')
    return addresses


def listeners(lsof, pids=None, port=None):
    argv = [lsof, '-nP', '-a']
    if pids is not None:
        argv += ['-p', ','.join(str(p) for p in sorted(pids))]
    argv += ['-iTCP' + (':' + str(port) if port else ''), '-sTCP:LISTEN', '-FpnT']
    # lsof exits 1 with empty stdout when there are no matches. Other failures remain UNKNOWN.
    c.executable(lsof)
    try:
        result = c.subprocess.run([str(a) for a in argv], shell=False, env=c.child_env(),
                                  capture_output=True, text=True, timeout=30)
    except (OSError, c.subprocess.TimeoutExpired):
        c.fail(1, 'lsof', '待受確認不能', 'プロセス・権限を確認')
    if result.returncode not in (0, 1) or result.stderr.strip() or (result.returncode == 1 and result.stdout):
        c.fail(1, 'lsof', '待受確認不能', '権限・プロセスを確認')
    return parse_lsof(result.stdout)


def descendants(table, roots, same_group=False):
    if any(p not in table for p in roots):
        c.fail(1, '待受', '持ち主のプロセス関係不明', '起動・権限を確認')
    selected = set(roots)
    groups = {table[p][1] for p in roots}
    while True:
        added = {pid for pid, (parent, group, _) in table.items()
                 if parent in selected and (not same_group or group in groups)}
        if added <= selected:
            return selected
        selected |= added


def address_diagnostic(records):
    all_addresses = [address for values in records.values() for address, _ in values]
    if not all_addresses:
        return ('UNKNOWN', '待受無し・確認不能', '対象を起動して再診断')
    ok = all(host != '*' and ipaddress.ip_address(host).is_loopback for host in all_addresses)
    return status(ok, '全 TCP LISTEN がループバック' if ok else '外部または混在 TCP LISTEN',
                  '外部公開せずループバックだけで起動。UDP は対象外')


def port_diagnostic(urls, table, lsof):
    records = {}
    for url in urls:
        u = urllib.parse.urlsplit(url)
        port = u.port or (443 if u.scheme == 'https' else 80)
        owners = {pid for pid, addr in listeners(lsof, port=port).items() if addr}
        if not owners:
            return ('UNKNOWN', '指定ポートの持ち主不在', 'API 起動・URL・権限を確認')
        pids = descendants(table, owners, same_group=True)
        found = listeners(lsof, pids=pids)
        # Each service must be confirmed on its own: a service that vanished between the
        # two lookups must not be hidden by the other service's healthy listeners.
        if not any(found.get(pid) for pid in owners):
            return ('UNKNOWN', '指定ポートの持ち主の待受を確認できない', 'API 起動・URL・権限を確認して再診断')
        records.update(found)
    return address_diagnostic(records)


def harness_diagnostic(name, table, lsof):
    roots = {pid for pid, (_, _, comm) in table.items() if Path(comm).name == name}
    if not roots:
        return ('UNKNOWN', 'Harness 未起動・完全名不一致', 'Harness を起動・名前を確認')
    return address_diagnostic(listeners(lsof, pids=descendants(table, roots)))


def aggregate(results):
    for i, (state, cause, remedy) in enumerate(results, 1):
        print(c.display(f'D-{i} {state}: {cause}; 対処: {remedy}'))
    return 0 if all(state == 'PASS' for state, _, _ in results) else 1


def diagnose(args):
    comfy = c.local_url(args.comfy_url)
    ollama = c.local_url(args.ollama_url, ollama=True)
    p = c.paths(args)
    profile, env_file = Path(args.profile_dir).expanduser(), Path(args.env_file).expanduser()
    def system():
        result = c.request_json(comfy + '/system_stats', timeout=args.http_timeout)
        return status(isinstance(result, dict) and isinstance(result.get('system'), dict) and isinstance(result.get('devices'), list),
                      'ComfyUI API 応答/構造確認', 'API 起動・URLを確認')
    def nodes():
        missing = []
        for name in c.NODES:
            try:
                result = c.request_json(comfy + '/object_info/' + name, timeout=args.http_timeout)
                if not isinstance(result, dict) or not isinstance(result.get(name), dict) or not result[name]:
                    missing.append(name)
            except c.H3Error:
                missing.append(name)
        return status(not missing, '4ノード登録' if not missing else '欠落: ' + ', '.join(missing), '固定ノード導入・ComfyUI 再起動')
    def tags():
        result = c.request_json(ollama + '/api/tags', timeout=args.http_timeout)
        if not isinstance(result, dict) or not isinstance(result.get('models'), list):
            c.fail(1, 'Ollama', 'タグ応答不正')
        ok = any(isinstance(m, dict) and c.QWEN in (m.get('name'), m.get('model')) for m in result['models'])
        return status(ok, 'Ollama API / Qwen 有り' if ok else 'Qwen 不在', 'Ollama 起動・手動 pull')
    results = [guarded(system), guarded(nodes), guarded(lambda: model_diagnostic(p)),
               guarded(lambda: ffmpeg_diagnostic(p['data_dir'])), guarded(tags),
               guarded(lambda: profile_diagnostic(profile, env_file, args.ollama_url), unknown=True),
               guarded(lambda: plugin_diagnostic(profile))]
    try:
        ps = c.executable(args.ps, search=True, item='ps')
        lsof = c.executable(args.lsof, search=True, item='lsof')
        table = process_table(ps)
        results.append(guarded(lambda: port_diagnostic((comfy, ollama), table, lsof), unknown=True))
        results.append(guarded(lambda: harness_diagnostic(args.harness_process, table, lsof), unknown=True))
    except c.H3Error:
        results.extend([('UNKNOWN', 'ps/lsof または関係の確認不能', '導入・権限・起動を確認')] * 2)
    return aggregate(results)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    c.add_paths(parser, ('instance', 'comfy_root', 'models_dir', 'manifest', 'data_dir'))
    parser.add_argument('--comfy-url', default='http://127.0.0.1:8188')
    parser.add_argument('--ollama-url', default='http://127.0.0.1:11434/v1')
    parser.add_argument('--profile-dir', default='~/.dsh/profiles/desktop')
    parser.add_argument('--env-file', default='~/.dsh/.env')
    parser.add_argument('--harness-process', default='DeepSeek Harness')
    parser.add_argument('--lsof', default='lsof', help='PATH から絶対パス解決')
    parser.add_argument('--ps', default='ps', help='PATH から絶対パス解決')
    parser.add_argument('--http-timeout', type=c.positive, default=5)
    return diagnose(c.parse(parser))


if __name__ == '__main__':
    sys.exit(c.cli(main))
