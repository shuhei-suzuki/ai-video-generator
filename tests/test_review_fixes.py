"""Offline regression coverage for security/contract fixes; fake home only."""
import argparse
import copy
import os
import shutil
from pathlib import Path
import sys
from unittest import mock
from support import Case, load, fixture_manifest, write_json, exec_file
from test_install import InstallTests
from test_submit import SubmitTests

c = load('h3_common')


class PathProtectionTests(Case):
    def protected(self):
        home = Path.home()
        protected = home / '.dsh'
        write_json(protected / '.env', {'fixture': True})
        write_json(protected / 'profiles/desktop/cordis.patch.yml', {'fixture': True})
        return home, protected

    def assert_denied(self, alias):
        home = Path.home()
        files = [home / '.dsh/.env', home / '.dsh/profiles/desktop/cordis.patch.yml']
        before = [(p.read_bytes(), c.file_identity(p.stat())) for p in files]
        for target in (alias / '.env', alias / 'profiles/desktop/cordis.patch.yml', alias / 'new/child'):
            for library in (False, True):
                self.raises_code(c, 2, c.writable, target, library=library)
        cases = [('make_manifest', 'tools', ['--output', str(alias / '.env')]),
                 ('register_dsh_workflow', 'scripts', ['--data-dir', str(alias / 'profiles/desktop')]),
                 ('download_h3_models', 'scripts', ['--models-dir', str(alias / 'profiles/desktop')]),
                 ('install_h3_node', 'scripts', ['--comfy-root', str(alias / 'profiles/desktop')])]
        for option in ('--instance', '--venv', '--models-dir'):
            cases.append(('install_h3_node', 'scripts', [option, str(alias / 'profiles/desktop')]))
        for name, folder, args in cases:
            with self.subTest(cli=name):
                module = load(name, folder)
                with mock.patch.object(sys, 'argv', [name] + args), mock.patch.object(module.c, 'command') as command, mock.patch.object(module.c, 'request_json') as request:
                    self.assertEqual(module.c.cli(module.main), 2)
                    command.assert_not_called()
                    request.assert_not_called()
        self.assertEqual([(p.read_bytes(), c.file_identity(p.stat())) for p in files], before)
        self.assertFalse((home / '.dsh/new').exists())

    def test_symlink_alias_all_writers_preserve_original(self):
        _, protected = self.protected()
        alias = self.root / 'alias'
        alias.symlink_to(protected, target_is_directory=True)
        self.assert_denied(alias)

    def test_mount_alias_identity_all_writers_preserve_original(self):
        # A mount alias retains its spelling after resolve(). A directory symlink
        # plus a lexical resolve for that prefix models this without mounting anything.
        _, protected = self.protected()
        alias = self.root / 'mount-view'
        alias.symlink_to(protected, target_is_directory=True)
        resolve = Path.resolve
        def mount_resolve(path, *args, **kwargs):
            return path.absolute() if path.absolute().is_relative_to(alias) else resolve(path, *args, **kwargs)
        with mock.patch.object(Path, 'resolve', mount_resolve):
            self.assert_denied(alias)
            allowed = alias / 'data/dsh-comfyui/workflows.json'
            c.writable(allowed, library=True)
            self.assertTrue(c.inside(allowed, protected))
            # Same identity logic also feeds existing links and read containment.
            installer = load('install_h3_node')
            self.assertFalse(installer.check_link(alias, protected))
            protected_video = protected / 'result.mp4'
            protected_video.write_bytes(b'fixture')
            self.assertTrue(c.inside(alias / 'result.mp4', protected))
            self.assertFalse(c.inside(alias / 'result.mp4', self.root / 'outside'))

    def test_case_alias_all_writers_preserve_original(self):
        home, protected = self.protected()
        alias = home / '.DSH'
        if not alias.exists() or not os.path.samefile(alias, protected):
            self.skipTest('一時ボリュームは大文字小文字を区別し、同実体の別名にならない')
        self.assert_denied(alias)
        c.writable(alias / 'DATA/DSH-COMFYUI/WORKFLOWS.JSON', library=True)

    def test_allowed_paths_missing_components_and_existing_case_distinction(self):
        _, protected = self.protected()
        for path in (protected / 'data/dsh-comfyui', protected / 'data/dsh-comfyui/workflows.json',
                     protected / 'DATA/DSH-COMFYUI/WORKFLOWS.JSON', self.root / 'outside'):
            c.writable(path, library=True)
        (protected / 'data/dsh-comfyui').mkdir(parents=True)
        c.writable(protected / 'data/dsh-comfyui/workflows.json', library=True)
        write_json(protected / 'data/dsh-comfyui/workflows.json', [])
        c.writable(protected / 'data/dsh-comfyui/workflows.json', library=True)
        other = protected / 'data/dsh-comfyui/WORKFLOWS.JSON'
        if not other.exists():
            other.write_text('different real file')
            self.raises_code(c, 2, c.writable, other, library=True)
        self.raises_code(c, 2, c.writable, protected / 'data/dsh-comfyui/child', library=True)


