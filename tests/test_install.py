import argparse
import json
import os
import shutil
from unittest import mock
from support import Case, load, exec_file, write_json

i = load('install_h3_node')
c = i.c


class InstallTests(Case):
    def test_requirements_fixed_markers_and_rejections(self):
        path = self.root / 'requirements.txt'
        path.write_text('mlx>=0.32.0; sys_platform == "darwin" and platform_machine == "arm64"\nhuggingface_hub>=0.30\nnumpy>=1.26\n')
        i.requirements(path)
        for text in ('--index-url https://other.invalid', '-r other.txt', 'git+https://x', 'pkg @ https://x', './local', '-e pkg'):
            path.write_text(text)
            self.raises_code(c, 2, i.requirements, path)

    def test_pip_plan_existing_same_update_downgrade_refused(self):
        for version in ('1', '2', '0'):
            report = dict(install=[dict(metadata=dict(name='Existing_Pkg', version=version))])
            self.raises_code(c, 5, i.check_plan, report, {'existing-pkg': '1'})
        self.assertEqual(i.check_plan(dict(install=[dict(metadata=dict(name='new', version='1'))]), {'existing': '1'}), {'new': '1'})
        for bad in ({}, dict(install=None), dict(install=[{}])):
            self.raises_code(c, 1, i.check_plan, bad, {})
        self.raises_code(c, 1, i.pip_json, '{broken')

    def test_checkout_fixed_clean_allows_untracked(self):
        target = self.root / 'node'
        target.mkdir()
        (target / '__pycache__').mkdir()
        with mock.patch.object(c, 'command', side_effect=[argparse.Namespace(stdout=c.NODE_SHA), argparse.Namespace(stdout='')]) as run:
            i.check_checkout(self.root / 'git', target, 30)
            self.assertIn('--untracked-files=no', run.call_args.args[0])
        for head, dirty in (('other', ''), (c.NODE_SHA, ' M nodes.py')):
            with mock.patch.object(c, 'command', side_effect=[argparse.Namespace(stdout=head), argparse.Namespace(stdout=dirty)]):
                self.raises_code(c, 5, i.check_checkout, self.root / 'git', target, 30)
        self.raises_code(c, 5, i.check_checkout, self.root / 'git', self.root / 'missing', 30)

    def test_links_same_different_broken(self):
        target = exec_file(self.root / 'real')
        alias = self.root / 'link'
        self.assertTrue(i.check_link(alias, target))
        alias.symlink_to(target)
        before = alias.lstat()
        self.assertFalse(i.check_link(alias, target))
        self.assertEqual(alias.lstat(), before)
        self.raises_code(c, 5, i.check_link, alias, self.root / 'other')
        alias.unlink()
        alias.symlink_to(self.root / 'missing')
        self.raises_code(c, 5, i.check_link, alias, target)

    def setup_install(self):
        core = self.root / 'core'
        venv = core / '.venv'
        python = exec_file(venv / 'bin/python')
        (venv / 'pyvenv.cfg').write_text('home = fixture')
        git = exec_file(self.root / 'git')
        ffmpeg = exec_file(self.root / 'brew/ffmpeg')
        exec_file(self.root / 'brew/ffprobe')
        graph = c.load_graph()
        graph['3']['inputs']['ffmpeg_path'] = str(ffmpeg)
        target = core / 'custom_nodes' / c.NODE_DIR
        target.mkdir(parents=True)
        (target / 'requirements.txt').write_text('new_pkg>=1\n')
        (target / 'untracked.txt').write_text('keep')
        return argparse.Namespace(comfy_root=str(core), venv=str(venv), models_dir=str(self.root / 'shared'),
                                  git=str(git), command_timeout=1800), graph, target

    def test_install_isolated_index_configuration_and_shared_creation(self):
        args, graph, target = self.setup_install()
        calls = []
        count = 0
        # These user config files must remain unchanged and cannot select endpoints.
        pipconf = self.root / 'pip.conf'
        gitconf = self.root / 'gitconfig'
        pipconf.write_text('[global]\nindex-url=https://alternate.invalid\n')
        gitconf.write_text('[url "https://alternate.invalid/"]\ninsteadOf=https://github.com/\n')
        before = pipconf.read_bytes(), gitconf.read_bytes()
        def run(argv, **kwargs):
            nonlocal count
            calls.append((argv, kwargs))
            stdout = ''
            if argv[0] == args.git:
                stdout = c.NODE_SHA if 'rev-parse' in argv else ''
            elif 'list' in argv:
                count += 1
                stdout = json.dumps([dict(name='existing', version='1')] + ([] if count == 1 else [dict(name='new_pkg', version='1')]))
            elif '--report' in argv:
                write_json(c.Path(argv[argv.index('--report') + 1]), dict(install=[dict(metadata=dict(name='new_pkg', version='1'))]))
            return argparse.Namespace(returncode=0, stdout=stdout, stderr='')
        with mock.patch.object(c, 'load_graph', return_value=graph), mock.patch.object(c.subprocess, 'run', side_effect=run), mock.patch.dict(os.environ, {'PIP_CONFIG_FILE': str(pipconf), 'GIT_CONFIG_GLOBAL': str(gitconf), 'PIP_INDEX_URL': 'bad', 'SECRET': 'MARKER'}):
            self.assertEqual(i.install(args), 0)
        self.assertEqual((pipconf.read_bytes(), gitconf.read_bytes()), before)
        self.assertEqual((target / 'untracked.txt').read_text(), 'keep')
        self.assertTrue((self.root / 'shared').is_dir())
        self.assertEqual((self.root / 'core/models/minimax_h3').resolve(), (self.root / 'shared').resolve())
        pipcalls = [(argv, kw) for argv, kw in calls if 'pip' in argv]
        self.assertTrue(all('-I' in argv and '--isolated' in argv for argv, _ in pipcalls))
        for argv, kw in pipcalls:
            self.assertEqual(kw['env']['PIP_CONFIG_FILE'], os.devnull)
            self.assertNotIn('PIP_INDEX_URL', kw['env'])
            self.assertNotIn('SECRET', kw['env'])
            self.assertFalse(kw['shell'])
            if 'install' in argv:
                self.assertEqual(argv[argv.index('--index-url') + 1], 'https://pypi.org/simple')
        for argv, kw in calls:
            if argv[0] == args.git:
                self.assertEqual(kw['env']['GIT_CONFIG_GLOBAL'], os.devnull)
                self.assertEqual(kw['env']['GIT_CONFIG_NOSYSTEM'], '1')

    def test_install_existing_plan_nonchange(self):
        args, graph, target = self.setup_install()
        def command(argv, *rest, **kwargs):
            if '--report' in argv:
                write_json(c.Path(argv[argv.index('--report') + 1]), dict(install=[dict(metadata=dict(name='existing', version='2'))]))
            stdout = '[{"name":"existing","version":"1"}]' if 'list' in argv else ''
            return argparse.Namespace(stdout=stdout)
        with mock.patch.object(c, 'load_graph', return_value=graph), mock.patch.object(i, 'check_checkout'), mock.patch.object(c, 'command', side_effect=command) as run:
            self.raises_code(c, 5, i.install, args)
            self.assertFalse(any('install' in call.args[0] and '--dry-run' not in call.args[0] for call in run.call_args_list))
        self.assertFalse((self.root / 'shared').exists())
        self.assertFalse((self.root / 'core/models/minimax_h3').exists())

    def test_install_preflight_conflict_no_commands(self):
        args, graph, target = self.setup_install()
        (self.root / 'core/.venv/bin/ffmpeg').write_text('existing')
        with mock.patch.object(c, 'load_graph', return_value=graph), mock.patch.object(c, 'command') as run:
            self.raises_code(c, 5, i.install, args)
            run.assert_not_called()

    def test_install_new_checkout_fixed_repo_sha_and_temporary_cleanup(self):
        args, graph, target = self.setup_install()
        shutil.rmtree(target)  # this test's tempfile fixture only
        stage = []
        def command(argv, *rest, **kwargs):
            stdout = ''
            if 'init' in argv:
                source = c.Path(argv[-1])
                source.mkdir()
                (source / 'requirements.txt').write_text('numpy>=1\n')
                stage.append(source)
            if 'fetch' in argv:
                self.assertIn(c.NODE_REPO, argv)
                self.assertEqual(argv[-1], c.NODE_SHA)
            if 'rev-parse' in argv:
                stdout = c.NODE_SHA
            if 'list' in argv:
                stdout = '[]'
            if '--report' in argv:
                write_json(c.Path(argv[argv.index('--report') + 1]), dict(install=[]))
            return argparse.Namespace(stdout=stdout)
        with mock.patch.object(c, 'load_graph', return_value=graph), mock.patch.object(c, 'command', side_effect=command) as run:
            self.assertEqual(i.install(args), 0)
            self.assertTrue(any('checkout' in call.args[0] and '--detach' in call.args[0] for call in run.call_args_list))
        self.assertTrue((target / 'requirements.txt').is_file())
        self.assertTrue(stage)
        self.assertFalse(stage[0].parent.exists())

    def test_install_postcheck_detects_existing_version_change(self):
        args, graph, target = self.setup_install()
        lists = 0
        def command(argv, *rest, **kwargs):
            nonlocal lists
            stdout = ''
            if 'list' in argv:
                lists += 1
                stdout = json.dumps([dict(name='existing', version='1' if lists == 1 else '2')])
            if '--report' in argv:
                write_json(c.Path(argv[argv.index('--report') + 1]), dict(install=[]))
            return argparse.Namespace(stdout=stdout)
        with mock.patch.object(c, 'load_graph', return_value=graph), mock.patch.object(i, 'check_checkout'), mock.patch.object(c, 'command', side_effect=command):
            self.raises_code(c, 6, i.install, args)
        self.assertFalse((self.root / 'shared').exists())

    def test_command_timeout_pip_safe_message(self):
        exe = exec_file(self.root / 'python')
        with mock.patch.object(c.subprocess, 'run', side_effect=c.subprocess.TimeoutExpired('SECRET', 1)):
            self.assertEqual(c.cli(lambda: c.command([exe], timeout=1, kind='pip')), 7)
        self.assertIn('変更が途中', self.error.getvalue())
        self.assertIn('pip check', self.error.getvalue())
        self.assertNotIn('SECRET', self.error.getvalue())

    def test_command_nonzero_and_pip_absent(self):
        exe = exec_file(self.root / 'python')
        with mock.patch.object(c.subprocess, 'run', return_value=argparse.Namespace(returncode=1, stdout='SECRET', stderr='SECRET')):
            self.raises_code(c, 1, c.command, [exe, '-I', '-m', 'pip', '--isolated', '--version'], kind='pip', code=1)
