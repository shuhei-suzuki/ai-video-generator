import argparse
import copy
import os
import sys
from unittest import mock
from support import Case, load, fixture_manifest, write_json

d = load('download_h3_models')
c = d.c


class DownloadTests(Case):
    def args(self, **changes):
        path = self.root / 'manifest.json'
        write_json(path, fixture_manifest(c))
        return argparse.Namespace(models_dir=str(self.root / 'models'), manifest=str(path),
                                  models=changes.pop('models', ['base', 'int8', 'turbo']),
                                  accept_license=changes.pop('accept_license', False),
                                  test_free_bytes=changes.pop('test_free_bytes', None), **changes)

    def test_consent_each_model_non_tty_no_transfer(self):
        for model in ('base', 'int8', 'turbo'):
            with self.subTest(model=model), mock.patch.object(d.sys.stdin, 'isatty', return_value=False), mock.patch.object(d, 'hub_client') as hub:
                self.raises_code(c, 3, d.acquire, self.args(models=[model]))
                hub.assert_not_called()

    def test_consent_yes_flag_eof_refusal(self):
        d.consent(True)
        turbo = c.MODELS[2]
        self.assertIn(f"{turbo['revision']}/README.md", self.output.getvalue())
        self.assertNotIn(f"{turbo['revision']}/LICENSE", self.output.getvalue())
        self.assertIn('https://www.apache.org/licenses/LICENSE-2.0', self.output.getvalue())
        with mock.patch.object(d.sys.stdin, 'isatty', return_value=True), mock.patch('builtins.input', return_value='yes'):
            d.consent(False)
        for value in ('no', ''):
            with mock.patch.object(d.sys.stdin, 'isatty', return_value=True), mock.patch('builtins.input', return_value=value):
                self.raises_code(c, 3, d.consent, False)
        with mock.patch.object(d.sys.stdin, 'isatty', return_value=True), mock.patch('builtins.input', side_effect=EOFError):
            self.raises_code(c, 3, d.consent, False)

    def test_all_complete_no_hub_no_consent_no_capacity(self):
        args = self.args()
        for m in fixture_manifest(c)['models']:
            target = self.root / 'models' / m['local_dir'] / 'test.bin'
            target.parent.mkdir(parents=True)
            target.write_bytes(b'x' * m['total_bytes'])
        with mock.patch.object(d, 'hub_client', side_effect=ImportError), mock.patch.object(d, 'consent') as consent, mock.patch.object(d, 'capacity') as capacity:
            self.assertEqual(d.acquire(args), 0)
            consent.assert_not_called()
            capacity.assert_not_called()

    def test_conflict_each_model_precedes_consent(self):
        for i, m in enumerate(c.MODELS):
            args = self.args(models=[m['key']])
            target = self.root / 'models' / m['local_dir'] / 'test.bin'
            target.parent.mkdir(parents=True, exist_ok=True)
            for size in (1, 20):
                target.write_bytes(b'x' * size)
                before = target.stat()
                with mock.patch.object(d, 'hub_client') as hub:
                    self.raises_code(c, 5, d.acquire, args)
                    hub.assert_not_called()
                self.assertEqual(target.stat(), before)

    def test_size_incomplete_extra_shared_d3(self):
        data = self.complete(c)
        extra = self.root / data['models'][0]['local_dir'] / 'extra.txt'
        extra.write_text('allowed')
        self.assertTrue(all(s == '完了' for _, _, s in c.inspect_models(self.root, data['models'])))
        incomplete = extra.parent / '.cache/huggingface/download/extra.incomplete'
        incomplete.parent.mkdir(parents=True)
        incomplete.write_bytes(b'')
        rows = c.inspect_models(self.root, data['models'])
        self.assertIn('途中', [s for _, _, s in rows])
        self.assertEqual(extra.read_text(), 'allowed')

    def test_extra_cache_symlink_rejected(self):
        data = self.complete(c)
        (self.root / data['models'][0]['local_dir'] / '.cache').symlink_to(self.root)
        self.raises_code(c, 5, c.inspect_models, self.root, data['models'])

    def test_capacity_boundary_and_clamp(self):
        need = 4 + 1024**3
        with mock.patch.object(d.shutil, 'disk_usage', return_value=argparse.Namespace(free=need - 1)):
            self.raises_code(c, 4, d.capacity, self.root / 'not/yet/there', 4, None)
            self.raises_code(c, 4, d.capacity, self.root, 4, need + 100)
        with mock.patch.object(d.shutil, 'disk_usage', return_value=argparse.Namespace(free=need)) as disk:
            d.capacity(self.root / 'not/yet', 4, None)
            self.assertEqual(disk.call_args.args[0], self.root.resolve())
            self.raises_code(c, 4, d.capacity, self.root, 4, need - 1)
            d.capacity(self.root, 4, need + 1)

    def test_acquire_missing_only_revision_token_recheck(self):
        args = self.args(accept_license=True, test_free_bytes=2**40)
        existing = self.root / 'models' / c.MODELS[0]['local_dir'] / 'test.bin'
        existing.parent.mkdir(parents=True)
        existing.write_bytes(b'xxxx')
        before = existing.stat()
        calls = []
        def download(**kwargs):
            calls.append(kwargs)
            m = next(m for m in fixture_manifest(c)['models'] if m['repo'] == kwargs['repo_id'])
            path = c.Path(kwargs['local_dir']) / kwargs['filename']
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'x' * m['total_bytes'])
        with mock.patch.object(d, 'hub_client', return_value=download), mock.patch.object(d, 'capacity') as capacity:
            self.assertEqual(d.acquire(args), 0)
            self.assertEqual(len(calls), 2)
            self.assertEqual(capacity.call_count, 4)  # before/after mkdir + 2 files
            self.assertTrue(all(call.args[2] == 2**40 for call in capacity.call_args_list))
        self.assertEqual(existing.stat(), before)
        for call in calls:
            m = next(m for m in c.MODELS if m['repo'] == call['repo_id'])
            self.assertEqual(call['revision'], m['revision'])
            self.assertIs(call['token'], False)

    def test_capacity_after_mkdir_stops_transfer(self):
        args = self.args(accept_license=True)
        error = c.H3Error(4, '容量', '不足', '確認')
        transfer = mock.Mock()
        with mock.patch.object(d, 'hub_client', return_value=transfer), mock.patch.object(d, 'capacity', side_effect=[None, error]):
            self.raises_code(c, 4, d.acquire, args)
            transfer.assert_not_called()

    def test_transfer_failure_retains_partial(self):
        args = self.args(models=['turbo'], accept_license=True)
        partial = self.root / 'models' / c.MODELS[2]['local_dir'] / 'test.bin'
        def broken(**kwargs):
            partial.parent.mkdir(parents=True)
            partial.write_bytes(b'x')
            raise RuntimeError('SECRET_MARKER')
        with mock.patch.object(d, 'hub_client', return_value=broken), mock.patch.object(d, 'capacity'):
            self.assertEqual(c.cli(lambda: d.acquire(args)), 6)
        self.assertEqual(partial.read_bytes(), b'x')
        self.assertNotIn('SECRET_MARKER', self.error.getvalue())

    def test_hub_absent_old_and_fixed_environment(self):
        with mock.patch.dict(os.environ, {'HF_TOKEN': 'SECRET_MARKER', 'HF_ENDPOINT': 'bad'}, clear=True):
            with mock.patch.dict(sys.modules, {'huggingface_hub': None}):
                self.raises_code(c, 1, d.hub_client)
            self.assertEqual(os.environ['HF_ENDPOINT'], 'https://huggingface.co')
            self.assertEqual(os.environ['HF_HUB_DISABLE_IMPLICIT_TOKEN'], '1')
            self.assertNotIn('HF_TOKEN', os.environ)
            with mock.patch.dict(sys.modules, {'huggingface_hub': argparse.Namespace(__version__='0.30.0')}):
                self.raises_code(c, 1, d.hub_client)
            download = mock.Mock()
            with mock.patch.dict(sys.modules, {'huggingface_hub': argparse.Namespace(__version__='1.30.0', hf_hub_download=download)}):
                self.assertIs(d.hub_client(), download)
