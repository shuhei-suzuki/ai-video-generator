"""Requirement-linked mutations, isolated in tempfile copies of the implementation."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
# name, file, original, mutation, test file, intended failing test
MUTATIONS = [
    ('同意ゲート', 'scripts/download_h3_models.py', '    consent(args.accept_license)', '    pass  # mutation: consent bypass', 'test_download.py', 'test_consent_each_model_non_tty_no_transfer'),
    ('固定SHA', 'scripts/h3_common.py', "if model.get(field) != expected[field]:", "if model.get(field) != expected[field] and field != 'revision':", 'test_common.py', 'test_manifest_sha_repo_scope'),
    ('サイズ一致', 'scripts/h3_common.py', "state = '完了' if size == item['size']", "state = '完了' if size <= item['size']", 'test_download.py', 'test_conflict_each_model_precedes_consent'),
    ('取得途中', 'scripts/h3_common.py', "if name.endswith('.incomplete') and inside", "if False and name.endswith('.incomplete') and inside", 'test_download.py', 'test_size_incomplete_extra_shared_d3'),
    ('残量ゼロ', 'scripts/download_h3_models.py', "    if not pending:\n        print", "    if not pending:\n        return 5\n        print", 'test_download.py', 'test_all_complete_no_hub_no_consent_no_capacity'),
    ('容量境界', 'scripts/download_h3_models.py', 'if free < needed:', 'if free <= needed:', 'test_download.py', 'test_capacity_boundary_and_clamp'),
    ('パス包含', 'scripts/h3_common.py', 'return path.resolve().is_relative_to(root.resolve())', 'return True  # mutation: containment bypass', 'test_submit.py', 'test_output_missing_invalid_and_escape'),
    ('ループバック', 'scripts/h3_common.py', "or not address.is_loopback or", "or False or", 'test_common.py', 'test_local_url_loopback'),
    ('診断集約', 'scripts/check_env.py', "all(state == 'PASS' for state, _, _ in results)", "any(state == 'PASS' for state, _, _ in results)", 'test_check_env.py', 'test_aggregate_any_failure_unknown'),
    ('キー非表示', 'scripts/check_env.py', "            hits.append(bool(value)", "            print(value)  # mutation: leaks target value\n            hits.append(bool(value)", 'test_check_env.py', 'test_target_key_never_printed'),
    ('公開6項目', 'scripts/h3_common.py', "    if {p.get('name') for p in value} != set(PUBLIC) or {p.get('inputKey') for p in value} != set(PUBLIC):", "    if False:  # mutation: public set bypass", 'test_common.py', 'test_parameters_exact_six_no_max'),
    ('同名同内容', 'scripts/register_dsh_workflow.py', '        if changes:', '        if True:  # mutation: always conflict', 'test_register.py', 'test_same_content_different_ids_byte_unchanged'),
    ('同名別内容', 'scripts/register_dsh_workflow.py', '        if changes:', '        if False:  # mutation: conflict bypass', 'test_register.py', 'test_different_workflow_and_parameter_nonchange'),
    ('両ストリーム', 'scripts/h3_common.py', "audio = next(s for s in streams if s.get('codec_type') == 'audio')", "audio = {'codec_name': 'aac'}  # mutation: fabricate audio", 'test_submit.py', 'test_video_missing_audio_wrong_codec_wrong_resolution'),
    ('解像度', 'scripts/h3_common.py', "if video.get('width') != width or video.get('height') != height:", "if False:  # mutation: resolution bypass", 'test_submit.py', 'test_video_missing_audio_wrong_codec_wrong_resolution'),
    ('全デコード', 'scripts/h3_common.py', 'if decoded.stderr.strip():', 'if False:  # mutation: decoder errors bypass', 'test_submit.py', 'test_video_decode_failure_and_timeout'),
    ('D-4登録項目', 'scripts/check_env.py', '    if registered is not None:', '    if False:  # mutation: registration ignored', 'test_check_env.py', 'test_d4_repository_and_registration_both_checked'),
    ('D-4不正ライブラリ', 'scripts/check_env.py', "    _, registered = c.read_library(data_dir / 'workflows.json')", "    try:\n        _, registered = c.read_library(data_dir / 'workflows.json')\n    except c.H3Error:\n        registered = None", 'test_check_env.py', 'test_d4_bad_library_fails_not_unregistered'),
    ('verify登録項目', 'scripts/submit_h3.py', '    if registered is not None:', '    if False:  # mutation: registration ignored', 'test_submit.py', 'test_verify_registered_and_repository_both_no_execution'),
    ('verify不正ライブラリ', 'scripts/submit_h3.py', "        _, registered = c.read_library(p['data_dir'] / 'workflows.json')", "        try:\n            _, registered = c.read_library(p['data_dir'] / 'workflows.json')\n        except c.H3Error:\n            registered = None", 'test_submit.py', 'test_verify_bad_library_never_fallback'),
]


class MutationTests(unittest.TestCase):
    def test_requirement_mutations_detected_and_copies_removed(self):
        paths = []
        for name, file, before, after, testfile, testname in MUTATIONS:
            with self.subTest(mutation=name):
                with tempfile.TemporaryDirectory(prefix='h3-mutation-') as temporary:
                    root = Path(temporary)
                    paths.append(root)
                    for directory in ('scripts', 'tools', 'config', 'workflows', 'tests'):
                        shutil.copytree(ROOT / directory, root / directory,
                                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
                    target = root / file
                    text = target.read_text(encoding='utf-8')
                    self.assertEqual(text.count(before), 1, (name, 'ambiguous mutation'))
                    target.write_text(text.replace(before, after, 1), encoding='utf-8')
                    # Reject syntax-invalid mutants BEFORE running any test.
                    compile(target.read_text(), file, 'exec')
                    result = subprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover',
                                             '-s', 'tests', '-p', testfile, '-k', testname, '-v'],
                                            cwd=root, capture_output=True, text=True, timeout=30, shell=False)
                    combined = result.stdout + result.stderr
                    self.assertNotIn('skipped', combined)
                    self.assertNotEqual(result.returncode, 0, (name, combined))
                    self.assertIn(testname, combined)
                    self.assertIn('FAILED (', combined)
                    self.assertNotIn('SyntaxError', combined)
                    self.assertNotIn('no network in tests', combined)
                    self.assertEqual((ROOT / file).read_text(encoding='utf-8'), text,
                                     (name, 'original implementation changed'))
        self.assertTrue(all(not path.exists() for path in paths))