class ProcessAndOutputTests(Case):
    def test_all_child_input_is_closed(self):
        exe = exec_file(self.root / 'git')
        e = load('check_env')
        for common, call in ((c, lambda: c.command([exe], kind='git')),
                             (e.c, lambda: e.listeners(exe))):
            with mock.patch.object(common.subprocess, 'run', return_value=argparse.Namespace(returncode=0, stdout='', stderr='')) as run:
                call()
                self.assertEqual(run.call_args.kwargs['stdin'], common.subprocess.DEVNULL)
        self.assertEqual(c.child_env('git')['GIT_TERMINAL_PROMPT'], '0')

    def test_model_summary_verbose_and_pass_remedies(self):
        models = fixture_manifest(c)['models']
        models[0]['files'] = [dict(path='complete.bin', size=4), dict(path='missing.bin', size=4)]
        rows = [(models[0], dict(path='complete.bin', size=4), '完了'),
                (models[0], dict(path='missing.bin', size=4), '未取得'),
                (models[0], dict(path='.cache/huggingface/download/extra.incomplete', size=0), '途中')]
        c.model_summary(rows)
        self.assertIn('base: 完了 1 / 全 2 件', self.output.getvalue())
        self.assertNotIn('complete.bin', self.output.getvalue())
        self.assertIn('missing.bin', self.output.getvalue())
        c.model_summary(rows, verbose=True)
        self.assertIn('complete.bin', self.output.getvalue())
        self.output.truncate(0); self.output.seek(0)
        load('check_env').aggregate([('PASS', 'ok', 'unused'), ('FAIL', 'bad', 'repair'), ('UNKNOWN', 'unknown', 'retry')])
        self.assertEqual(self.output.getvalue().splitlines(),
                         ['D-1 PASS: ok', 'D-2 FAIL: bad; 対処: repair', 'D-3 UNKNOWN: unknown; 対処: retry'])

    def test_capacity_only_prints_changes_but_always_checks(self):
        d = load('download_h3_models')
        with mock.patch.object(d.shutil, 'disk_usage', return_value=argparse.Namespace(free=2**40)) as disk:
            state = d.capacity(self.root, 4, None)
            d.capacity(self.root, 4, None, state)
            d.capacity(self.root, 3, None, state)
            self.assertEqual(disk.call_count, 3)
        self.assertEqual(self.output.getvalue().count('容量:'), 2)

    def test_verbose_reaches_all_summary_consumers(self):
        data = fixture_manifest(c)
        models = self.root / 'models'
        for model in data['models']:
            target = models / model['local_dir'] / 'test.bin'
            target.parent.mkdir(parents=True)
            target.write_bytes(b'x' * model['total_bytes'])
        manifest = self.root / 'manifest.json'
        write_json(manifest, data)
        d = load('download_h3_models')
        with mock.patch.object(d.c, 'model_summary') as summary:
            self.assertEqual(d.acquire(argparse.Namespace(models_dir=str(models), manifest=str(manifest),
                                                         models=['base', 'int8', 'turbo'], verbose=True)), 0)
            self.assertIs(summary.call_args.args[1], True)
        e = load('check_env')
        entrance = self.root / 'core/models/minimax_h3'
        entrance.parent.mkdir(parents=True)
        entrance.symlink_to(models, target_is_directory=True)
        with mock.patch.object(e.c, 'model_summary') as summary:
            self.assertEqual(e.model_diagnostic(dict(models_dir=models, manifest=manifest,
                                                     comfy_root=self.root / 'core', verbose=True))[0], 'PASS')
            self.assertIs(summary.call_args.args[1], True)
        m = load('make_manifest', 'tools')
        with mock.patch.object(m, 'from_api', side_effect=data['models']), mock.patch.object(m.c, 'request_json'), \
                mock.patch.object(m.c, 'model_summary') as summary:
            self.assertEqual(m.make(argparse.Namespace(output=str(self.root / 'new.json'), compare_dir=str(models),
                                                      http_timeout=1, verbose=True)), 0)
            self.assertIs(summary.call_args.args[1], True)


