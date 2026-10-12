# Mac で MiniMax H3 の動画・音声を生成する

macOS 26 / Apple Silicon M5 Max / 128GB を基準に、Comfy Desktop と MiniMax H3 MLX でローカルの MP4 を生成し、Ollama の Qwen を使う DeepSeek Harness のチャットからも同じワークフローを実行するための資料と Python ツールです。モデル重みは収録しません。

実機結果とスクリプトの実行範囲は[検証記録](doc/verification/issue-1-verification.md)の開始状態・対象コミット・証跡・未確認範囲を参照してください。2026-10-12 の記録には既存環境での CLI 実行と、空の一時配置先への取得・登録が含まれます。対象外の構成や生成条件の成功を保証しません。

## 対象構成とライセンス

確認日 **2026-10-12**。条件の要約は非正本です。取得する配布物の原文を優先し、本人が確認してください。「未確認」は配布条件の確認完了を意味しません。基本モデルの `LICENSE`、INT8 の `LICENSE`、Turbo の `README.md` は、固定リビジョンの URL が応答することを 2026-10-12 に確認しました（内容の要約は非正本）。

| 対象 | 固定版 / リビジョン | ライセンス原文・配布元と確認範囲 |
| --- | --- | --- |
| Comfy Desktop | 1.1.6 arm64（ComfyUI 0.39.2 / Python 3.13.12 / Manager V4.2.2） | [Desktop 配布元](https://www.comfy.org/download)、[LICENSE](https://github.com/Comfy-Org/desktop/blob/main/LICENSE)・配布条件の詳細は未確認 |
| H3 カスタムノード | `ab1756d571ebb14fed3168354dae42966a04348b` | [固定コミットの Apache-2.0 原文](https://github.com/Argus-AiTeam/ComfyUI-MiniMax-H3-MLX/blob/ab1756d571ebb14fed3168354dae42966a04348b/LICENSE) |
| 基本モデル `MiniMaxAI/MiniMax-H3` | `42ed227ee7df40d41602854ae760620d6eb651fe` | [MiniMax H3 Community License](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/42ed227ee7df40d41602854ae760620d6eb651fe/LICENSE) |
| INT8 `water1234/MiniMax-H3-MLX-Argus-Calibrated-INT8` | `70505b09c80e298e684d798d8e0f946937dcfad4` | [同梱 LICENSE](https://huggingface.co/water1234/MiniMax-H3-MLX-Argus-Calibrated-INT8/blob/70505b09c80e298e684d798d8e0f946937dcfad4/LICENSE)（HF 表記 other）。H3 派生物として H3 条件が及ぶ前提 |
| Turbo `water1234/MiniMax-H3-Turbo-v4-step600-EMA-MLX` | `9771f9c606a50671bb94ee57191461602f02d1fc` | [固定モデルカード](https://huggingface.co/water1234/MiniMax-H3-Turbo-v4-step600-EMA-MLX/blob/9771f9c606a50671bb94ee57191461602f02d1fc/README.md)の apache-2.0 表記、[Apache-2.0 原文](https://www.apache.org/licenses/LICENSE-2.0)。同梱 LICENSE は一覧に無い。H3 派生物として H3 条件が及ぶ前提 |
| Ollama 本体 | 0.33.3 | [公式配布](https://ollama.com/download)、[原文](https://github.com/ollama/ollama/blob/v0.33.3/LICENSE)・配布条件の詳細は未確認 |
| Qwen | `qwen3.8:27b-mlx` | [モデル配布元](https://ollama.com/library/qwen3.8)、配布モデルの `ollama show qwen3.8:27b-mlx --license` で原文を確認（Apache-2.0） |
| DeepSeek Harness Desktop | 0.2.0-rc.2 | [公式配布の条件](https://www.deepseek.com/harness)と dmg の同梱 LICENSE / 利用規約を参照。配布条件の詳細は未確認 |
| dsh-comfyui | npm 0.5.4 | [0.5.4 配布物の MIT 原文](https://unpkg.com/dsh-comfyui@0.5.4/LICENSE)、[配布元](https://www.npmjs.com/package/dsh-comfyui/v/0.5.4) |
| ffmpeg / ffprobe | Homebrew、対象機 ffmpeg 7.1.1 | [原文・構成による条件](https://ffmpeg.org/legal.html)、[Homebrew formula](https://formulae.brew.sh/formula/ffmpeg)。導入配布物の条件は未確認。ffprobe の版は未確認 |

H3 は **米国・EU・英国・韓国での利用が対象外**、**年商2,000万USD超は別途許諾**が必要です。派生2モデルにも H3 の条件が及ぶ前提で、3モデルすべての取得前に同意を求めます。公開取得できることは利用許諾を意味しません。

## 容量・配置

2026-10-12 の[必須ファイル一覧](config/h3_models.manifest.json)と[実測記録](doc/verification/issue-1-verification.md#容量と導入)に基づきます。基本モデルはリポジトリ全体ではなく `FL2VA/model_index.json` と tokenizer / processor / text_encoder / video_vae / audio_vae の部分取得です。

| 対象 | 件数 | バイト数 | 概算 GB |
| --- | --- | --- | --- |
| 基本（指定コンポーネント） | 66 | 77,770,657,762 | 77.77 |
| INT8 | 13 | 37,797,145,373 | 37.80 |
| Turbo | 57 | 1,559,967,577 | 1.56 |
| 合計 | 136 | 117,127,770,712 | 117.13（約109 GiB） |

Qwen は約18GB、Desktop のインスタンスは数GBです。導入開始時の **150GB は暫定の目安**で容量保証ではありません。キャッシュ、動画、OS の余裕も別に確保してください。取得スクリプトは Qwen を含めず未取得分 R のみから `R + max(1 GiB, ceil(R×5%))` を算出し、配置先ボリュームの空きを検査します。

```text
~/ComfyUI-Installs/ComfyUI/            インスタンス
  ComfyUI/                             本体 <comfy-root>
    .venv/                             仮想環境（本体の直下）
    custom_nodes/ComfyUI-MiniMax-H3-MLX/
    models/minimax_h3/                  共有先と同じ実体への入口
~/ComfyUI-Shared/models/minimax_h3/     3モデルの配置先
~/ComfyUI-Shared/output/minimax_h3/     MP4
~/.dsh/profiles/desktop/cordis.patch.yml  本人が追記する設定
~/.dsh/.env                            非秘密ダミー値のキー参照
~/.dsh/data/dsh-comfyui/workflows.json   登録ライブラリ（profile の外）
```

既定と違う場合は CLI で指定します。`--instance` → `<instance>/ComfyUI` → `<comfy-root>/.venv` と導出し、明示値を優先します。別インスタンスを自動探索しません。利用者のシェルや Harness profile はスクリプトで書き換えません。

## 自動化の境界

| 対象 | スクリプトで取得・変更 | 手作業の手順書 | 診断のみ |
| --- | --- | --- | --- |
| Comfy Desktop | — | 公式導入・初回 GUI 起動 | API / 待受 |
| Ollama 本体 | — | 公式導入・起動 | API / 待受 |
| Harness 本体 | — | 公式導入・初回 GUI 起動 | profile / キー / 待受 |
| ffmpeg 本体 | — | Homebrew 導入 | 固定絶対パスの実行可否 |
| カスタムノード | 固定コミット・新規依存・venv bin 補助リンク・`<comfy-root>/models/minimax_h3` へのリンク作成・共有モデルディレクトリの作成（未存在時）。既存の別実体があれば5で停止 | ComfyUI の停止・再起動 | 4ノード |
| H3 系3モデル | 本人同意後、未取得ファイルだけ | 原文確認・本人同意 | 必須ファイル・途中データ |
| Harness 設定例 | — | 既存項目を保持した追記・再適用 | desktop の実使用設定 |
| Qwen | — | 手動 pull | 存在 |
| dsh-comfyui | — | 互換性例外の承諾・手動導入 | 0.5.4 導入済み |
| ワークフロー登録 | ライブラリ1項目の追加 | 競合時のパネル削除 | 履歴と登録/固定グラフ照合 |

## 導入手順（手作業を含む）

1. 利用条件・対象構成・空き容量を確認する。Comfy Desktop 1.1.6 arm64 と Harness Desktop 0.2.0-rc.2 の公式 dmg を取得する。macOS の署名・公証（Notarized Developer ID）を確認して導入する。拒否を無効化して起動しない。Ollama 0.33.3 は公式配布から導入する。
2. Comfy Desktop を **初回 GUI 起動**し、インスタンスのセットアップを完了する。本体・仮想環境・共有モデル・出力の実配置を確認する。ComfyUI を `127.0.0.1:8188`、Ollama を `127.0.0.1:11434` だけで起動する。Harness も初回 GUI 起動で desktop profile を用意する。Harness のポートは動的であり19387に固定しない。
3. Homebrew を公式手順で導入済みにして、本人が `brew install ffmpeg` を実行する。`/opt/homebrew/bin/ffmpeg` と同じ場所の ffprobe を確認する。GUI 起動の ComfyUI は Homebrew を PATH に含まないことがあるため、[ワークフロー](workflows/minimax_h3_t2v_api.json)の Save 固定入力を使う。別配置なら **このファイルの ffmpeg_path だけを本人が修正**し、後で再登録する。Cellar の版番号付きパスを埋め込まない。
4. ComfyUI を停止して固定ノードを導入する。`<comfy-root>/custom_nodes` と `main.py` が無ければ何も作らず1で停止するので、初回 GUI 起動と `--comfy-root` を確認する。導入前の `pip check` が不合格なら既存環境の不整合を先に解消する（非変更5）。導入は既存配布物の入れ替え計画を同版でも拒否する。dry-run と実導入は `--only-binary :all:` / `--isolated` / 明示 PyPI / 子設定隔離を使い、ソース配布物をビルドしない。この環境向けの wheel が無ければ計画時に非変更1で停止する。既存 Git・pip 設定の接続先は使わない。共有モデルディレクトリの作成（未存在時）と `<comfy-root>/models/minimax_h3` へのリンク作成も行う。既存のリンクは同じ実体なら保持し、既存の別実体があれば5で停止する。ノード Registry は使わない。

入れ替え検出は配布名に基づくため、別名の配布物が同じファイルを提供する衝突までは検出しない。install の失敗表示は工程（事前検査 / 取得 / 計画 / 依存導入 / 事後検査 / 配置 / リンク）、仮想環境の変更状態、再実行の可否を示す。依存導入開始後は途中変更の可能性があるため、そのまま再実行せず本人が pip check・配布物差分・配置を確認する。

```sh
~/ComfyUI-Installs/ComfyUI/ComfyUI/.venv/bin/python -I scripts/install_h3_node.py
```

5. 原文を読んだ **本人**がモデルを取得する。`--accept-license` はライセンスを読んだ本人だけが付ける。エージェントに取得スクリプトを実行させない。フラグを省くと TTY で `yes` を求める。非TTY・EOF・拒否では取得しない。完了済みなら同意・容量要求・hub 読込なしで0。途中・不一致は自動 resume / repair / force せず本人が退避する。一覧外の通常ファイルは保持する。並列取得しない。

```sh
~/ComfyUI-Installs/ComfyUI/ComfyUI/.venv/bin/python -I scripts/download_h3_models.py
# 原文を読んだ本人が端末で yes と入力する。部分選択も同様
~/ComfyUI-Installs/ComfyUI/ComfyUI/.venv/bin/python -I scripts/download_h3_models.py --models turbo --models-dir ~/ComfyUI-Shared/models/minimax_h3
```

原文を読んだ本人が、非対話で実行したいときの変形だけに `--accept-license` を使います。

```sh
~/ComfyUI-Installs/ComfyUI/ComfyUI/.venv/bin/python -I scripts/download_h3_models.py --accept-license
```

モデル状態はモデルごとの「完了 N / 全 M 件」と未完了ファイルだけを表示します。全件は download / check_env / make_manifest の `--verbose` で表示できます。取得中は1ファイル1行の進捗、容量は開始時と値が変わったときに表示します（容量検査自体は毎回行います）。

ComfyUI venv の既存 huggingface_hub>=1.0 が必要なのは取得時だけです（対象機1.30.0）。`token=False`、固定 endpoint/revision と標準転送を使い、暗黙のトークンを送らない設定です。存在・サイズ照合は同サイズ改変の暗号学的な完全性保証ではありません。

6. 本人が `ollama pull qwen3.8:27b-mlx` を実行する。Harness を終了して [YAML 例](config/harness/cordis.patch.example.yml)の `llm-pi-ai` の providers.ollama と `agent-default-model` を `~/.dsh/profiles/desktop/cordis.patch.yml` の **既存項目を保持して手動追記**する。同じ id を重複させない。baseURL は `/v1`、API は `openai-completions`、contextWindow=65536、maxTokens=8192。`~/.dsh/.env` に [ダミー例](config/harness/dsh-env.example)の対象キーだけを手動追記する。Ollama 自体はキーを無視するが Harness はキー参照の解決を要求する。Harness は実行中に YAML を再保存するため再適用も上書きコピーしない。
7. プラグインの互換性例外を本人が判断する。0.5.4 は 0.2.0-rc.2 に対し次の拒否になる。上流の未マージ修正を解消済みとは扱わない。async は失敗しうるため本資料では未検証とし同期を標準にする。

```text
installation rejected: Plugin dsh-comfyui@0.5.4 is incompatible with dsh 0.2.0-rc.2: peerDependencies ...
```

例外は通常の互換性検査を緩める操作です。**対象版とリスクを読んだ本人の明示承諾後だけ**、公式の完全一致バージョン例外を手で登録して導入します。スクリプトは承諾を代行しません。

```sh
dsh plugin --profile desktop allow-version dsh-comfyui@0.5.4 --dsh-version 0.2.0-rc.2 --accept-risk
dsh plugin --profile desktop add dsh-comfyui@0.5.4
```

8. Harness を終了した状態でライブラリへ登録する。起動中は警告して続行するが同時更新は保証しない。登録先は profile の外。既存同名の workflow 全体・parameters（parameter id 除外）・description・tags が今回登録する内容と一致すればバイト不変0、異なれば原本保持5。競合は Harness の ComfyUI パネルで既存項目を削除してから登録し直す。

ライブラリの既定値は prompt がワークフローの値、768×448・5秒・steps=9・seed=0（random）です。保存する workflow はリポジトリのグラフそのままで、グラフと直接 submit の既定値は64×64・1秒・steps=5のスモーク条件です。「同じワークフロー」は公開6項目を除いた固定入力の一致で判定します。description は英語で実行ツール・同期モード・条件・所要時間・期限・保存先をエージェントへ案内します。

```sh
~/ComfyUI-Installs/ComfyUI/ComfyUI/.venv/bin/python -I scripts/register_dsh_workflow.py
```

9. ComfyUI / Ollama / Harness Desktop を起動し、Harness の ComfyUI 接続先を `http://127.0.0.1:8188` に設定する。Harness 再起動でプラグインを読み込む。診断は全項目を読み取りだけで検査する。check_env は既存 PyYAML が必要（対象機6.0.3）。

```sh
~/ComfyUI-Installs/ComfyUI/ComfyUI/.venv/bin/python -I scripts/check_env.py
# 別ポート・配置の指定例
~/ComfyUI-Installs/ComfyUI/ComfyUI/.venv/bin/python -I scripts/check_env.py --comfy-url http://127.0.0.1:8188 --instance ~/ComfyUI-Installs/ComfyUI --models-dir ~/ComfyUI-Shared/models/minimax_h3
```

## 直接生成とチャットでの使い方

実行はリポジトリ直下で行います。`--help` は各CLIの引数と既定値を表示します。共通モジュールは明示ロードし、PYTHONPATH に依存しません。モデル・ffmpeg・保存先 prefix の CLI 上書きは設けません。

```sh
# 固定スモーク: 64×64 / 1秒 / steps=5 / seed=0、シーンと音の既定プロンプト
~/ComfyUI-Installs/ComfyUI/ComfyUI/.venv/bin/python -I scripts/submit_h3.py
# 直接生成の実機確認条件（プロンプトは例。実測時の原文は未提供）
~/ComfyUI-Installs/ComfyUI/ComfyUI/.venv/bin/python -I scripts/submit_h3.py --prompt 'A red panda in a misty bamboo forest, with rustling bamboo and footsteps' --width 768 --height 448 --seconds 5 --steps 9 --seed 42
# チャット実行の prompt_id を同じ ComfyUI 起動中に照合（新規投入なし）
~/ComfyUI-Installs/ComfyUI/ComfyUI/.venv/bin/python -I scripts/submit_h3.py --verify-history PROMPT_ID
# 一覧の再生成は保守用。通常の取得・診断では実行しない（重みは取得しない）
~/ComfyUI-Installs/ComfyUI/ComfyUI/.venv/bin/python -I tools/make_manifest.py --output config/h3_models.manifest.json --compare-dir ~/ComfyUI-Shared/models/minimax_h3
```

プロンプトは非空、幅・高さは正の32倍数、秒数は正の有限数、steps は2以上の整数、seed は非負整数です。上限は設けませんが大きい値は時間・メモリ・容量を増やします。生成全体の既定期限は **7200秒**、HTTP は30秒、poll は2秒、動画検査各300秒（`--timeout` / `--http-timeout` / `--poll-interval` / `--command-timeout`）。期限超過でサーバーの生成を止めたり再投入したりしません。

チャットの指示例（実機成功条件。スモークの英語プロンプトはセッション記録の値、長い2条件の英語プロンプトは例）：

> 登録ワークフロー minimax-h3-t2v をライブラリから取得し、その id と parameters を comfyui_workflow action=run に渡して同期実行してください。prompt は「A golden retriever puppy running on a sunny beach, waves crashing softly」、width=64、height=64、duration_seconds=1、steps=5。mode=sync、timeout_ms=900000。同時に1本だけ、モデルパス・ffmpeg_path は変更せず、完了後に prompt_id と保存先を示してください。

> minimax-h3-t2v のライブラリ id と parameters を comfyui_workflow action=run に渡して mode=sync で生成してください。prompt は「A red panda in a misty bamboo forest, with rustling bamboo and footsteps」、width=768、height=448、duration_seconds=5、steps=9。タイムアウトは30分（timeout_ms は1800000）で。同時に1本だけ、モデルパス・ffmpeg_path は変更せず、prompt_id と保存先を示してください。

> minimax-h3-t2v のライブラリ id と parameters を comfyui_workflow action=run に渡して mode=sync で生成してください。prompt は「A waterfall in a green forest, rushing water and birds singing」、width=448、height=768、duration_seconds=15、steps=9。タイムアウトは 70 分（timeout_ms は 4200000）で。同時に1本だけ、モデルパス・ffmpeg_path は変更せず、prompt_id と保存先を示してください。

公開項目は prompt / width / height / duration_seconds / steps / seed の6つだけです。プロンプトは英語で場面と音を書き、width / height は32の倍数、検証済みサイズは768×448（横）と448×768（縦）、秒数は15までを運用目安にします。保存先は ComfyUI の出力ディレクトリの `minimax_h3/` です。seed 省略はプラグインでランダム化します。検証した呼出しは `comfyui_workflow`、`action: run`、ライブラリ id、parameters の5項目、`mode: sync`、`timeout_ms: 900000` です。**既定の同期チャット期限は15分**で、長い動画はチャット側が先に終了しうる一方 ComfyUI は生成を継続します。長い生成には5秒なら1800000、15秒なら4200000を明示し、再投入せず出力ディレクトリまたは実行履歴で完了を確認してください。async とリポジトリ版の登録項目によるチャット生成は未検証です（理由は検証記録）。

verify は履歴を登録項目とリポジトリの両方へ直接照合し、照合相手（リポジトリのワークフロー・登録 id または登録項目なし）を表示します。履歴に ID が無ければ待たずに2です（ComfyUI の再起動で履歴は消えます）。履歴の公開値の型が不正ならその原因を表示して8です。構成・固定入力が片方でも異なれば外部コマンドを起動せず8です。公開6項目は履歴値を表示し、値差だけは不合格にしません。検査実行物は常にリポジトリの Save 固定入力の ffmpeg と同じ場所の ffprobe です。Save 出力の filename/subfolder/type から通常の MP4 を解決し、H.264 映像・AAC 音声・要求解像度・エラー無しの全フレームデコードを確認します。stdout の文字列だけは保存先と見なしません。`open` やファイルマネージャーから本人が MP4 を再生してください。

## 生成時間とメモリの指針

2026-10-12 の対象機で生成を伴う実行の目安です。同じ入力の再投入はキャッシュで短くなることがあります。秒数指定と実フレーム数の一致は合否条件にしません。

| 条件 | 結果・生成時間 | 動画 |
| --- | --- | --- |
| 直接 64×64 / 1秒 / steps=5 / seed=0 | 成功・約52秒（約1分） | H.264 24fps 39フレーム / AAC stereo 32kHz / 全デコード成功 |
| 直接 768×448 / 5秒 / steps=9 / seed=42 | 成功・845秒（約14分） | H.264 124フレーム / AAC stereo / 全デコード成功 |
| チャット同期スモーク | 成功・61秒、seed=3105209621 | H.264 64×64 39フレーム / AAC stereo / 全デコード成功 |
| チャット 448×768 / 15秒 / steps=9 | ComfyUI 側完了・48分（長時間） | H.264 361フレーム / AAC stereo / 全デコード成功 |

INT8 Transformer 約38GB、テキストエンコーダ約67GBはストリーミングで読みます。Qwen の実測は約20〜21GB、Ollama のコンテキスト長 **262144 は当該機の既定値**で他機体への推奨値ではありません。Harness の定義は **65536**です。チャット前後のシステム空き率40〜60%、15秒生成中41〜44%という観測は無条件の併用保証ではありません。

まず同時生成1件から確認し、文脈を必要な長さまで抑え、使わないモデルを解放し、Qwen の応答と生成の同時実行を減らしてください。メモリ圧迫・swap 増加・応答停止・1ステップの延伸があれば処理を増やさずモデル解放や文脈削減を行います。直接5秒生成では1ステップ約60秒、Qwen と GPU 共用した区間は約100秒でした。

## トラブルシュート

PASS 行は `D-n PASS: 原因`、FAIL / UNKNOWN 行は `D-n 状態: 原因; 対処`。UNKNOWN も全体終了1です。診断は修復しません。

| 項目・原因 | 本人が行う対処 |
| --- | --- |
| D-1 API 未起動・不正応答 | ComfyUI 起動、URL・ポートを確認 |
| D-2 各ノード欠落 | 固定ノードを導入し再起動。ModelLoader / Generate / ResultToComfyUI / SaveVideo の4つを確認 |
| D-3 必須欠落・サイズ不一致・取得途中・入口相違 | 不足のみ取得。異常ファイルや cache の `.incomplete` は本人が退避。入口を検査した共有先と同じ実体にする。余分な通常ファイルは保持 |
| D-4 相対パス・ffmpeg 不在/実行不可・登録との値相違 | ワークフローの絶対パスを修正、実行権限とリンク先の通常ファイルを確認。競合はパネルで削除再登録。不正 JSON / 非リスト / 対象名重複も FAIL。ffprobe の表示は補足で、D-4 合否は ffmpeg 条件 |
| D-5 Ollama 無応答・Qwen 不在 | Ollama 起動、手動 pull |
| D-6 profile 欠落・構造不正/重複/不透明・キー未解決 | 指定 desktop profile の例を既存項目を保持して追記。対象キーのダミー値を .env に追記。別 profile やプロセス環境で補わない。全値は非表示 |
| D-7 未導入・別版 | 指定 profile の dsh-comfyui 0.5.4 を手動導入。互換性拒否は上記の本人承諾手順 |
| D-8 ComfyUI/Ollama 外部・混在待受 / 持ち主確認不能 | URL ポート所有者と同グループの子の全 TCP 待受をループバックにする。ps/lsof の権限・起動を確認 |
| D-9 Harness 未起動・待受無し・解析不能・外部待受 | 起動後再診断。完全プロセス名・子・複数一致の全 TCP 待受を確認。UDP は未確認 |
| 容量不足（4） | 配置先ボリュームの空きを確保。`--test-free-bytes N` は実測より下げるだけ、必要量の上書きは不可 |
| 未同意（3） | 原文を読んだ本人のみ同意。エージェントが代行しない |
| 依存競合（5）・ノード別版/追跡変更 | 原本保持。専用環境・固定版を確認。既存依存は自動更新・巻戻ししない |
| pip 失敗/事後版不一致（6）・期限超過（7） | 変更が途中の可能性あり。ComfyUI を止めたまま本人が仮想環境の `python -I -m pip --isolated check`（pip check）と差分を確認 |
| hub 不在/1.0未満・PyYAML 不在（1） | 指定 ComfyUI venv の Python -I を使う。スクリプト用に追加導入しない |
| 登録同名別内容（5） | Harness パネルで既存項目を削除してから再登録。同時更新を止める |
| ffprobe 不在/実行不可（1） | ffmpeg と同じ場所に ffprobe があるか確認 |
| 動画・履歴不合格（8） | 対象履歴、固定入力、output-dir、H.264/AAC 両ストリーム・解像度・デコードを確認 |
| チャット期限・async 制約 | 同期を使用。15分を超える生成は ComfyUI 側履歴/出力で確認し、再投入を避ける |
| メモリ逼迫 | 文脈削減・モデル解放・同時実行削減。128GB でも無条件保証なし |

終了コード: 0成功 / 1失敗・確認不能 / 2入力不正 / 3未同意 / 4容量不足 / 5既存データ競合 / 6外部処理失敗 / 7期限超過 / 8動画・履歴不合格。

## 安全上の注意と開発検証

認証不要の ComfyUI / Ollama / Harness API を **外部公開しない**。ComfyUI を CORS 許可や `--listen` 付きで起動しない。ループバックだけで運用するローカル単一利用者向けです。

`MiniMaxH3SaveVideo.ffmpeg_path` は任意の実行ファイルを受け取れます。モデルパス・ffmpeg_path・保存先を公開6項目に含めない約束は、プラグインの `comfyui_run` による任意グラフ投入を遮断しません。悪意のある Web ページがブラウザ経由でループバックの ComfyUI API に要求を送る経路は CORS 許可付きの起動で成立しやすくなり、CORS 設定は診断の対象外です。ツール承認・無効化は未調査で、任意投入を許可する残余リスクは利用者判断です。外部サイトの文章や第三者のファイルなど **信頼できない入力をそのままエージェントに実行させない**でください。

固定ノード・プラグインの事前確認の観点と未確認範囲は[記録](doc/verification/issue-1-verification.md)にあります。依存パッケージの中身は未確認で、全面的な安全性保証ではありません。モデル配下のリンク・逸脱を拒否し、コマンドは引数リストと最小子環境を使います。単一利用者の同時ディレクトリ差替えは運用外です。秘密・重み・個人の絶対パスを公開しないでください。公開ログのホームは `~` に置換し、実データの照合は置換前に行います。

```sh
python3 -m unittest discover -s tests -v
```

標準ライブラリの unittest / tempfile / mock でネットワーク・実サービス・GPU なしの検証を行います。PyYAML が無い場合は該当 YAML テストを理由付きでスキップし、実機合格には数えません。hub のインターフェースはスタブで検証します。実機結果は検証記録の LIVE レコードを参照してください。今回の修正差分の実機再実行・独立再レビューは orchestrator が別途実施します。
