import argparse
import copy
from unittest import mock
from support import Case, load, exec_file, write_json

s = load('submit_h3')
c = s.c


class SubmitTests(Case):
    def setup_graph(self):
        graph = c.load_graph()
        ffmpeg = exec_file(self.root / 'bin/ffmpeg')
        exec_file(self.root / 'bin/ffprobe')
        graph['3']['inputs']['ffmpeg_path'] = str(ffmpeg)
        return graph

    def entry(self, graph=None):
        graph = graph or self.setup_graph()
        video = self.root / 'output/minimax_h3/ComfyUI_00001_.mp4'
        video.parent.mkdir(parents=True, exist_ok=True)
        video.write_bytes(b'fixture')
        return dict(prompt=[1, 'id', copy.deepcopy(graph)], status=dict(completed=True, status_str='success'),
                    outputs={'3': {'minimax_h3_video': [dict(filename=video.name, subfolder='minimax_h3', type='output')]}})

    def streams(self, **video):
        return dict(streams=[dict(codec_type='video', codec_name='h264', width=64, height=64, **video),
                             dict(codec_type='audio', codec_name='aac', channels=2, sample_rate='32000')])

    def test_verify_public_diff_repository_tool_paths(self):
        graph = self.setup_graph()
        entry = self.entry(graph)
        entry['prompt'][2]['2']['inputs'].update(seed=3105209621)
        registered = dict(workflow=copy.deepcopy(graph))
        def command(argv, **kwargs):
            if c.Path(argv[0]).name == 'ffprobe':
                return argparse.Namespace(stdout=c.json.dumps(self.streams()), stderr='')
            self.assertIn('-xerror', argv)
            self.assertIn('0:a:0', argv)
            return argparse.Namespace(stdout='', stderr='')
        with mock.patch.object(c, 'command', side_effect=command) as run:
            self.assertEqual(s.verify_entry(entry, graph, registered, self.root / 'output', 300), 0)
            self.assertEqual(run.call_count, 2)
            self.assertEqual(run.call_args_list[0].args[0][0], self.root / 'bin/ffprobe')
            self.assertEqual(run.call_args_list[1].args[0][0], self.root / 'bin/ffmpeg')
        self.assertIn('3105209621', self.output.getvalue())

    def test_verify_registered_and_repository_both_no_execution(self):
        graph = self.setup_graph()
        for changed in ('library_only', 'library_and_history', 'history_only'):
            entry = self.entry(graph)
            registered = dict(workflow=copy.deepcopy(graph))
            if changed in ('library_only', 'library_and_history'):
                registered['workflow']['3']['inputs']['ffmpeg_path'] = str(self.root / 'evil')
            if changed in ('history_only', 'library_and_history'):
                entry['prompt'][2]['3']['inputs']['ffmpeg_path'] = str(self.root / 'evil')
            with mock.patch.object(c, 'command') as command:
                self.raises_code(c, 8, s.verify_entry, entry, graph, registered, self.root / 'output', 300)
                command.assert_not_called()

    def test_verify_bad_library_never_fallback(self):
        graph = self.setup_graph()
        args = self.args(verify_history='id')
        path = self.root / 'data/workflows.json'
        entry = dict(id='a', name=c.NAME, workflow=graph)
        for raw in ('{bad', '{}', c.json.dumps([entry, entry])):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(raw)
            with mock.patch.object(c, 'load_graph', return_value=graph), mock.patch.object(c, 'request_json') as request, mock.patch.object(c, 'command') as command:
                self.raises_code(c, 2, s.submit, args)
                request.assert_not_called()
                command.assert_not_called()

    def test_video_missing_audio_wrong_codec_wrong_resolution(self):
        graph = self.setup_graph()
        video = c.output_video(self.entry(graph), self.root / 'output')
        values = [dict(streams=self.streams()['streams'][:1]),
                  dict(streams=[dict(codec_type='video', codec_name='hevc', width=64, height=64), self.streams()['streams'][1]]),
                  dict(streams=[dict(codec_type='video', codec_name='h264', width=32, height=64), self.streams()['streams'][1]])]
        for streams in values:
            with mock.patch.object(c, 'command', return_value=argparse.Namespace(stdout=c.json.dumps(streams), stderr='')) as command:
                self.raises_code(c, 8, c.inspect_video, video, 64, 64, graph)
                self.assertEqual(command.call_count, 1)

    def test_video_decode_failure_and_timeout(self):
        graph = self.setup_graph()
        video = c.output_video(self.entry(graph), self.root / 'output')
        probe = argparse.Namespace(stdout=c.json.dumps(self.streams()), stderr='')
        for outcome, code in ((argparse.Namespace(stdout='', stderr='error'), 8),
                              (c.H3Error(8, 'decode', 'failure', '確認'), 8),
                              (c.H3Error(7, 'decode', 'timeout', '確認'), 7)):
            with mock.patch.object(c, 'command', side_effect=[probe, outcome]):
                self.raises_code(c, code, c.inspect_video, video, 64, 64, graph)

    def test_ffprobe_missing_is_one(self):
        graph = self.setup_graph()
        (self.root / 'bin/ffprobe').unlink()
        with mock.patch.object(c, 'command') as command:
            self.raises_code(c, 1, c.inspect_video, self.root / 'v.mp4', 64, 64, graph)
            command.assert_not_called()

    def test_output_missing_invalid_and_escape(self):
        graph = self.setup_graph()
        entry = self.entry(graph)
        desc = entry['outputs']['3']['minimax_h3_video'][0]
        for change in (dict(filename='/absolute.mp4'), dict(subfolder='../outside'), dict(type='temp'), dict(filename='missing.mp4')):
            bad = copy.deepcopy(entry)
            bad['outputs']['3']['minimax_h3_video'][0].update(change)
            self.raises_code(c, 8, c.output_video, bad, self.root / 'output')
        outside = self.root / 'outside'
        outside.mkdir()
        (outside / 'v.mp4').write_bytes(b'x')
        (self.root / 'output/jump').symlink_to(outside)
        desc.update(subfolder='jump', filename='v.mp4')
        self.raises_code(c, 8, c.output_video, entry, self.root / 'output')

    def args(self, **changes):
        values = dict(comfy_url='http://127.0.0.1:8188', output_dir=str(self.root / 'output'),
                      data_dir=str(self.root / 'data'), verify_history=None, prompt="O'Reilly < 2; 日本語", width=64, height=64,
                      seconds=1.0, steps=5, seed=0, timeout=7200, http_timeout=30, poll_interval=2, command_timeout=300)
        return argparse.Namespace(**{**values, **changes})

    def test_submit_success_and_json_prompt(self):
        graph = self.setup_graph()
        entry = self.entry(graph)
        entry['prompt'][2]['2']['inputs']['prompt'] = self.args().prompt
        with mock.patch.object(c, 'load_graph', return_value=graph), mock.patch.object(c, 'request_json', side_effect=[dict(prompt_id='id'), {'id': entry}]) as request, mock.patch.object(c, 'inspect_video'):
            self.assertEqual(s.submit(self.args()), 0)
            sent = request.call_args_list[0].args[1]['prompt']
            self.assertEqual(sent['2']['inputs']['prompt'], self.args().prompt)
            self.assertEqual(sent['1'], graph['1'])
            self.assertEqual(sent['3'], graph['3'])

    def submit_with(self, graph, history, args=None, **extra):
        """Run submit() end to end with stubbed HTTP; returns (callable, inspect mock context)."""
        args = args or self.args()
        responses = [{'id': history}] if args.verify_history else [dict(prompt_id='id'), {'id': history}]
        return (mock.patch.object(c, 'load_graph', return_value=graph),
                mock.patch.object(c, 'request_json', side_effect=responses))

    def test_submit_reaches_history_output_and_video_checks(self):
        # Guards the wiring: submit() must not return before the final verification.
        graph = self.setup_graph()
        good = self.entry(graph)
        good['prompt'][2]['2']['inputs']['prompt'] = self.args().prompt
        load, request = self.submit_with(graph, good)
        with load, request, mock.patch.object(c, 'inspect_video') as inspect:
            self.assertEqual(s.submit(self.args()), 0)
            inspect.assert_called_once()
            self.assertEqual(inspect.call_args.args[1:3], (64, 64))
            self.assertEqual(inspect.call_args.args[3], graph)

        fixed_changed = copy.deepcopy(good)
        fixed_changed['prompt'][2]['3']['inputs']['crf'] = 1
        public_changed = copy.deepcopy(good)
        public_changed['prompt'][2]['2']['inputs']['seed'] = 7
        video_missing = copy.deepcopy(good)
        video_missing['outputs']['3']['minimax_h3_video'][0]['filename'] = 'missing.mp4'
        for history in (fixed_changed, public_changed, video_missing):
            load, request = self.submit_with(graph, history)
            with load, request, mock.patch.object(c, 'inspect_video') as inspect, mock.patch.object(c, 'command') as command:
                self.raises_code(c, 8, s.submit, self.args())
                inspect.assert_not_called()
                command.assert_not_called()

        load, request = self.submit_with(graph, good)
        with load, request, mock.patch.object(c, 'inspect_video', side_effect=c.H3Error(8, '動画', '不合格', '確認')):
            self.raises_code(c, 8, s.submit, self.args())

    def test_verify_history_passes_the_registered_entry_through_submit(self):
        # Guards the wiring from read_library() to the comparison inside submit().
        graph = self.setup_graph()
        history = self.entry(graph)
        args = self.args(verify_history='id')
        library = self.root / 'data/workflows.json'
        same = dict(id='a', name=c.NAME, workflow=copy.deepcopy(graph))
        write_json(library, [same])
        load, request = self.submit_with(graph, history, args)
        with load, request, mock.patch.object(c, 'inspect_video') as inspect:
            self.assertEqual(s.submit(args), 0)
            inspect.assert_called_once()

        different = copy.deepcopy(same)
        different['workflow']['1']['inputs']['memory_limit_gb'] = 1.0
        write_json(library, [different])
        load, request = self.submit_with(graph, history, args)
        with load, request, mock.patch.object(c, 'inspect_video') as inspect, mock.patch.object(c, 'command') as command:
            self.raises_code(c, 8, s.submit, args)
            inspect.assert_not_called()
            command.assert_not_called()

    def test_history_request_cut_by_the_deadline_is_a_timeout(self):
        failure = c.H3Error(6, 'HTTP', '無応答', '確認')
        with mock.patch.object(s.time, 'monotonic', side_effect=[0, 10]), mock.patch.object(c, 'request_json', side_effect=failure):
            self.raises_code(c, 7, s.wait_history, 'http://127.0.0.1:1', 'id', 5, 30, 2)
        with mock.patch.object(s.time, 'monotonic', side_effect=[0, 1]), mock.patch.object(c, 'request_json', side_effect=failure):
            self.raises_code(c, 6, s.wait_history, 'http://127.0.0.1:1', 'id', 5, 30, 2)

    def test_submit_post_rejection_node_errors(self):
        graph = self.setup_graph()
        for response in (dict(node_errors={'x': 'SECRET'}), dict(error='SECRET'), {}, []):
            with mock.patch.object(c, 'load_graph', return_value=graph), mock.patch.object(c, 'request_json', return_value=response):
                self.raises_code(c, 6, s.submit, self.args())
        self.assertNotIn('SECRET', self.output.getvalue())

    def test_history_error_and_deadline(self):
        with mock.patch.object(c, 'request_json', return_value={'id': dict(status=dict(status_str='error', completed=False))}):
            self.raises_code(c, 6, s.wait_history, 'http://127.0.0.1:1', 'id', float('inf'), 30, 2)
        with mock.patch.object(s.time, 'monotonic', return_value=10), mock.patch.object(c, 'request_json') as request:
            self.raises_code(c, 7, s.wait_history, 'http://127.0.0.1:1', 'id', 9, 30, 2)
            request.assert_not_called()

    def test_poll_caps_request_and_sleep_to_remaining(self):
        graph = self.setup_graph()
        entry = self.entry(graph)
        with mock.patch.object(s.time, 'monotonic', side_effect=[0, 1, 2, 3]), mock.patch.object(s.time, 'sleep') as sleep, mock.patch.object(c, 'request_json', side_effect=[{}, {'id': entry}]) as request:
            self.assertEqual(s.wait_history('http://127.0.0.1:1', 'id', 4, 30, 20), entry)
        self.assertEqual(request.call_args_list[0].kwargs['timeout'], 4)
        self.assertEqual(sleep.call_args.args[0], 3)