class InstallFixTests(Case):
    setup_install = InstallTests.setup_install
    def test_missing_comfy_structure_no_creation_or_commands(self):
        args, graph, target = self.setup_install()
        for missing in ('main.py', 'custom_nodes'):
            path = self.root / 'core' / missing
            hidden = path.with_name(missing + '-hidden')
            path.rename(hidden)
            try:
                with mock.patch.object(self.common, 'command') as command:
                    exc = self.raises_code(self.common, 1, self.installer.install, args)
                    command.assert_not_called()
                self.assertIn('事前検査', exc.item)
                self.assertIn('未変更', exc.cause)
                self.assertIn('--comfy-root', exc.remedy)
                self.assertFalse((self.root / 'shared').exists())
            finally:
                hidden.rename(path)

    @property
    def installer(self):
        import test_install
        return test_install.i

    @property
    def common(self):
        return self.installer.c

    def test_precheck_and_wheel_failure_are_nonchanging(self):
        args, graph, _ = self.setup_install()
        cc = self.common
        for kind, code, text in (('check', 5, '既存環境の不整合を先に解消'),
                                 ('plan', 1, 'この環境向けの wheel が無い依存がある')):
            def command(argv, *rest, **kwargs):
                if (kind == 'check' and 'check' in argv) or (kind == 'plan' and '--dry-run' in argv):
                    cc.fail(6, 'pip', 'failed')
                return argparse.Namespace(stdout='[]' if 'list' in argv else '')
            with mock.patch.object(cc, 'load_graph', return_value=graph), mock.patch.object(self.installer, 'check_checkout'), mock.patch.object(cc, 'command', side_effect=command) as run:
                exc = self.raises_code(cc, code, self.installer.install, args)
            self.assertIn(text, exc.cause)
            self.assertIn('未変更', exc.cause)
            self.assertIn('再実行可', exc.cause)
            self.assertFalse(any('install' in call.args[0] and '--dry-run' not in call.args[0] for call in run.call_args_list))
            self.assertFalse((self.root / 'shared').exists())

    def test_install_failure_stage_changed_and_no_blind_retry(self):
        args, graph, _ = self.setup_install()
        cc = self.common
        def command(argv, *rest, **kwargs):
            if '--report' in argv:
                self.assertIn('--only-binary', argv)
                write_json(Path(argv[argv.index('--report') + 1]), dict(install=[dict(metadata=dict(name='new', version='1'))]))
            elif 'install' in argv:
                self.assertIn('--only-binary', argv)
                cc.fail(7, 'pip', '期限超過')
            return argparse.Namespace(stdout='[]' if 'list' in argv else '')
        with mock.patch.object(cc, 'load_graph', return_value=graph), mock.patch.object(self.installer, 'check_checkout'), mock.patch.object(cc, 'command', side_effect=command):
            exc = self.raises_code(cc, 7, self.installer.install, args)
        self.assertIn('依存導入', exc.item)
        self.assertIn('変更済み', exc.cause)
        self.assertIn('そのまま再実行しない', exc.cause)
        self.assertFalse((self.root / 'shared').exists())

    def test_failure_reports_acquisition_postcheck_placement_and_link(self):
        cc = self.common
        for stage in ('取得', '事後検査', '配置', 'リンク'):
            # A separate fixture per stage keeps published paths out of later cases.
            with self.subTest(stage=stage):
                with mock.patch.object(self, 'root', self.root / stage):
                    args, graph, target = self.setup_install()
                    if stage in ('取得', '配置'):
                        shutil.rmtree(target)
                    check_count = 0
                    def command(argv, *rest, **kwargs):
                        nonlocal check_count
                        if 'init' in argv:
                            source = Path(argv[-1])
                            source.mkdir()
                            (source / 'requirements.txt').write_text('numpy>=1')
                        if 'fetch' in argv and stage == '取得':
                            cc.fail(6, 'git', 'failed')
                        if 'check' in argv:
                            check_count += 1
                            if check_count == 2 and stage == '事後検査':
                                cc.fail(6, 'pip', 'failed')
                        if '--report' in argv:
                            write_json(Path(argv[argv.index('--report') + 1]), dict(install=[]))
                        return argparse.Namespace(stdout='[]' if 'list' in argv else '')
                    with mock.patch.object(cc, 'load_graph', return_value=graph), mock.patch.object(self.installer, 'check_checkout'), mock.patch.object(cc, 'command', side_effect=command), \
                            mock.patch.object(self.installer.shutil, 'move', side_effect=OSError('fixture')) as move, \
                            mock.patch.object(Path, 'symlink_to', side_effect=OSError('fixture')):
                        exc = self.raises_code(cc, 6 if stage in ('取得', '事後検査') else 1, self.installer.install, args)
                    self.assertEqual(exc.item, 'install ' + stage)
                    self.assertIn('未変更', exc.cause)  # no pip install ran
                    self.assertIn('再実行可', exc.cause)


