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
    ('パス包含', 'scripts/h3_common.py', 'return entity_relative(path, root) is not None', 'return True  # mutation: containment bypass', 'test_submit.py', 'test_output_missing_invalid_and_escape'),
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
    ('実体を文字列比較へ戻す', 'scripts/h3_common.py', 'if os.path.samestat(info, rootstat):', 'if cursor == anchor:', 'test_review_fixes.py', 'test_mount_alias_identity_all_writers_preserve_original'),
    ('書込保護を外す', 'scripts/h3_common.py', 'if inside(path, home):', 'if False:', 'test_review_fixes.py', 'test_symlink_alias_all_writers_preserve_original'),
    ('未存在要素のcasefoldを外す', 'scripts/h3_common.py', 'tuple(p.casefold() for p in parts[:len(missing)]) == tuple(p.casefold() for p in missing)', 'tuple(parts[:len(missing)]) == missing', 'test_review_fixes.py', 'test_allowed_paths_missing_components_and_existing_case_distinction'),
    ('既存実体の大小を文字列許可', 'scripts/h3_common.py', 'if not library or not any(entity_relative(path, p) == () for p in (allowed, allowed / \'workflows.json\')):', 'if not library:', 'test_review_fixes.py', 'test_allowed_paths_missing_components_and_existing_case_distinction'),
    ('command標準入力を継承', 'scripts/h3_common.py', 'stdin=subprocess.DEVNULL', 'stdin=None', 'test_review_fixes.py', 'test_all_child_input_is_closed'),
    ('listeners標準入力を継承', 'scripts/check_env.py', 'stdin=c.subprocess.DEVNULL', 'stdin=None', 'test_review_fixes.py', 'test_all_child_input_is_closed'),
    ('git対話を許可', 'scripts/h3_common.py', "GIT_TERMINAL_PROMPT='0'", "GIT_TERMINAL_PROMPT='1'", 'test_review_fixes.py', 'test_all_child_input_is_closed'),
    ('ffmpeg対話を許可', 'scripts/h3_common.py', "[ffmpeg, '-nostdin',", '[ffmpeg,', 'test_review_fixes.py', 'test_decode_disables_stdin'),
    ('完了ファイルを常時表示', 'scripts/h3_common.py', "if verbose or state != '完了':", 'if True:', 'test_review_fixes.py', 'test_model_summary_verbose_and_pass_remedies'),
    ('PASSにも対処を表示', 'scripts/check_env.py', "suffix = '' if state == 'PASS' else f'; 対処: {remedy}'", "suffix = f'; 対処: {remedy}'", 'test_review_fixes.py', 'test_model_summary_verbose_and_pass_remedies'),
    ('容量を毎回表示', 'scripts/download_h3_models.py', 'if current != previous:', 'if True:', 'test_review_fixes.py', 'test_capacity_only_prints_changes_but_always_checks'),
    ('取得進捗を外す', 'scripts/download_h3_models.py', '        print(f"取得 {index}/{len(pending)}: {m[\'local_dir\']}/{f[\'path\']}（{f[\'size\']} bytes）", flush=True)', '        pass', 'test_download.py', 'test_acquire_missing_only_revision_token_recheck'),
    ('Comfy構成検査を外す', 'scripts/install_h3_node.py', "if not (comfy / 'custom_nodes').is_dir() or not (comfy / 'main.py').is_file():", 'if False:', 'test_review_fixes.py', 'test_missing_comfy_structure_no_creation_or_commands'),
    ('pip事前checkを外す', 'scripts/install_h3_node.py', "    try:\n        c.command(pip + ['check'], args.command_timeout, 'pip')", '    try:\n        pass', 'test_review_fixes.py', 'test_precheck_and_wheel_failure_are_nonchanging'),
    ('wheel限定を外す', 'scripts/install_h3_node.py', "'install', '--only-binary', ':all:',", "'install',", 'test_review_fixes.py', 'test_install_failure_stage_changed_and_no_blind_retry'),
    ('計画失敗を6へ戻す', 'scripts/install_h3_node.py', "c.fail(1, 'pip計画', 'この環境向けの wheel", "c.fail(6, 'pip計画', 'この環境向けの wheel", 'test_review_fixes.py', 'test_precheck_and_wheel_failure_are_nonchanging'),
    ('変更状態を未変更へ戻す', 'scripts/install_h3_node.py', "progress.update(stage='依存導入', changed=True)", "progress.update(stage='依存導入', changed=False)", 'test_review_fixes.py', 'test_install_failure_stage_changed_and_no_blind_retry'),
    ('失敗工程を消す', 'scripts/install_h3_node.py', "'install ' + progress['stage']", "'install'", 'test_review_fixes.py', 'test_failure_reports_acquisition_postcheck_placement_and_link'),
    ('登録既定値をスモークへ戻す', 'scripts/h3_common.py', "dict(graph['2']['inputs'], width=768, height=448, duration_seconds=5.0, steps=9, seed=0)", "graph['2']['inputs']", 'test_review_fixes.py', 'test_practical_defaults_graph_unchanged_and_agent_description'),
    ('説明文の期限を欠落', 'scripts/register_dsh_workflow.py', '1800000 for 5 seconds', '900000 for 5 seconds', 'test_review_fixes.py', 'test_practical_defaults_graph_unchanged_and_agent_description'),
    ('登録説明文の配線を外す', 'scripts/register_dsh_workflow.py', 'description=DESCRIPTION,', "description='obsolete',", 'test_review_fixes.py', 'test_practical_defaults_graph_unchanged_and_agent_description'),
    ('description比較を外す', 'scripts/register_dsh_workflow.py', "        changes.extend(differences(match.get('description'), DESCRIPTION, 'description'))", '        pass', 'test_review_fixes.py', 'test_description_tags_and_terminal_control_characters'),
    ('tags比較を外す', 'scripts/register_dsh_workflow.py', "        changes.extend(differences(match.get('tags'), TAGS, 'tags'))", '        pass', 'test_review_fixes.py', 'test_description_tags_and_terminal_control_characters'),
    ('既存idを未加工表示', 'scripts/register_dsh_workflow.py', "c.json.dumps(match['id'], ensure_ascii=True)", "match['id']", 'test_review_fixes.py', 'test_description_tags_and_terminal_control_characters'),
    ('既存キー名を未加工表示', 'scripts/register_dsh_workflow.py', 'c.json.dumps(changes, ensure_ascii=True)', "', '.join(changes)", 'test_review_fixes.py', 'test_description_tags_and_terminal_control_characters'),
    ('履歴不在の配線を外す', 'scripts/submit_h3.py', 'require_present=bool(args.verify_history)', 'require_present=True if False else False', 'test_review_fixes.py', 'test_missing_verify_id_fails_immediately'),
    ('公開型不正を固定入力不一致表示', 'scripts/submit_h3.py', '履歴の公開値の型が不正', 'ノード構成・固定入力が不一致', 'test_review_fixes.py', 'test_history_public_type_message_and_comparison_targets'),
    ('照合相手を非表示', 'scripts/submit_h3.py', "print('履歴照合 PASS: ノード構成・固定入力 / リポジトリのワークフロー / ' + other)", "print('履歴照合 PASS: ノード構成・固定入力')", 'test_review_fixes.py', 'test_history_public_type_message_and_comparison_targets'),
    ('download verbose配線を外す', 'scripts/download_h3_models.py', 'c.model_summary(rows, args.verbose)', 'c.model_summary(rows, False)', 'test_review_fixes.py', 'test_verbose_reaches_all_summary_consumers'),
    ('check verbose配線を外す', 'scripts/check_env.py', "c.model_summary(rows, p.get('verbose', False))", 'c.model_summary(rows, False)', 'test_review_fixes.py', 'test_verbose_reaches_all_summary_consumers'),
    ('make verbose配線を外す', 'tools/make_manifest.py', 'c.model_summary(rows, args.verbose)', 'c.model_summary(rows, False)', 'test_review_fixes.py', 'test_verbose_reaches_all_summary_consumers'),
    ('診断verbose引数を捨てる', 'scripts/check_env.py', "p['verbose'] = args.verbose", "p['verbose'] = False", 'test_check_env.py', 'test_full_diagnostics_api_faults_individual'),
    ('追加cacheを必須件数へ混入', 'scripts/h3_common.py', '{len(model["files"])} 件', '{len(group)} 件', 'test_review_fixes.py', 'test_model_summary_verbose_and_pass_remedies'),
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
                    argv = [sys.executable, '-B', '-m', 'unittest', 'discover',
                            '-s', 'tests', '-p', testfile, '-k', testname, '-v']
                    control = subprocess.run(argv, cwd=root, capture_output=True, text=True,
                                             timeout=30, shell=False, stdin=subprocess.DEVNULL)
                    self.assertEqual(control.returncode, 0, (name, control.stdout + control.stderr))
                    target.write_text(text.replace(before, after, 1), encoding='utf-8')
                    # Reject syntax-invalid mutants BEFORE running any test.
                    compile(target.read_text(), file, 'exec')
                    result = subprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover',
                                             '-s', 'tests', '-p', testfile, '-k', testname, '-v'],
                                            cwd=root, capture_output=True, text=True, timeout=30, shell=False, stdin=subprocess.DEVNULL)
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
