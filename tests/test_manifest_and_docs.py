import argparse
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest import mock
from support import Case, ROOT, load, fixture_manifest, write_json

m = load('make_manifest', 'tools')
c = m.c


class ManifestTests(Case):
    def api(self, model):
        path = 'FL2VA/model_index.json' if model['key'] == 'base' else 'weights.bin'
        return dict(sha=model['revision'], siblings=[dict(rfilename=path, size=4), dict(rfilename='.gitattributes', size=1)])

    def test_fixed_api_paths_scope_sizes(self):
        for model in c.MODELS:
            result = m.from_api(model, self.api(model))
            self.assertEqual(result['total_bytes'], 4)
            self.assertEqual(len(result['files']), 1)
            bad = self.api(model)
            bad['sha'] = 'other'
            self.raises_code(c, 6, m.from_api, model, bad)

    def test_api_duplicate_bad_path_and_size(self):
        model = c.MODELS[0]
        for change in (dict(rfilename='../escape', size=4), dict(rfilename='ok', size=True), dict(rfilename='ok', size=-1)):
            bad = self.api(model)
            bad['siblings'].append(change)
            self.raises_code(c, 2, m.from_api, model, bad)
        bad = self.api(model)
        bad['siblings'].append(bad['siblings'][0])
        self.raises_code(c, 2, m.from_api, model, bad)

    def test_generation_no_token_fixed_url_and_compare_preserves(self):
        output = self.root / 'manifest.json'
        output.write_text('original')
        args = argparse.Namespace(output=str(output), compare_dir=str(self.root / 'empty'), http_timeout=3)
        def request(url, **kwargs):
            self.assertTrue(url.startswith('https://huggingface.co/api/models/'))
            self.assertTrue(url.endswith('?blobs=true'))
            model = next(model for model in c.MODELS if model['revision'] in url)
            return self.api(model)
        with mock.patch.object(c, 'request_json', side_effect=request):
            self.raises_code(c, 1, m.make, args)
        self.assertEqual(output.read_text(), 'original')
        args.compare_dir = None
        with mock.patch.object(c, 'request_json', side_effect=request):
            self.assertEqual(m.make(args), 0)
        c.validate_manifest(c.read_json(output))


class DocumentationTests(Case):
    def test_required_artifacts_and_no_personal_paths_weights(self):
        files = ['README.md', '.gitignore', 'config/h3_models.manifest.json',
                 'tools/make_manifest.py', 'config/harness/cordis.patch.example.yml', 'config/harness/dsh-env.example',
                 'workflows/minimax_h3_t2v_api.json', 'scripts/h3_common.py', 'scripts/install_h3_node.py',
                 'scripts/download_h3_models.py', 'scripts/check_env.py', 'scripts/submit_h3.py',
                 'scripts/register_dsh_workflow.py', 'doc/verification/issue-1-verification.md',
                 'doc/design/master/architecture.md', 'doc/design/master/operations.md', 'doc/design/master/security.md']
        for file in files:
            with self.subTest(file=file):
                self.assertTrue((ROOT / file).is_file())
                self.assertNotIn('/Users/', (ROOT / file).read_text())
        self.assertEqual(list(ROOT.rglob('*.safetensors')), [])

    def test_readme_boundary_security_help_examples(self):
        readme = (ROOT / 'README.md').read_text()
        for token in ('2026-10-12', 'ffmpeg_path', '--accept-license', 'CORS', '--listen', '900000',
                      '7200', '48', '262144', '65536', '年商', '2,000万', 'EU', '-I scripts/',
                      'allow-version', '--accept-risk', 'pip check', '既存項目', '手作業', '未検証'):
            self.assertIn(token, readme)
        for n in range(1, 10):
            self.assertIn(f'D-{n}', readme)

    def test_master_present_no_issue_history(self):
        for path in (ROOT / 'doc/design/master').glob('*.md'):
            text = path.read_text()
            self.assertNotIn('Issue', text)
            self.assertNotIn('issue-1', text)

    def test_help_with_isolated_python_no_optional_imports(self):
        # --help only: no real services/commands touched by any CLI.
        # Bypass the test's subprocess guard solely for launching --help.
        for file in ['scripts/install_h3_node.py', 'scripts/download_h3_models.py', 'scripts/check_env.py',
                     'scripts/submit_h3.py', 'scripts/register_dsh_workflow.py', 'tools/make_manifest.py']:
            result = self.real_run([sys.executable, '-I', str(ROOT / file), '--help'],
                                   capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('usage:', result.stdout)

    def test_old_executable_flags_not_accepted(self):
        for name in ['install_h3_node', 'submit_h3', 'register_dsh_workflow']:
            module = load(name)
            with mock.patch.object(sys, 'argv', [name, '--ffmpeg', '/invalid']), self.assertRaises(SystemExit) as raised:
                module.main()
            self.assertEqual(raised.exception.code, 2)

    def setUp(self):
        # Capture actual runner before Case patches it.
        self.real_run = subprocess.run
        super().setUp()