class RegisterFixTests(Case):
    def test_practical_defaults_graph_unchanged_and_agent_description(self):
        r = load('register_dsh_workflow')
        graph = c.load_graph()
        params = c.parameters(graph)
        self.assertEqual({p['name']: p['default'] for p in params},
                         dict(prompt=graph['2']['inputs']['prompt'], width=768, height=448,
                              duration_seconds=5.0, steps=9, seed=0))
        self.assertTrue(params[-1]['random'])
        self.assertEqual((graph['2']['inputs']['width'], graph['2']['inputs']['height'], graph['2']['inputs']['steps']), (64, 64, 5))
        self.assertLessEqual(len(r.DESCRIPTION), 2000)
        for text in ('stereo audio', 'Apple Silicon', 'action: run', 'mode: sync', 'Async', 'English',
                     'multiples of 32', '768x448', '448x768', 'up to 15', '10-14', '48', '1 minute',
                     '1800000', '4200000', '900000', 'do not resubmit', 'one generation', 'minimax_h3/', 'ffmpeg_path'):
            self.assertIn(text, r.DESCRIPTION)
        args = argparse.Namespace(data_dir=str(self.root / 'library'), ps=str(exec_file(self.root / 'ps')), harness_process='fixture')
        with mock.patch.object(r.c, 'command', return_value=argparse.Namespace(stdout='')):
            r.register(args)
        path = self.root / 'library/workflows.json'
        entry = r.c.read_json(path)[0]
        self.assertEqual(entry['workflow'], graph)
        self.assertEqual(entry['description'], r.DESCRIPTION)
        self.assertEqual(entry['tags'], r.TAGS)

    def test_description_tags_and_terminal_control_characters(self):
        r = load('register_dsh_workflow')
        args = argparse.Namespace(data_dir=str(self.root / 'library'))
        path = self.root / 'library/workflows.json'
        entry = dict(id='id\x1b[31m\n', name=c.NAME, workflow=c.load_graph(),
                     parameters=c.parameters(c.load_graph()), description=r.DESCRIPTION, tags=r.TAGS)
        write_json(path, [entry])
        original = path.read_bytes(), c.file_identity(path.stat())
        self.assertEqual(r.register(args), 0)
        self.assertEqual((path.read_bytes(), c.file_identity(path.stat())), original)
        self.assertIn('"id\\u001b[31m\\n"', self.output.getvalue())
        for field in ('description', 'tags', 'workflow'):
            changed = copy.deepcopy(entry)
            if field == 'workflow':
                changed[field]['2']['inputs']['evil\x1b[31m\n'] = 1
            else:
                changed[field] = 'different'
            write_json(path, [changed])
            before = path.read_bytes(), c.file_identity(path.stat())
            self.raises_code(r.c, 5, r.register, args)
            self.assertEqual((path.read_bytes(), c.file_identity(path.stat())), before)
        self.assertNotIn('\x1b', self.output.getvalue())


