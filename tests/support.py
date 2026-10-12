import argparse
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load(name, folder='scripts'):
    spec = importlib.util.spec_from_file_location(name, ROOT / folder / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture_manifest(c):
    models = []
    for i, model in enumerate(c.MODELS):
        models.append(dict(**copy.deepcopy(model), total_bytes=4 + i,
                           files=[dict(path='test.bin', size=4 + i)]))
    return dict(schema=1, models=models)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')


def exec_file(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('test fixture; never executed', encoding='utf-8')
    path.chmod(0o700)
    return path


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='h3-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.output = io.StringIO()
        self.error = io.StringIO()
        self.enterContext(contextlib.redirect_stdout(self.output))
        self.enterContext(contextlib.redirect_stderr(self.error))
        # All HTTP/child process effects must be explicitly stubbed by each test.
        self.enterContext(mock.patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('no network in tests')))
        self.enterContext(mock.patch('subprocess.run', side_effect=AssertionError('no live commands in tests')))

    def raises_code(self, c, expected_code, fn, *args, **kwargs):
        with self.assertRaises(c.H3Error) as raised:
            fn(*args, **kwargs)
        self.assertEqual(raised.exception.code, expected_code)
        return raised.exception

    def complete(self, c):
        data = fixture_manifest(c)
        for model in data['models']:
            path = self.root / model['local_dir'] / 'test.bin'
            path.parent.mkdir(parents=True)
            path.write_bytes(b'x' * model['total_bytes'])
        return data
