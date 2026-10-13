import argparse
import copy
import importlib.util
import sys
from unittest import mock
from support import Case, ROOT, load, fixture_manifest, write_json, exec_file

e = load('check_env')
c = e.c
HAS_YAML = importlib.util.find_spec('yaml') is not None


class CheckTests(Case):
    def graph(self):
        graph = c.load_graph()
        graph['3']['inputs']['ffmpeg_path'] = str(exec_file(self.root / 'bin/ffmpeg'))
        return graph

    def test_d4_repository_and_registration_both_checked(self):
        graph = self.graph()
        data = self.root / 'data'
        entry = dict(id='id', name=c.NAME, workflow=copy.deepcopy(graph))
        with mock.patch.object(c, 'load_graph', return_value=graph):
            self.assertEqual(e.ffmpeg_diagnostic(data)[0], 'PASS')
            self.assertIn('未登録', e.ffmpeg_diagnostic(data)[1])
            for value in ('relative', str(self.root / 'missing'), str(exec_file(self.root / 'bin/other'))):
                entry['workflow']['3']['inputs']['ffmpeg_path'] = value
                write_json(data / 'workflows.json', [entry])
                self.assertEqual(e.guarded(lambda: e.ffmpeg_diagnostic(data))[0], 'FAIL')
            entry['workflow']['3']['inputs']['ffmpeg_path'] = graph['3']['inputs']['ffmpeg_path']
            write_json(data / 'workflows.json', [entry])
            self.assertEqual(e.ffmpeg_diagnostic(data)[0], 'PASS')
            (self.root / 'bin/ffmpeg').chmod(0o600)
            self.assertEqual(e.guarded(lambda: e.ffmpeg_diagnostic(data))[0], 'FAIL')

    def test_d4_bad_library_fails_not_unregistered(self):
        graph = self.graph()
        data = self.root / 'data'
        entry = dict(id='id', name=c.NAME, workflow=graph)
        path = data / 'workflows.json'
        path.parent.mkdir()
        with mock.patch.object(c, 'load_graph', return_value=graph):
            for raw in ('{bad', '{}', c.json.dumps([entry, entry])):
                path.write_text(raw)
                result = e.guarded(lambda: e.ffmpeg_diagnostic(data))
                self.assertEqual(result[0], 'FAIL')
                self.assertNotIn('未登録', result[1])

    def test_d4_ffprobe_is_supplement_only(self):
        graph = self.graph()
        with mock.patch.object(c, 'load_graph', return_value=graph):
            result = e.ffmpeg_diagnostic(self.root / 'data')
            self.assertEqual(result[0], 'PASS')
            self.assertIn('ffprobe 無し', result[1])
            exec_file(self.root / 'bin/ffprobe')
            self.assertIn('ffprobe 有り', e.ffmpeg_diagnostic(self.root / 'data')[1])

    def test_d3_model_entry_real_target(self):
        data = self.complete(c)
        manifest = self.root / 'manifest.json'
        write_json(manifest, data)
        core = self.root / 'core'
        entrance = core / 'models/minimax_h3'
        entrance.parent.mkdir(parents=True)
        p = dict(comfy_root=core, models_dir=self.root, manifest=manifest)
        self.assertEqual(e.model_diagnostic(p)[0], 'FAIL')
        entrance.symlink_to(self.root)
        self.assertEqual(e.model_diagnostic(p)[0], 'PASS')
        entrance.unlink()
        entrance.mkdir()
        self.assertEqual(e.model_diagnostic(p)[0], 'FAIL')
        (self.root / data['models'][0]['local_dir'] / 'test.bin').write_bytes(b'x')
        self.assertIn('途中', e.model_diagnostic(p)[1])

    def test_env_key_only_nonempty_duplicate_export_expansion(self):
        path = self.root / '.env'
        for value, expected in (("export OLLAMA_API_KEY='local'\n", True), ('OLLAMA_API_KEY=""\n', False),
                                ('OLLAMA_API_KEY=\n', False), ('OLLAMA_API_KEY=$OTHER\n', False),
                                ('OLLAMA_API_KEY=x\nOLLAMA_API_KEY=y\n', False), ('OTHER=SECRET\n', False),
                                ('OLLAMA_API_KEY=x # comment\n', True),
                                # A value that is only a comment is empty, as the harness reads it.
                                ('OLLAMA_API_KEY= # comment\n', False), ('OLLAMA_API_KEY=#comment\n', False),
                                ('OLLAMA_API_KEY=a#b\n', True)):
            path.write_text('OTHER=SECRET_MARKER\n' + value)
            self.assertEqual(e.env_key_resolved(path, 'OLLAMA_API_KEY'), expected)
        self.assertNotIn('SECRET_MARKER', self.output.getvalue())

    def test_target_key_never_printed(self):
        path = self.root / '.env'
        path.write_text('UNRELATED=SECRET_OTHER\nOLLAMA_API_KEY=SECRET_TARGET\n')
        self.assertTrue(e.env_key_resolved(path, 'OLLAMA_API_KEY'))
        self.assertNotIn('SECRET', self.output.getvalue())

    @__import__('unittest').skipUnless(HAS_YAML, 'PyYAML 未導入: D-6 YAML テストは実行不可')
    def test_profile_example_unknown_tag_other_provider(self):
        profile = self.root / 'profile'
        profile.mkdir()
        patch = (ROOT / 'config/harness/cordis.patch.example.yml').read_text()
        (profile / 'cordis.patch.yml').write_text(patch + '\n- id: unrelated\n  config: !!js "do not evaluate"\n')
        env = self.root / '.env'
        env.write_text('OTHER=SECRET_OTHER\nOLLAMA_API_KEY=SECRET_TARGET\n')
        before = env.stat(), env.read_bytes()
        self.assertEqual(e.profile_diagnostic(profile, env, 'http://127.0.0.1:11434/v1')[0], 'PASS')
        self.assertEqual((env.stat(), env.read_bytes()), before)
        self.assertNotIn('SECRET', self.output.getvalue())

    @__import__('unittest').skipUnless(HAS_YAML, 'PyYAML 未導入: D-6 YAML テストは実行不可')
    def test_profile_missing_bad_ambiguous_opaque(self):
        profile = self.root / 'profile'
        profile.mkdir()
        env = self.root / '.env'
        env.write_text('OLLAMA_API_KEY=x\n')
        patch = (ROOT / 'config/harness/cordis.patch.example.yml').read_text()
        for raw in ('{bad', '{}', patch + '\n- id: agent-default-model\n  config: {}',
                    patch.replace('api: openai-completions', 'api: !!js code'),
                    patch.replace('api: openai-completions', 'api: openai-completions\n        api: other'),
                    patch.replace('model: qwen3.8:27b-mlx', 'model: missing')):
            (profile / 'cordis.patch.yml').write_text(raw)
            self.assertEqual(e.guarded(lambda: e.profile_diagnostic(profile, env, 'http://127.0.0.1:11434/v1'), True)[0], 'UNKNOWN')
        self.assertEqual(e.guarded(lambda: e.profile_diagnostic(self.root / 'different-profile', env, 'http://127.0.0.1:11434/v1'), True)[0], 'UNKNOWN')

    @__import__('unittest').skipUnless(HAS_YAML, 'PyYAML 未導入: D-6 YAML テストは実行不可')
    def test_yaml_merge_and_alias_overrides_remain_supported(self):
        patch = self.root / 'patch.yml'
        patch.write_text('- id: other\n  config: &base\n    value: old\n- id: another\n  config:\n    <<: *base\n    value: new\n')
        entries = e.read_patch(patch)
        self.assertEqual(e.unique_map(entries[1]['config'])['value'], 'new')

    def test_pyyaml_absent_one_and_unknown(self):
        with mock.patch.dict(sys.modules, {'yaml': None}):
            self.raises_code(c, 1, e.read_patch, self.root / 'patch.yml')
            self.assertEqual(e.guarded(lambda: e.read_patch(self.root / 'patch.yml'), True)[0], 'UNKNOWN')

    def test_plugin_actual_profile_no_search(self):
        good = self.root / 'good/node_modules/dsh-comfyui/package.json'
        write_json(good, dict(name='dsh-comfyui', version='0.5.4'))
        self.assertEqual(e.plugin_diagnostic(self.root / 'good')[0], 'PASS')
        self.assertEqual(e.guarded(lambda: e.plugin_diagnostic(self.root / 'other'))[0], 'FAIL')
        write_json(good, dict(name='dsh-comfyui', version='0.5.3'))
        self.assertEqual(e.plugin_diagnostic(self.root / 'good')[0], 'FAIL')

    def test_lsof_ipv4_ipv6_wildcard_lan_and_parse_failures(self):
        for host, expected in (('127.0.0.1', 'PASS'), ('[::1]', 'PASS'), ('*', 'FAIL'),
                               ('0.0.0.0', 'FAIL'), ('[::]', 'FAIL'), ('192.168.0.1', 'FAIL')):
            self.assertEqual(e.address_diagnostic(e.parse_lsof(f'p1\nn{host}:8188\nTST=LISTEN\n'))[0], expected)
        mixed = e.parse_lsof('p1\nn127.0.0.1:8188\np2\nn*:2\n')
        self.assertEqual(e.address_diagnostic(mixed)[0], 'FAIL')
        for raw in ('pbad', 'n127.0.0.1:8188', 'p1\nngarbage', 'p1\nnlocalhost:1', 'p1\nTST=ESTABLISHED'):
            self.raises_code(c, 1, e.parse_lsof, raw)
        self.assertEqual(e.address_diagnostic({})[0], 'UNKNOWN')

    def test_port_owner_children_all_listeners(self):
        table = {1: (0, 10, 'python'), 2: (1, 10, 'worker'), 3: (1, 20, 'other'), 4: (0, 4, 'ollama')}
        def listeners(lsof, pids=None, port=None):
            if port:
                return {1: [('127.0.0.1', port)]} if port == 9000 else {4: [('::1', port)]}
            return {p: [('192.168.0.1' if p == 2 else '127.0.0.1', 10000)] for p in pids}
        with mock.patch.object(e, 'listeners', side_effect=listeners) as lsof:
            self.assertEqual(e.port_diagnostic(('http://127.0.0.1:9000', 'http://127.0.0.1:9100'), table, self.root / 'lsof')[0], 'FAIL')
            self.assertEqual(lsof.call_args_list[1].kwargs['pids'], {1, 2})
        with mock.patch.object(e, 'listeners', return_value={}):
            self.assertEqual(e.port_diagnostic(('http://127.0.0.1:9000',), table, self.root / 'lsof')[0], 'UNKNOWN')

    def test_port_owner_vanished_not_hidden_by_other_service(self):
        # The first service owns its port, then disappears before its listeners are listed.
        # The healthy second service must not turn that into PASS.
        table = {1: (0, 10, 'python'), 4: (0, 4, 'ollama')}
        def listeners(lsof, pids=None, port=None):
            if port:
                return {1: [('127.0.0.1', port)]} if port == 9000 else {4: [('127.0.0.1', port)]}
            return {} if pids == {1} else {4: [('127.0.0.1', 9100)]}
        for urls in (('http://127.0.0.1:9000', 'http://127.0.0.1:9100'),
                     ('http://127.0.0.1:9100', 'http://127.0.0.1:9000')):
            with mock.patch.object(e, 'listeners', side_effect=listeners):
                self.assertEqual(e.port_diagnostic(urls, table, self.root / 'lsof')[0], 'UNKNOWN', urls)
        # Control: both services confirmed on loopback.
        def healthy(lsof, pids=None, port=None):
            owner = 1 if (port == 9000 or pids == {1}) else 4
            return {owner: [('127.0.0.1', 9000 if owner == 1 else 9100)]}
        with mock.patch.object(e, 'listeners', side_effect=healthy):
            self.assertEqual(e.port_diagnostic(('http://127.0.0.1:9000', 'http://127.0.0.1:9100'),
                                               table, self.root / 'lsof')[0], 'PASS')

    def test_harness_exact_name_union_children(self):
        table = {1: (0, 1, '/Applications/DeepSeek Harness'), 2: (0, 2, 'DeepSeek Harness'),
                 3: (2, 3, 'child'), 4: (0, 4, 'DeepSeek Harness Other')}
        with mock.patch.object(e, 'listeners', return_value={3: [('*', 1000)]}) as listeners:
            self.assertEqual(e.harness_diagnostic('DeepSeek Harness', table, self.root / 'lsof')[0], 'FAIL')
            self.assertEqual(listeners.call_args.kwargs['pids'], {1, 2, 3})
        self.assertEqual(e.harness_diagnostic('Missing', table, self.root / 'lsof')[0], 'UNKNOWN')

    def test_lsof_no_matches_vs_permission_and_fixed_argv(self):
        path = exec_file(self.root / 'lsof')
        for outcome, expected in ((argparse.Namespace(returncode=1, stdout='', stderr=''), True),
                                  (argparse.Namespace(returncode=1, stdout='', stderr='permission'), False)):
            with mock.patch.object(c.subprocess, 'run', return_value=outcome) as run:
                if expected:
                    self.assertEqual(e.listeners(path, pids={2, 1}), {})
                else:
                    self.raises_code(c, 1, e.listeners, path, pids={2, 1})
                argv = run.call_args.args[0]
                self.assertIn('1,2', argv)
                self.assertIn('-sTCP:LISTEN', argv)
                self.assertFalse(run.call_args.kwargs['shell'])

    def test_process_table_and_children(self):
        with mock.patch.object(c, 'command', return_value=argparse.Namespace(stdout='1 0 1 /Applications/DeepSeek Harness\n2 1 1 child\n')):
            table = e.process_table(self.root / 'ps')
            self.assertEqual(e.descendants(table, {1}), {1, 2})
        with mock.patch.object(c, 'command', return_value=argparse.Namespace(stdout='not a process table')):
            self.raises_code(c, 1, e.process_table, self.root / 'ps')

    def test_aggregate_any_failure_unknown(self):
        normal = [('PASS', 'ok', 'keep')] * 9
        self.assertEqual(e.aggregate(normal), 0)
        for i in range(9):
            for state in ('FAIL', 'UNKNOWN'):
                changed = list(normal)
                changed[i] = (state, 'broken', 'fix')
                self.assertEqual(e.aggregate(changed), 1)
        for i in range(1, 10):
            self.assertIn(f'D-{i}', self.output.getvalue())

    def test_full_diagnostics_api_faults_individual(self):
        args = argparse.Namespace(comfy_url='http://127.0.0.1:9000', ollama_url='http://127.0.0.1:9100/v1',
                                  http_timeout=5, profile_dir=str(self.root), env_file=str(self.root / '.env'),
                                  ps=str(exec_file(self.root / 'ps')), lsof=str(exec_file(self.root / 'lsof')),
                                  harness_process='DeepSeek Harness', verbose=True)
        def response(url, **kwargs):
            if url.endswith('/system_stats'):
                return dict(system={}, devices=[])
            if '/object_info/' in url:
                name = url.rsplit('/', 1)[1]
                return {name: {'input': {}}}
            return dict(models=[dict(name=c.QWEN)])
        normal = ('PASS', 'fixture', 'keep')
        with mock.patch.object(c, 'request_json', side_effect=response), mock.patch.object(e, 'model_diagnostic', return_value=normal), mock.patch.object(e, 'ffmpeg_diagnostic', return_value=normal), mock.patch.object(e, 'profile_diagnostic', return_value=normal), mock.patch.object(e, 'plugin_diagnostic', return_value=normal), mock.patch.object(e, 'process_table', return_value={1: (0, 1, 'DeepSeek Harness')}), mock.patch.object(e, 'port_diagnostic', return_value=normal), mock.patch.object(e, 'harness_diagnostic', return_value=normal):
            self.assertEqual(e.diagnose(args), 0)
            self.assertIs(e.model_diagnostic.call_args.args[0]['verbose'], True)
            cases = [('/system_stats', {}), ('/api/tags', {'models': []})] + [('/object_info/' + name, {}) for name in c.NODES]
            for suffix, result in cases:
                def bad(url, **kwargs):
                    return result if url.endswith(suffix) else response(url, **kwargs)
                with mock.patch.object(c, 'request_json', side_effect=bad):
                    self.assertEqual(e.diagnose(args), 1)
            with mock.patch.object(c, 'request_json', side_effect=c.H3Error(6, 'HTTP', '無応答', '起動')):
                self.assertEqual(e.diagnose(args), 1)
