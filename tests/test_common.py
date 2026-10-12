import argparse
import copy
import json
import os
from pathlib import Path
import sys
from unittest import mock
from support import Case, ROOT, load, fixture_manifest, exec_file, write_json

c = load('h3_common')


class CommonTests(Case):
    def test_manifest_real_totals(self):
        models = c.validate_manifest(c.read_json(c.MANIFEST))
        self.assertEqual([len(m['files']) for m in models], [66, 13, 57])
        self.assertEqual([m['total_bytes'] for m in models], [77770657762, 37797145373, 1559967577])

    def test_manifest_sha_repo_scope(self):
        for field in ('revision', 'repo', 'local_dir', 'include'):
            with self.subTest(field=field):
                value = fixture_manifest(c)
                value['models'][0][field] = 'wrong'
                self.raises_code(c, 2, c.validate_manifest, value)

    def test_manifest_bad_sizes_duplicates(self):
        for size in (True, -1, 1.5, '4'):
            value = fixture_manifest(c)
            value['models'][0]['files'][0]['size'] = size
            self.raises_code(c, 2, c.validate_manifest, value)
        value = fixture_manifest(c)
        value['models'][0]['files'] *= 2
        self.raises_code(c, 2, c.validate_manifest, value)
        value = fixture_manifest(c)
        value['models'][0]['total_bytes'] += 1
        self.raises_code(c, 2, c.validate_manifest, value)

    def test_relative_paths(self):
        for path in ('/absolute', '../a', 'a/../b', 'a//b', './x', 'a\\b', '', 'a\x00b'):
            self.raises_code(c, 2, c.relpath, path)
        self.assertEqual(c.relpath('FL2VA/a.json'), 'FL2VA/a.json')

    def test_model_containment(self):
        self.assertFalse(c.inside(self.root.parent / (self.root.name + '-other/file'), self.root))
        self.assertTrue(c.inside(self.root / 'file', self.root))
        (self.root / 'jump').symlink_to(self.root.parent)
        self.raises_code(c, 2, c.safe_model_path, self.root, 'jump/file')

    def test_model_symlink_inside_rejected(self):
        (self.root / 'real').mkdir()
        (self.root / 'alias').symlink_to(self.root / 'real')
        self.raises_code(c, 5, c.safe_model_path, self.root, 'alias/file')

    def test_write_protection_aliases(self):
        home = self.root / 'home'
        (home / '.dsh/profiles').mkdir(parents=True)
        (self.root / 'alias').symlink_to(home / '.dsh')
        with mock.patch.object(c.Path, 'home', return_value=home):
            for path in (home / '.dsh/.env', home / '.dsh/profiles/x', self.root / 'alias/profiles/x'):
                self.raises_code(c, 2, c.writable, path)
                self.raises_code(c, 2, c.writable, path, library=True)
            c.writable(home / '.dsh/data/dsh-comfyui/workflows.json', library=True)
            self.raises_code(c, 2, c.writable, home / '.dsh/data/dsh-comfyui/other', library=True)
            c.writable(self.root / 'outside')

    def test_resolution_defaults_and_overrides(self):
        home = self.root / 'home'
        with mock.patch.object(c.Path, 'home', return_value=home):
            p = c.paths(argparse.Namespace())
            self.assertEqual(p['venv'], home / 'ComfyUI-Installs/ComfyUI/ComfyUI/.venv')
            p = c.paths(argparse.Namespace(instance=str(self.root / 'instance')))
            self.assertEqual(p['venv'], self.root / 'instance/ComfyUI/.venv')
            p = c.paths(argparse.Namespace(comfy_root=str(self.root / 'core'), venv=str(self.root / 'env')))
            self.assertEqual(p['venv'], self.root / 'env')

    def test_executable_links(self):
        real = exec_file(self.root / 'real')
        for name in ('python', 'git', 'ffmpeg', 'ffprobe', 'lsof', 'ps'):
            alias = self.root / name
            alias.symlink_to(real)
            self.assertEqual(c.executable(alias), alias)
        real.chmod(0o600)
        self.raises_code(c, 1, c.executable, self.root / 'python')
        self.raises_code(c, 1, c.executable, self.root)
        self.raises_code(c, 1, c.executable, 'relative')

    def test_child_env_isolation(self):
        with mock.patch.dict(os.environ, {'HF_TOKEN': 'MARKER', 'HTTPS_PROXY': 'MARKER', 'PIP_INDEX_URL': 'MARKER', 'GIT_CONFIG_COUNT': '2', 'HF_ENDPOINT': 'MARKER'}, clear=True):
            self.assertNotIn('HF_TOKEN', c.child_env('hub'))
            self.assertEqual(c.child_env('hub')['HF_ENDPOINT'], 'https://huggingface.co')
            self.assertEqual(c.child_env('pip')['PIP_CONFIG_FILE'], os.devnull)
            self.assertEqual(c.child_env('git')['GIT_CONFIG_GLOBAL'], os.devnull)
            self.assertEqual(c.child_env('git')['GIT_CONFIG_NOSYSTEM'], '1')
            self.assertNotIn('MARKER', str(c.child_env('pip')))

    def test_local_url_loopback(self):
        for url in ('http://127.0.0.1:9000', 'https://127.3.4.5:8188/', 'http://[::1]:8188'):
            self.assertTrue(c.local_url(url))
        for url in ('http://localhost:8188', 'http://192.168.1.1:8188', 'http://0.0.0.0', 'file:///etc/a', 'http://127.0.0.1/a', 'http://x@127.0.0.1', 'http://127.0.0.1?x=1', 'http://127.0.0.1#x', 'http://[::]', 'http://127.0.0.1:0'):
            self.raises_code(c, 2, c.local_url, url)
        self.assertEqual(c.local_url('http://127.0.0.1:11434/v1', True), 'http://127.0.0.1:11434')

    def test_http_proxy_redirect_and_secret_errors(self):
        opener = mock.Mock()
        response = mock.MagicMock()
        response.__enter__.return_value.read1.side_effect = [b'{"ok":', b' true}', b'']
        opener.open.return_value = response
        with mock.patch.object(c.urllib.request, 'build_opener', return_value=opener) as build:
            self.assertEqual(c.request_json('http://127.0.0.1:1'), {'ok': True})
            self.assertEqual(build.call_args.args[0].proxies, {})
            self.assertIsNone(build.call_args.args[1].redirect_request(None, None, 302, '', {}, 'http://example.invalid'))
            opener.open.side_effect = c.urllib.error.URLError('SECRET_MARKER')
            self.assertEqual(c.cli(lambda: c.request_json('http://127.0.0.1:1')), 6)
        self.assertNotIn('SECRET_MARKER', self.error.getvalue())

    def test_http_protocol_errors_are_classified_not_raised(self):
        # Protocol-level failures are not OSError; they must still become code 6 without
        # leaking the peer's bytes, both when opening and while reading the body.
        errors = (c.http.client.IncompleteRead(b'SECRET_MARKER'), c.http.client.BadStatusLine('SECRET_MARKER'),
                  c.http.client.RemoteDisconnected('SECRET_MARKER'))
        for error in errors:
            for stage in ('open', 'read'):
                opener = mock.Mock()
                response = mock.MagicMock()
                if stage == 'open':
                    opener.open.side_effect = error
                else:
                    response.__enter__.return_value.read1.side_effect = error
                    opener.open.return_value = response
                with mock.patch.object(c.urllib.request, 'build_opener', return_value=opener):
                    self.raises_code(c, 6, c.request_json, 'http://127.0.0.1:1')
                    self.assertEqual(c.cli(lambda: c.request_json('http://127.0.0.1:1')), 6)
        self.assertNotIn('SECRET_MARKER', self.error.getvalue())

    def test_http_body_deadline_bounds_a_slow_drip(self):
        # Each read returns quickly, so the socket timeout never fires; only the deadline stops it.
        opener = mock.Mock()
        response = mock.MagicMock()
        reads = []
        def drip(_):
            reads.append(1)
            # Without the deadline this would never end; fail fast instead of hanging.
            if len(reads) > 50:
                raise AssertionError('body read was not bounded by the deadline')
            return b' '
        response.__enter__.return_value.read1.side_effect = drip
        opener.open.return_value = response
        clock = iter(range(0, 1000))
        with mock.patch.object(c.urllib.request, 'build_opener', return_value=opener), \
                mock.patch.object(c.time, 'monotonic', side_effect=lambda: next(clock)):
            self.raises_code(c, 6, c.request_json, 'http://127.0.0.1:1', timeout=5)
        self.assertLessEqual(len(reads), 5)

    def test_parse_shows_every_default_in_help(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--seed', type=int, default=0)
        parser.add_argument('--timeout', type=float, default=7200)
        parser.add_argument('--url', default='http://127.0.0.1:8188', help='接続先')
        parser.add_argument('--percent', default='50%')
        parser.add_argument('--flag', action='store_true')
        parser.add_argument('--named', default='x', help='既定: 明示済み')
        with mock.patch.object(sys, 'argv', ['tool']):
            c.parse(parser)
        text = parser.format_help()
        for expected in ('（既定: 0）', '（既定: 7200）', '接続先 （既定: http://127.0.0.1:8188）', '（既定: 50%）'):
            self.assertIn(expected, text)
        self.assertEqual(text.count('既定: 明示済み'), 1)
        self.assertNotIn('（既定: False）', text)

    def test_json_nonfinite(self):
        for value in ('NaN', 'Infinity', '-Infinity', '1e999', '{"x": [1e999]}', '{bad'):
            self.raises_code(c, 2, c.json_loads, value)

    def test_public_bounds_special_prompt(self):
        graph = c.load_graph()
        values = {k: graph['2']['inputs'][k] for k in c.PUBLIC}
        values['prompt'] = "O'Reilly < 2; `cmd` 日本語"
        self.assertEqual(c.validate_public(values)['prompt'], values['prompt'])
        for key, bad in (('width', 31), ('height', True), ('duration_seconds', float('nan')), ('steps', 1), ('seed', -1), ('prompt', ' ')):
            self.raises_code(c, 2, c.validate_public, {**values, key: bad})
        self.raises_code(c, 2, c.validate_public, {**values, 'duration_seconds': 10**500})

    def test_parameters_exact_six_no_max(self):
        params = c.parameters(c.load_graph())
        self.assertEqual({p['name'] for p in params}, set(c.PUBLIC))
        self.assertTrue(all('max' not in p for p in params))
        c.parameter_contract(params)
        params[0]['name'] = 'ffmpeg_path'
        params[0]['inputKey'] = 'ffmpeg_path'
        self.raises_code(c, 2, c.parameter_contract, params)

    def test_graph_fixed_and_public_diff(self):
        graph = c.load_graph()
        actual = copy.deepcopy(graph)
        actual['2']['inputs'].update(width=768, height=448, seed=12345)
        actual['1'].pop('_meta')
        c.compare_graph(actual, graph)
        for node, key in (('1', 'memory_limit_gb'), ('2', 'block_cache'), ('3', 'ffmpeg_path')):
            actual = copy.deepcopy(graph)
            actual[node]['inputs'][key] = 'changed'
            self.raises_code(c, 8, c.compare_graph, actual, graph)

    def test_cli_no_raw_exception(self):
        self.assertEqual(c.cli(lambda: (_ for _ in ()).throw(ValueError('SECRET_MARKER'))), 1)
        self.assertNotIn('SECRET_MARKER', self.error.getvalue())
