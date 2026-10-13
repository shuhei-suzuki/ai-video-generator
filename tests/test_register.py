import argparse
import copy
import os
from pathlib import Path
import stat
import uuid
from unittest import mock
from support import Case, load, write_json, exec_file

r = load('register_dsh_workflow')
c = r.c


class RegisterTests(Case):
    def args(self):
        return argparse.Namespace(data_dir=str(self.root / 'data'), ps=str(exec_file(self.root / 'ps')),
                                  harness_process='DeepSeek Harness')

    def entry(self):
        graph = c.load_graph()
        return dict(id=str(uuid.uuid4()), name=c.NAME, workflow=graph, parameters=c.parameters(graph),
                    description=r.DESCRIPTION, tags=r.TAGS, unknown='keep')

    def test_add_uuid4_preserve_unknown_and_warning(self):
        args = self.args()
        path = self.root / 'data/workflows.json'
        other = dict(id='other', name='other', workflow={'x': dict(class_type='Other', inputs={})}, unknown={'secret': 'not displayed'})
        write_json(path, [other])
        path.chmod(0o640)
        with mock.patch.object(c, 'command', return_value=argparse.Namespace(stdout='/Applications/DeepSeek Harness\n')):
            self.assertEqual(r.register(args), 0)
        entries, entry = c.read_library(path)
        self.assertEqual(entries[0], other)
        self.assertEqual(uuid.UUID(entry['id']).version, 4)
        self.assertTrue(all(uuid.UUID(p['id']).version == 4 for p in entry['parameters']))
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o640)
        self.assertIn('同時更新', self.error.getvalue())
        self.assertNotIn('not displayed', self.output.getvalue())

    def test_create_parent_new_mode(self):
        args = self.args()
        with mock.patch.object(c, 'command', return_value=argparse.Namespace(stdout='')):
            self.assertEqual(r.register(args), 0)
        path = self.root / 'data/workflows.json'
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(list(path.parent.glob('.h3-*')), [])

    def test_same_content_different_ids_byte_unchanged(self):
        args = self.args()
        path = self.root / 'data/workflows.json'
        entry = self.entry()
        write_json(path, [entry])
        before = path.read_bytes(), path.stat()
        self.assertEqual(r.register(args), 0)
        self.assertEqual((path.read_bytes(), path.stat()), before)

    def test_different_workflow_and_parameter_nonchange(self):
        args = self.args()
        path = self.root / 'data/workflows.json'
        for kind in ('fixed', 'default', 'extra_parameter', 'metadata'):
            entry = self.entry()
            if kind == 'fixed':
                entry['workflow']['1']['inputs']['memory_limit_gb'] = 64
            elif kind == 'default':
                entry['parameters'][1]['default'] = 64
            elif kind == 'extra_parameter':
                entry['parameters'].append(dict(name='ffmpeg_path'))
            else:
                entry['parameters'][1]['max'] = 2048
            write_json(path, [entry])
            before = path.read_bytes(), path.stat()
            self.raises_code(c, 5, r.register, args)
            self.assertEqual((path.read_bytes(), path.stat()), before)
        self.assertIn('workflow/1/inputs/memory_limit_gb', self.output.getvalue())
        self.assertIn('parameters/1/default', self.output.getvalue())

    def test_bad_library_json_nonlist_duplicate_invalid(self):
        args = self.args()
        path = self.root / 'data/workflows.json'
        for raw in ('{bad', '{}', '[1]', c.json.dumps([self.entry(), self.entry()])):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(raw)
            before = path.read_bytes()
            self.raises_code(c, 2, r.register, args)
            self.assertEqual(path.read_bytes(), before)

    def test_library_link_refused(self):
        args = self.args()
        path = self.root / 'data/workflows.json'
        path.parent.mkdir()
        source = self.root / 'source.json'
        write_json(source, [])
        path.symlink_to(source)
        self.raises_code(c, 2, r.register, args)
        self.assertEqual(source.read_text(), '[]')

    def test_allowed_directory_links_refused_without_profile_changes(self):
        allowed = Path.home() / '.dsh/data/dsh-comfyui'
        profile = Path.home() / '.dsh/profiles/desktop'
        write_json(profile / 'cordis.patch.yml', {'fixture': True})
        write_json(profile / 'dsh-comfyui/workflows.json', [])

        def snapshot():
            result = {}
            for p in [profile, *profile.rglob('*')]:
                content = p.read_bytes() if p.is_file() else None
                info = p.stat()
                result[p.relative_to(profile)] = (content, info.st_mode, info.st_size,
                                                  info.st_mtime_ns, info.st_ino)
            return result

        for link in (allowed, allowed.parent):
            with self.subTest(link=link.name):
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(profile, target_is_directory=True)
                try:
                    before = snapshot()
                    args = argparse.Namespace(data_dir=str(allowed), ps=str(exec_file(self.root / 'ps')),
                                              harness_process='fixture')
                    with mock.patch.object(c, 'command', return_value=argparse.Namespace(stdout='')) as command, mock.patch.object(c, 'atomic_json') as atomic:
                        self.raises_code(c, 2, r.register, args)
                        command.assert_not_called()
                        atomic.assert_not_called()
                    after = snapshot()
                    self.assertEqual(after, before)
                    self.assertTrue(link.is_symlink())
                finally:
                    link.unlink()
                    if link == allowed:
                        link.parent.rmdir()

    def test_atomic_change_and_replace_failure_preserve_original(self):
        path = self.root / 'workflows.json'
        write_json(path, [])
        snapshot = path.stat(), path.read_bytes()
        path.write_text('["changed"]')
        self.raises_code(c, 5, c.atomic_json, path, [1], snapshot)
        self.assertEqual(path.read_text(), '["changed"]')
        self.assertEqual(list(self.root.glob('.h3-*')), [])
        snapshot = path.stat(), path.read_bytes()
        with mock.patch.object(c.os, 'replace', side_effect=OSError('SECRET')):
            with self.assertRaises(OSError):
                c.atomic_json(path, [1], snapshot)
        self.assertEqual(path.read_text(), '["changed"]')
        self.assertEqual(list(self.root.glob('.h3-*')), [])