class SubmitFixTests(Case):
    setup_graph = SubmitTests.setup_graph
    entry = SubmitTests.entry
    args = SubmitTests.args
    streams = SubmitTests.streams
    def test_missing_verify_id_fails_immediately(self):
        import test_submit
        ss, cc = test_submit.s, test_submit.c
        with mock.patch.object(cc, 'request_json', side_effect=[{}, cc.H3Error(6, 'fixture', 'unexpected polling', 'fixture')]) as request, mock.patch.object(ss.time, 'sleep') as sleep:
            exc = self.raises_code(cc, 2, ss.submit, self.args(verify_history='missing'))
            self.assertIn('履歴に無い ID', exc.cause)
            self.assertEqual(request.call_count, 1)
            sleep.assert_not_called()

    def test_history_public_type_message_and_comparison_targets(self):
        import test_submit
        ss, cc = test_submit.s, test_submit.c
        graph = self.setup_graph()
        good = self.entry(graph)
        for key, value in (('prompt', 1), ('width', '64'), ('height', True),
                           ('duration_seconds', '1'), ('steps', []), ('seed', -1)):
            bad = copy.deepcopy(good)
            bad['prompt'][2]['2']['inputs'][key] = value
            with mock.patch.object(cc, 'command') as command:
                exc = self.raises_code(cc, 8, ss.verify_entry, bad, graph, None, self.root / 'output', 3)
                self.assertEqual(exc.cause, '履歴の公開値の型が不正')
                command.assert_not_called()
        with mock.patch.object(cc, 'inspect_video'):
            ss.verify_entry(good, graph, None, self.root / 'output', 3)
            ss.verify_entry(good, graph, dict(id='safe\x1b\n', workflow=graph), self.root / 'output', 3)
        self.assertIn('リポジトリのワークフロー / 登録項目なし', self.output.getvalue())
        self.assertIn('登録項目 id="safe\\u001b\\n"', self.output.getvalue())
        self.assertNotIn('\x1b', self.output.getvalue())

    def test_decode_disables_stdin(self):
        import test_submit
        cc = test_submit.c
        graph = self.setup_graph()
        with mock.patch.object(cc, 'command', side_effect=[argparse.Namespace(stdout=cc.json.dumps(self.streams()), stderr=''),
                                                        argparse.Namespace(stdout='', stderr='')]) as command:
            cc.inspect_video(self.root / 'fixture.mp4', 64, 64, graph)
        self.assertIn('-nostdin', command.call_args.args[0])


# unittest discovery also inspects imported TestCase classes.
del InstallTests, SubmitTests
