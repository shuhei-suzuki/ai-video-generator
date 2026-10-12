# Issue #1 設計：ローカル動画生成環境の再現

## 概要

入力は `doc/requirements/issue-1-requirements.md` 全文と orchestrator の決定。macOS 26・Apple Silicon・128GB、Comfy Desktop 1.1.6（ComfyUI 0.39.2）、Ollama 0.33.3、Harness 0.2.0-rc.2、dsh-comfyui 0.5.4 を対象とする。
本書は実装の決定記録であり、全設計の実機検証済みという宣言ではない。参考試作の上限値・直接上書き・固定個人パスは採用しない。全スクリプトは ComfyUI 仮想環境の Python 3.11 以上で実行する。download だけが既存 `huggingface_hub>=1.0`、check_env だけが既存 PyYAML を要求し、他は標準ライブラリだけで動く。必要ライブラリの不在・hub の版不足は理由を表示して1、スクリプトのための追加導入はしない。README の実行例は `<venv>/bin/python -I scripts/<スクリプト>.py ...` とし、PYTHONPATH などの影響を避ける。POSIX シェルは起動例だけに留める。
利用者が Desktop・Ollama・Harness・ffmpeg・Qwen・プラグインを手動導入し、初回 GUI 起動、設定追記、互換性例外を承諾する。スクリプトはノード導入→同意付きモデル取得→登録→診断→直接生成を担当する。チャット生成は登録ライブラリを同期実行する。
Multi-Tenant Access Control：適用外（理由）：ローカル単一利用者向けのスクリプト群であり、テナント・認可の概念が無い。

### FR / AC / D と設計要素の対応

| 要件 | 受け入れ条件 | 診断 | 設計要素・検証 |
| --- | --- | --- | --- |
| FR-1 | AC-1 | — | README の構成・容量・配置・境界・順序、生成時間・チャット期限、実測記録への参照 |
| FR-2 | AC-2 | — | README の原文・確認日・制限、download の3モデル共通同意ゲート |
| FR-3 | AC-3 | D-3 | 隔離 PyPI 導入計画・既存版保持、モデル入口の実体一致、共通状態判定、残量・下げるだけの空き容量指定、Turbo 再実行 |
| FR-4 | AC-4 | D-5〜D-7 | 設定例・手動例外、応答時刻と Ollama 要求ログの照合 |
| FR-5 | AC-5 | D-1〜D-9 | D-4 のリポジトリ/登録項目の両検査、実使用先だけの D-3/D-6/D-7、ポート起点の D-8、故障注入と実機正常系 |
| FR-6 | AC-6、AC-11 | D-1〜D-4 | API グラフ、固定入力由来の動画ツール、完了待ち・動画検査、直接2条件 |
| FR-7 | AC-7 | D-1〜D-7 | 同名の内容一致/競合判定、公開6項目、同期呼出し証跡、登録項目と履歴の直接照合、チャット動画検査 |
| FR-8 | AC-8 | D-1〜D-9 | verification の成果物対応・状態3区分・証跡・全対処一覧 |
| 公開物の安全性 | AC-9 | — | 秘密・個人パスの文字列点検、公開ファイル一覧で重み不在確認 |
| 信頼境界・残余リスク | AC-10 | D-8、D-9 | URL 制限・待受検査、任意投入と ffmpeg_path の注意 |
| メモリ | AC-12 | — | README の併用指針、チャット前後の時刻付き実測 |

### Opus round 1 指摘と改訂先

| 指摘 | 仕様・依存節への反映 |
| --- | --- |
| D1-01（必須） | 共通 CLI、register、D-4、submit：固定入力の出どころ・同名比較・登録項目との直接照合。FR/AC 対応、影響範囲、テスト、却下案も統一 |
| D1-02（採用） | install・安全性：pip/Git の子設定隔離。設定ファイルありの argv/環境テスト |
| D1-03（採用） | D-8/D-9：ポート所有 PID/同グループの子と Harness 名の和集合。TCP のみ、UDP は未確認記録 |
| D1-04（採用） | install/D-3・影響範囲：モデル入口と共有先の実体一致、共有先作成とリンクのテスト |
| D1-05（採用） | install・テスト：固定 HEAD/追跡 clean、未追跡を許容 |
| D1-06（採用） | download・容量テスト・AC-3 検証記録：min(実測,N) と全再確認、置換根拠 |
| D1-07（採用） | 概要・安全性・影響範囲：-I、空の ProxyHandler、TMPDIR と3種の書込先 |
| D1-08（採用） | install・テスト・対処/却下案：pip 開始前確認、期限超過7と pip check、constraints 不採用 |
| D1-09（採用） | 安全性・共通 CLI テスト：実行物のリンク先を検査、リンク fixture、リンク拒否対象の限定 |
| D1-10（採用） | download・テスト：判定順、残量0の無同意成功、hub>=1.0、転送の全体期限なし |
| D1-11（採用） | submit・検証記録：生成を伴う時間、同起動中の履歴、6項目の表示記録、出力不在/逸脱8 |
| D1-12（採用） | register・影響範囲/テスト：起動中警告続行、同時更新非保証、親作成、UUID4 |
| D1-13（採用） | D-2/D-6/D-7・テスト：ノード別 API と profile の固定先のみ |
| D1-14（採用） | 概要・共通 CLI テスト：スクリプトごとの必要ライブラリ |
| D1-15（採用） | download・安全性・README 点検：本人だけの同意/取得、CORS/--listen 起動禁止 |
| D1-16（採用） | 安全性・テスト：任意の堅牢化と要件由来の変異対象だけに限定 |

## 構成（ファイル一覧と責務）

以下は実装フェーズの新規追加予定。本作業で作るのは本書だけとする。

| ファイル | 責務 |
| --- | --- |
| `README.md` | venv/既存ライブラリの前提・自動化境界・順序・原文ライセンス参照・実行例・生成時間/チャット期限・全対処・メモリ案内 |
| `.gitignore` | `worktree/`、`__pycache__/`、`.DS_Store` を除外。重み・秘密は作業ツリー外に置く |
| `config/h3_models.manifest.json` | 固定3リビジョンの必須ファイル名・バイトサイズの唯一の一覧 |
| `tools/make_manifest.py` | HF API の一覧を固定リビジョンで再生成・任意のローカルサイズ照合 |
| `config/harness/cordis.patch.example.yml` | 指定版のプロバイダ・既定モデル設定の手動追記例 |
| `config/harness/dsh-env.example` | `OLLAMA_API_KEY=local-dummy-not-secret` の手動追記例 |
| `workflows/minimax_h3_t2v_api.json` | 固定3ノードの API グラフ、スモーク既定値 |
| `scripts/h3_common.py` | パス・URL・入力検証、manifest 状態判定、グラフ編集、動画検査、エラー形式を共有 |
| `scripts/install_h3_node.py` | 固定ノード・依存導入、仮想環境 bin とモデルへの補助リンク |
| `scripts/download_h3_models.py` | 選択モデルの同意・非変更判定・容量・取得・再判定 |
| `scripts/check_env.py` | D-1〜D-9 の読み取り専用診断 |
| `scripts/submit_h3.py` | 直接投入・期限付き完了待ち・履歴照合・動画検査 |
| `scripts/register_dsh_workflow.py` | 既存項目を保持した追加・同名同内容は0、別内容は非変更で5 |
| `tests/test_*.py` | unittest、スタブ HTTP・コマンド・一時ディレクトリによる故障注入 |
| `doc/requirements/issue-1-requirements.md`、本書 | 既存要件は変更せず参照。本書は決定の履歴 |
| `doc/verification/issue-1-verification.md` | AC・D ごとの公開可能なテキスト検証記録 |
| `doc/design/master/{architecture,operations,security}.md` | 実装時に作る現在の正（後述） |

## 各スクリプトの仕様

### 共通 CLI・入出力・終了コード

パスの優先順位は明示 CLI 引数→Desktop 1.1.6 の既定配置。配置・接続先の上書きは CLI 引数だけとし、設定用の環境変数は設けない。`Path.home()` と `expanduser()` で実行時解決し、存在・実行可否・仮想環境を検査する。推測で別インスタンスを選ばず不明なら停止する。リポジトリ資材は `__file__` 起点で解決し、-I でも共通モジュールを読めるよう `importlib` で同じ scripts 内の `h3_common.py` を明示ロードする（PYTHONPATH に依存しない）。
既定インスタンスは `~/ComfyUI-Installs/ComfyUI`、本体は `<instance>/ComfyUI`、venv は `<comfy-root>/.venv`（実機の本体ディレクトリ直下）。共有モデルは `~/ComfyUI-Shared/models/minimax_h3`、出力は `~/ComfyUI-Shared/output`。明示された共有モデルルートのリンクは入口として解決し、その実体を包含検査の基準にする。
共通配置指定は `--instance`、`--comfy-root`、`--venv`、`--models-dir`、`--output-dir`、`--manifest`、`--data-dir`（既定 `~/.dsh/data/dsh-comfyui`）。各 CLI は責務に必要なものだけを受け、`--help` に既定値と解決元を示す。インスタンスの各配置は共通 resolver で導出し、明示指定を実使用先と診断先の両方に適用する。
グラフの唯一の出どころは `workflows/minimax_h3_t2v_api.json`。register/submit に `--ffmpeg` による上書きは設けず、別の workflow/ffprobe 指定も設けない。固定入力 `/opt/homebrew/bin/ffmpeg` は Apple Silicon の Homebrew 既定配置を対象とし、別配置の利用者はこのファイルを自分で編集して登録し直すと README に記す。動画検査・補助リンクの ffmpeg は Save 固定入力、ffprobe はそのパスの同じディレクトリから導出する。
終了コードは 0=成功（完了済み・同名同内容含む）、1=失敗または確認不能、2=引数・入力形式不正、3=未同意、4=容量不足、5=既存データとの競合（取得途中・サイズ不一致・別版・リンク先相違・同名別内容・既存パッケージの入れ替え計画）、6=外部処理・API の失敗、7=期限超過、8=動画検査不合格。check_env は有効な引数で1項目でも異常なら1、全正常なら0。
stdout は対象・状態・集計・ID・保存先・検査結果、stderr は `項目/処理名: 原因分類; 対処`。HTTP 本文・env 値・profile 全文・未加工例外は表示しない。ログのホームは `~` にするが、実際の通信・コマンドには解決済みパスを使う。
HTTP 1要求30秒、診断1要求5秒、ポーリング2秒、生成全体7200秒、git/pip 各1800秒、動画検査各300秒を既定とする。`--http-timeout`、`--timeout`、`--poll-interval`、`--command-timeout` で対象の期限を正の有限値に上書きできる。期限は monotonic 時計、生成中の1要求も残り全体期限以下とする。数十GBの個々の hub 転送には全体期限を設けず、生成・外部コマンドの期限を適用しない。

### install_h3_node.py

引数：共通配置、実行ファイル指定は `--venv` と `--git`（PATH から絶対パス解決）だけ。入力：固定 GitHub ノード、同コミットの requirements、venv の導入済み配布物。出力：custom_nodes の対象1ディレクトリ、新規依存、補助リンク、前後のパッケージ差分。
変更前に venv の Python で `-I -m pip --isolated --version` が動くこと、対象ノード・venv・補助リンクの競合と書込権限を全件確認し、ComfyUI を停止する手順を示す。固定コミット `ab1756d571ebb14fed3168354dae42966a04348b` を一時領域に取得し HEAD を照合する。既存ノードの clean は HEAD が固定コミットと一致し追跡ファイルに変更が無いこと。未追跡の `__pycache__` 等は許容し、別版・追跡変更・非 Git は5で中止する。他の custom_nodes は操作しない。
導入前に requirements の URL・VCS・追加 index・他ファイル参照の行を拒否して2で停止する。固定コミットの requirements は名前と版指定だけであることを確認済み。venv の Python の `-I -m pip --isolated list --format=json` で事前の名前・版を保存し、`-I -m pip --isolated install --index-url https://pypi.org/simple --dry-run --report <一時ファイル> -r requirements.txt` で計画を得る。事前集合にある正規化名が install 対象なら同版も入れ替え計画として差分表示・非変更で5。計画取得失敗は6、形式不明は変更前に1。
入れ替えが無ければ同じ requirements・isolated・index 指定で dry-run/report だけを外して導入し、`-I -m pip --isolated check` と既存の名前・版の不変を検査する。失敗・相違は6、pip の期限超過は「変更が途中の可能性あり」と表示して7、本人に `pip check` を案内する。自動巻き戻し・constraints は採用しない。計画・前後差分・検査結果を記録する。
pip は全呼出しに `--isolated`、接続する呼出しに `--index-url https://pypi.org/simple`、子だけに `PIP_CONFIG_FILE=/dev/null` を設定して利用者設定ファイルを読ませない。git の子だけに `GIT_CONFIG_GLOBAL=/dev/null`・`GIT_CONFIG_NOSYSTEM=1` を設定し `url.*.insteadOf` 等を無効にする。
成功後にノードを配置する。venv/bin の ffmpeg・ffprobe は未配置時だけ固定入力由来の実行物へのリンクを作り、既存は同じ実体なら保持、別実体・切れたリンクなら非変更で5。モデル入口は `<comfy-root>/models/minimax_h3`。共有側 `--models-dir` が無ければ作成してから入口のリンクを張り、既存入口は同じ実体なら保持、異なる実体・切れたリンクなら非変更で5。失敗時は工程・安全な再実行方法を表示し、今回だけの未配置一時領域を片付ける。

### download_h3_models.py

引数：`--models base int8 turbo`（既定は3種全部、部分選択可）、`--models-dir`、`--manifest`、`--accept-license`、`--test-free-bytes N`。Python と既存ライブラリの前提は共通仕様に従う。入出力：manifest と現状→選択モデルの不足ファイル・hub メタデータ、対象/リビジョン/一覧/配置先/状態/必要量/空き容量の表示。
判定順は引数・一覧の検証(2)→全選択対象の状態走査→取得途中・サイズ不一致があれば5→残量0なら同意を求めず0→同意(3)→容量(4)→取得(6)。hub の有無・版を調べるのは取得が必要になってからで、残量0なら hub が無くても0。必要な hub>=1.0 の不在・版不足は1。状態異常や完了済みを同意ゲートで隠さない。
取得が必要なときネットワーク前にライセンス原文の固定リビジョン参照、2026-10-12 の確認日、非正本要約、米国・EU・英国・韓国の利用対象外、年商2,000万USD超の別途許諾、派生2モデルにも H3 条件が及ぶ前提を表示する。Turbo は提供された全ファイル一覧に LICENSE が無いため、固定リビジョンの README と Apache-2.0 原文を参照する。TTY の明示 `yes` または `--accept-license` のみ同意。EOF・非TTY・拒否は3、環境変数で同意を代替しない。README に「`--accept-license` はライセンスを読んだ本人だけが付ける。エージェントに取得スクリプトを実行させない」と記す。
共通判定はファイル単位で「完了=通常ファイルかつサイズ一致」「未取得=不存在」「取得途中=サイズが一覧より小さい、またはモデルの `.cache/huggingface/download/` 内の `.incomplete`」「サイズ不一致=大きいサイズ」。型不正・読取不能・逸脱は異常として拒否する。
一覧外のファイルは非変更で許容するが `.incomplete` は必須ファイルの一致より優先して取得途中と判定する。選択集合を全件事前走査し、取得途中・不一致が1つでもあれば全取得を開始せず5。利用者が自分で退避する対処だけを示し、resume・repair・force を提供しない。
残量 R は未取得ファイルの size 合計（Qwen を含めない）。R>0 の必要空き容量は `R + max(1 GiB, ceil(R×0.05))`。配置先の最寄り既存親から同一ボリュームの free を測り、配置先作成後にも再確認する。R=0 は容量要求・hub 呼び出しなしで0。GB と GiB・整数バイトを区別して表示する。
`--test-free-bytes N` は非負整数で、free を毎回 `min(実測, N)` として容量ゲートを緩めない。配置先作成後・取得直前の再確認にも同じ N を使う。必要量は manifest と現状から算出・表示し、AC-3 欄に「必要量を上書きする指定」を「空き容量側を下げる指定」に置き換えた根拠（必要量を保ち不足だけを再現する）を残す。
未取得ファイルだけ `hf_hub_download(repo_id, filename, revision=固定SHA, local_dir=..., token=False)` をそのまま使って順に取得する。対象機で成功した標準の転送経路を使い、配布ホストの許可リスト・リダイレクト検査を独自実装しない。各取得直前にも存在・逸脱・空きを再確認し、既存ファイルの上書きをしない。通信失敗は6、今回生じた途中データを削除せず表示する。取得後の全選択対象を再判定しサイズ一致時だけ0。存在とサイズの一致は暗号学的な完全性保証ではない。

### check_env.py

引数：共通資材指定（`--data-dir` を含む）、`--comfy-url`、`--ollama-url`、`--profile-dir`、`--env-file`、`--harness-process`（既定 `DeepSeek Harness`）、`--lsof`、`--ps`。ComfyUI/Ollama の名前指定と plugin 探索指定は設けない。読み取り専用で最後まで診断し、`D-n PASS/FAIL/UNKNOWN: 原因; 対処` を各行表示する。

| ID | 確認方法・失敗時の表示と対処 |
| --- | --- |
| D-1 | `GET /system_stats` の成功・期待 JSON。無応答/不正応答→API 起動・指定 URL 確認 |
| D-2 | `GET /object_info/<クラス名>` を要件の4ノードごとに取得。欠落名を表示→ノード導入・再起動 |
| D-3 | 3モデルを download と同じ一覧・状態判定し、`<comfy-root>/models/minimax_h3` の存在と解決先が検査した `--models-dir` と同じ実体かも検査。欠落/サイズ/途中/入口相違→不足取得・本人による退避・入口の修正 |
| D-4 | (a) リポジトリの Save 固定入力 ffmpeg_path、(b) ライブラリに `minimax-h3-t2v` があればその Save 固定入力 ffmpeg_path の両方を絶対パス・実行可能か検査（リンク解決先は通常ファイル）。値が異なれば FAIL。不正 JSON・非リスト・対象名重複は FAIL とし未登録に代替しない。未登録は(a)だけで判定し「未登録」と表示、登録自体は AC-7 で確認。ffprobe の有無・実行可否も補足表示するが合否は ffmpeg 条件。不可→本体導入/ワークフローファイル編集、相違→既存項目をパネルで削除して再登録 |
| D-5 | Ollama `GET /api/tags` で API 応答と `qwen3.8:27b-mlx`。不在→手動 pull、無応答→起動 |
| D-6 | `<profile-dir>/cordis.patch.yml` だけで llm-pi-ai/agent-default-model、ollama URL/API/model/apiKeyEnv の整合と env 内対象キーの非空存在。欠落/曖昧/未解決→既存設定を保持して手動追記 |
| D-7 | `<profile-dir>/node_modules/dsh-comfyui/package.json` だけで name=`dsh-comfyui`・version=`0.5.4`。探索しない。未導入/別版→手動導入、例外は承諾後のみ |
| D-8 | 指定 ComfyUI/Ollama URL のポートで TCP LISTEN する PID を lsof で求め、その PID と同じプロセスグループの子の全 TCP LISTEN を検査。持ち主不在は UNKNOWN、外部待受は FAIL→起動/URL/ループバック設定確認 |
| D-9 | 動的ポートの Harness は完全なプロセス名で同定し、複数一致は和集合（子も含む）の全 TCP LISTEN を検査。未起動/待受無し/不明→起動して再診断 |

D-6 は ComfyUI 仮想環境の PyYAML の `yaml.safe_load` 相当を使う。SafeLoader を基に、未知のタグ（`!!js` など）は値を解釈せず不透明な値として読むローダーとし、任意オブジェクトを生成するローダーは使わない。安全に読める通常の YAML 構文を独自に制限しない。対象外 id は読み飛ばし、読取不能・想定外の構造・対象設定の重複や曖昧さ・確認対象が不透明な値なら UNKNOWN、推測で PASS にしない。env は行ごとにキー名（任意の export 接頭辞対応）を先に判定し、対象キーだけ引用を除いた非空判定、他の値は分割・保持せず全値を非表示。空の引用値・対象キー重複・展開が必要な値は解決済みとしない。source/eval・シェル展開はしない。
profile 既定は `~/.dsh/profiles/desktop`、env は `~/.dsh/.env`。D-6/D-7 は同じ profile の指定ファイルだけを読み、別 profile の正常値で補わない。ライブラリは register/submit/check が同じ `--data-dir` の workflows.json を読む。
lsof は `-nP -a -p <PID集合> -iTCP -sTCP:LISTEN -F...` の機械形式、ps は PID/親子/プロセスグループの関係に使う。IPv4/IPv6 の実アドレスが `*`・`0.0.0.0`・`::`・LAN なら FAIL、127/8・`::1` だけ PASS。権限不足/解析不能は UNKNOWN。対象は TCP LISTEN だけで、UDP は対象外として未確認範囲に記録する。

### submit_h3.py

引数：`--prompt`、`--width`、`--height`、`--seconds`、`--steps`、`--seed` の公開6項目、`--output-dir`、`--data-dir`、`--comfy-url`、期限指定。後者は運用設定で LLM 公開パラメータではない。モデルパス・ffmpeg・保存先 prefix のグラフ編集引数と `--no-wait` は設けない。
入力：検証済み API グラフと6項目。出力：prompt_id、生成条件、経過時間、実投入グラフの照合結果、保存先・存在・ストリーム・デコード判定。スモーク既定は64×64・1秒・steps=5・seed=0、プロンプトはシーンと音の固定例。幅/高さは正の32倍数、秒数は正の有限数、steps は2以上の整数、seed は非負整数、prompt は非空文字列。上限を新設せず大きい値の費用・メモリを案内する。
リポジトリの固定グラフを複製し Generate ノードの6フィールドだけ置換する。構成・固定入力を検証して `POST /prompt`、node_errors/拒否は6。`GET /history/<prompt_id>` で対象 ID の error は6、completed を期限内で待ち、未完了は7（サーバーのジョブを自動停止・再投入しない）。
履歴の実投入グラフを照合し、Save ノードの出力 filename/subfolder/type=output を検証して output-dir 内の通常動画へ解決する。絶対パス・`..`・リンクによる出力ディレクトリ外への逸脱・不明な出力構造・動画不在は8。stdout の文字列を保存先とは見なさない。
ffprobe の JSON で H.264 映像と AAC 音声の両ストリーム・要求解像度を検査、ffmpeg `-v error -xerror -i <絶対動画パス> -map 0:v:0 -map 0:a:0 -f null -` で全フレームをデコードし非ゼロ/エラーは8。検査期限超過は7。導出先の ffprobe が無い・実行できない場合は1で「ffmpeg と同じ場所に ffprobe があるか確認」と案内する。秒数と実測フレーム数の一致を合否にしない。
`--verify-history ID` は新規投入せず、登録項目があれば履歴をその workflow とリポジトリのグラフの両方に直接照合し、無ければリポジトリと照合する。不正 JSON・非リスト・対象名重複は2とし未登録に代替しない。構成・固定入力がどちらかと異なれば外部コマンドを起動せず8。公開6項目は履歴の値を表示・記録して値一致を合否にしない。動画の要求解像度は履歴から得る。submit/verify の動画ツールは常にリポジトリの Save 固定入力の ffmpeg と同じディレクトリの ffprobe を使い、ライブラリ内容から実行物を導出しない。
README と検証記録に、2026-10-12 の対象機での目安として64×64・1秒・steps=5は約1分、768×448・5秒・steps=9は約10〜14分、448×768・15秒・steps=9は完了結果48分を載せる。生成全体の既定期限は7200秒を維持する。
チャット同期実行ではエージェントが `timeout_ms: 900000`（15分）で呼んだため、長い生成はチャット側が先にタイムアウトしうる。その場合も ComfyUI 側の生成は継続する。長い生成では指示文でタイムアウトを明示し、完了は出力ディレクトリか実行履歴で確認する対処を README と検証記録に載せる。

### register_dsh_workflow.py

引数：`--data-dir`、`--harness-process`（check と同じ既定名）、`--ps`。入力：リポジトリの API グラフと workflows.json、出力：名前 `minimax-h3-t2v` の1項目。公開6項目の既定値はグラフから生成し、上限 max は付けない。data-dir 不在なら作成、項目 id と各 parameter id は UUID4。
JSON 不正・リスト以外・不正項目・対象名重複は非変更で2。同名時は既存の workflow 全体と parameters（各 parameter の id だけを除く）を今回の内容と構造比較し、同内容は「変更なし」で0、別内容は原本を保持して5。ノード/入力キーと parameter 名/フィールドで差分の所在を表示し、対処は「Harness の ComfyUI パネルで既存項目を削除してから登録し直す」。他の項目・未知フィールド・順序を保持する。
Harness 起動中は警告して続行し、同時更新は保証しない旨を表示する。README は終了してからの登録を勧めるが拒否条件にはしない。既存ライブラリファイルのリンクを拒否し、権限保持した同じ親の一時ファイルへ UTF-8 JSON を書き、flush/fsync→元の stat/内容再確認→`os.replace`（新規0600）。元の変化は5・非変更、置換前エラーは原本保持で非ゼロ。一時ファイルを除去し、親ディレクトリ fsync は任意とする。

### tools/make_manifest.py

引数：`--output`（既定 config の一覧）、`--compare-dir`（任意）、`--http-timeout`。固定3 repo/revision/include から HF API `.../api/models/<repo>/revision/<SHA>?blobs=true` を取得し sha 一致・パス・サイズ・重複を検証、ソート済み一覧を一時ファイルから置換する。モデル本体は取得しない。
照合指定時は共通判定の全件結果も表示し、失敗なら出力を置換せず1。API/sha 不一致は6、入力不正は2。出力は一覧件数・合計・照合結果。通常 download/check はこのツールを呼ばず、レビュー済み一覧だけを消費する。

## データ形式（必須ファイル一覧・ワークフロー・設定例）

manifest は schema=1、models は base/int8/turbo が各1件。各モデルは `key,repo,revision,local_dir,include,total_bytes,files`、files は `{"path":"相対POSIXパス","size":整数バイト}`。size は bool を除く非負整数、path は一意、total_bytes は合計と一致、revision は下表と一致を必須とする。全136件の詳細は config の一覧に収録し本書はその同じ一覧を参照する。

| key / repo / local_dir | 固定リビジョン | 範囲・件数・合計バイト |
| --- | --- | --- |
| base / `MiniMaxAI/MiniMax-H3` / `MiniMax-H3` | `42ed227ee7df40d41602854ae760620d6eb651fe` | `FL2VA/model_index.json` と tokenizer/processor/text_encoder/video_vae/audio_vae 配下、66件、77,770,657,762 |
| int8 / `water1234/MiniMax-H3-MLX-Argus-Calibrated-INT8` / repo末尾と同名 | `70505b09c80e298e684d798d8e0f946937dcfad4` | `.gitattributes` を除く全13件、37,797,145,373 |
| turbo / `water1234/MiniMax-H3-Turbo-v4-step600-EMA-MLX` / repo末尾と同名 | `9771f9c606a50671bb94ee57191461602f02d1fc` | `.gitattributes` を除く全57件、1,559,967,577 |

合計117,127,770,712バイト（約117.13GB）。提供された実データの件数・サイズを実装時に転記・再照合する。存在・サイズ一致は最低基準であり、同サイズ改変の暗号学的完全性保証ではない。README は確認日と部分取得範囲付き実測記録を参照し、150GBは Qwen/インスタンス/キャッシュ/動画も含む暫定目安として扱う。
グラフは node 1=ModelLoader、2=Generate、3=SaveVideo、接続は1→2→3。D-2 の ResultToComfyUI は登録確認対象であり本グラフには不要。checkpoint=`MiniMax-H3/FL2VA`、transformer=int8 local_dir、turbo_lora_path=turbo local_dir、text_encoder_dir は空（checkpoint 内解決）。
Loader 固定入力は low_memory/stream_blocks=true、group=2、memory_limit_gb=32、memory_pressure_guard/load_vision=false、LoRA scale=1/alpha=0、sigma shifts=0、dense_dequant_profile=off。Generate 固定入力は drop_adaln=true、block_cache/cache_text_conditioning=false、threshold=0.12/depth=0.75/max_consecutive=2。Save 固定入力は filename_prefix=`minimax_h3/ComfyUI`、crf=18、ffmpeg_path=`/opt/homebrew/bin/ffmpeg`。これらはリポジトリのワークフローファイルでだけ変更し、register はその値を保存する（Cellar 版番号パスを埋め込まない）。
ライブラリ項目は `id,name,description,workflow,parameters,tags,updatedAt`。parameters は各々 `id,name,label,type,nodeId,inputKey,default` と numberKind/min/step または seed の random を持つ。name/inputKey 集合は prompt,width,height,duration_seconds,steps,seed と完全一致、nodeId=`2`。モデル/ffmpeg/保存先は固定値で公開しない。
設定例は YAML の `id: llm-pi-ai`→`config.providers.ollama` に `api: openai-completions`、`baseURL: http://127.0.0.1:11434/v1`、`apiKeyEnv: OLLAMA_API_KEY`、model id=`qwen3.8:27b-mlx`、contextWindow=65536、maxTokens=8192、input=[text,image]。`id: agent-default-model` に provider=ollama/model 同上。`.env` 例はダミー1行。適用は利用者が既存項目を保持して追記し、スクリプトで YAML を再保存しない。

## 安全性設計（信頼境界・入力検証・外部コマンド・外部 URL・秘密情報）

信頼するのは本人の配置先・venv・運用指定と事前確認した固定ノード。manifest、HTTP 応答、履歴、既存 JSON は入力として型・構造を検証する。ノードと依存は実行コードであり固定版だけで安全とは扱わず、実装前に読み込み・外部処理・配布条件を確認し、日付・版・観点・未確認範囲を記録する。
manifest の path/local_dir は絶対パス、空要素、`.`/`..`、NUL、バックスラッシュを拒否し、resolve 後もモデルルート内かを Path の包含判定で確認する。モデル配下のリンクは cache を含め拒否し、読み書き直前にも再検査する。リンク自体を拒否する対象はモデル配下とライブラリファイルだけで、モデル入口は解決先一致、動画は通常ファイルと出力ルート包含で判定する。同時のディレクトリ差し替えは単一利用者の運用外とし、複数取得を禁止する。
JSON の非有限数・不正型は拒否する。プロンプトはデータとして JSON 化し、コマンドや YAML に埋め込まない。検証前の副作用を避け、ファイル出力先は profile/env と重なる指定を拒否する。要件に結びつかない JSON 重複キー拒否、FIFO・デバイスの追加拒否、親ディレクトリ fsync、応答サイズ上限は実装時に省いてよい任意とし、追加の受け入れ条件や変異対象にしない（必須の通常ファイル判定は維持）。
外部コマンドは subprocess の引数リスト・shell=False。python・git・ffmpeg・ffprobe・lsof（ps も同様）は絶対パスのリンクを辿った先が通常ファイルかつ実行可能かを見る。Homebrew bin/venv python のリンクは許容する。Python は ComfyUI venv の `-I`（venv の判別を保持するため実行は入口パス）、git/ps/lsof は指定または PATH 解決、動画ツールは常にリポジトリの固定入力由来。argv の固定オプションと絶対 operand を分ける。
親環境から読むのは HOME・必要最小限の PATH/locale・TMPDIR。子へも最小環境と install 節の Git/pip 固定設定だけを渡す。秘密・proxy・任意 Git/pip 設定の環境変数は継承しない。TMPDIR は tempfile の既定に従い、全消費者で勝手に差し替えない。管理者権限・hook 無効化・シェル設定変更をしない。
ComfyUI/Ollama は `http` または `https`、host は IP リテラルの127/8または `::1` のみ（localhost は使わず DNS を避ける）、port は1〜65535。userinfo/query/fragment を拒否、ComfyUI は空/root パス、Ollama は空/root または `/v1` のみ。ループバック HTTP は urllib の `ProxyHandler({})` でシステムのプロキシ設定を使わず、redirect も拒否する。別ポートは許す。
外部接続は固定 GitHub repo（`github.com`）、固定 HF repo の標準転送経路、明示 PyPI index（`pypi.org`・`files.pythonhosted.org`）を使い、TLS を検証する。HF API/取得のエンドポイントは `https://huggingface.co` に固定し、`HF_ENDPOINT` を継承しない。標準 hub クライアントの配布経路に独自のホスト許可リストやリダイレクト検査を追加しない。
hub の初期化前に隔離した実行環境で暗黙トークンを無効に固定し、取得には `token=False` を指定する。manifest 再生成の HF API にもトークンを送らない。固定リビジョンと取得後のサイズ照合を用いるが、存在・サイズ一致は暗号学的な完全性保証ではない。D-6 は対象キーの非空存在だけを見る。どの値も表示・変更せず、対象外の値を取得しない。設定例に実キーを入れない。
`~/.dsh` の永続ファイル書込みは workflows.json だけで、register の data-dir 作成も許す。全 CLI の実体解決済み書込先にこの制限を適用し、register の許可先以外は引数による迂回も拒否する。同じ親の一時ファイルは成功/失敗とも残さない。`--data-dir` が `~/.dsh` 内ならライブラリ用の親だけを許し、profile/env 配下を拒否する。外の検証用配置先は許可する。check/verify のライブラリ読取もリンク・不正 JSON・対象名重複を拒否し、不正を未登録扱いで代替しない。
標準経路の6項目制限は `comfyui_run` の任意投入を遮断しない。ffmpeg_path は任意実行物を受け得るため、README に外部公開禁止、「ComfyUI を CORS 許可や `--listen` 付きで起動しない」、未調査のツール承認/無効化は利用者判断、第三者の文章・ファイルをそのまま実行させない注意を記す。

## 影響範囲分析

変更対象は新規追加のみ。既存コード・API 契約・DB は無く、既存要件は読み取りだけ。調査時のファイル一覧は要件書のみで既存呼び出し元なし（行番号を持つ既存コード参照は該当なし）。新設共通モジュールの消費者は上記6 CLI と tests。実装時に定数・env・一覧・パスの全参照を rg で再確認する。

| 実行時の利用者環境 | 誰が読むか／触るか・影響・対応 |
| --- | --- |
| ComfyUI custom_nodes の対象ディレクトリ | install が新設/同版確認、check D-2 が API 経由で確認。固定版競合は停止 |
| ComfyUI venv と bin | 全 CLI が Python -I、download だけ hub>=1.0、check だけ PyYAML。install が新規依存・補助リンク、submit が固定入力由来ツール使用。既存版保持・同実体保持/別実体拒否で互換性保護 |
| 共有 models と `<comfy-root>/models/minimax_h3` | install が共有側作成・入口リンク新設、download が未取得分取得、D-3 が全件と入口実体一致を確認。残量/部分選択で容量・帯域を抑え、既存データ非変更 |
| ComfyUI output | サーバーが動画保存、submit が履歴と動画読取・デコード。生成/検査の時間・GPU/メモリ/追加容量を記録 |
| `~/.dsh/data/dsh-comfyui/workflows.json` | register が親作成・保持追加/原子置換、Harness が実行、check/verify が同じ data-dir を読取。同名同内容0/別内容5、起動中警告・同時更新非保証 |
| Harness profile・`~/.dsh/.env` | D-6 が安全な YAML ローダーで必要設定を読み、env の対象キー存在だけ確認。未知タグは不透明、読取不能/構造不正は UNKNOWN。書換え禁止、設定例適用は本人の手作業 |
| `<profile-dir>/node_modules/dsh-comfyui/package.json` | D-7 が指定 profile の固定先だけ読取、他の導入領域を探索せず実使用先と揃える |
| 配置先の `.cache/huggingface/` | download の huggingface_hub がメタデータ・途中ファイルを書込み、download/D-3 が途中判定。容量と非変更拒否に反映 |
| pip のキャッシュ | install の計画・導入で書込みが生じる。既存配布物の不変とキャッシュへの副作用を区別して記録 |
| `scripts/__pycache__` | Python の共通モジュール読込で生成されうる。gitignore 対象、導入対象の追跡 clean 判定とは別 |
| シェル設定・他のカスタムノード | 全スクリプトで書込みなし。対象外ディレクトリの非変更を回帰検証 |

| 定数・閾値・入力 | 誰が読むか／変更時の波及 |
| --- | --- |
| ノード SHA、モデル3 SHA、repo/include/local_dir | install、make_manifest、download、D-3、README、tests。更新は一覧再生成と全消費者照合が必要 |
| 固定 requirements・pip 導入計画・HF endpoint/トークン非送信 | install の事前/事後検査、download/make_manifest の接続、tests、README/verification。既存版保持・標準転送・上書き設定の非継承を照合 |
| ポート8188/11434、URL規則、動的 Harness 待受 | check、submit、設定例、tests。別ポート正常系と非ループバック拒否を双方検証 |
| Desktop/共有パス、bin、ffmpeg 固定入力、dsh ライブラリパス | resolver/install/submit/register/D-3/D-4、グラフ、README、tests。固定入力を重複 CLI で渡さず導出、D-4 はリポジトリ/登録項目双方、verify は登録項目を直接照合 |
| 各タイムアウト・ポーリング間隔 | 共通 HTTP/command、check、submit、make_manifest、期限テスト。hub 転送は全体期限対象外。7200秒とチャット900000ms、pip 期限超過の途中変更案内を README/verification に記録 |
| 容量余裕1GiB/5%、150GB暫定目安、test-free N | download と容量テスト、README/verification。R=0 の無同意成功と `min(実測,N)` を全再確認で維持 |
| 必須ファイル一覧136件（base66/int8 13/turbo57） | make_manifest が生成、download/D-3 が読む、tests が欠落/件数/合計/余分/途中を検査、設計/README が参照 |
| 公開6項目・固定3ノード・4登録ノード・ライブラリ名 | 共通グラフ、submit/register/D-2/D-4、Harness、履歴照合、tests。集合完全一致を検証 |

親環境から読む変数は次の最小限だけで、値を記録しない。共通配置・URL・指定可能な実行物は CLI と resolver に揃え、ffmpeg/ffprobe はグラフから、ComfyUI/Ollama の PID は URL ポートから導出する。

| 環境変数 | 誰が読むか |
| --- | --- |
| `HOME` | 共通 resolver のホーム解決。子にも渡す |
| `PATH` | git/ps/lsof の実行物探索と子プロセス用の最小経路 |
| locale（`LANG`・必要な `LC_*`） | 子プロセスの文字コード・表示制御に必要な分だけ渡す |
| `TMPDIR` | tempfile の既定の一時ファイル置場。pip/子プロセスにも渡すため全一時パスに波及、差し替えない |
| `GIT_CONFIG_GLOBAL`・`GIT_CONFIG_NOSYSTEM`・`PIP_CONFIG_FILE` | 親の値は読まず、install の子だけに固定値を設定。利用者の git/pip 設定ファイルを無効にする |

入力データ一覧は manifest 全件、API グラフ、profile、env ファイルの対象キー名、plugin package.json、workflows.json、HTTP 履歴/タグ/object_info、ps/lsof 出力、固定 requirements、pip 導入計画・前後の配布物一覧。各読者は上記仕様と対応する。`OLLAMA_API_KEY` は Harness 用設定であり、D-6 は env ファイル内の存在だけを確認し、プロセス環境から読まない。hub のエンドポイント・暗黙トークン無効化は内部の固定設定で、利用者の上書き入力ではない。必要設定以外のデータは読み出し/出力を増やさず、版ずれ自動検出や他アプリ移行は別スコープとする。

## テスト方針（故障注入の方法と AC の対応、変異検証の対象）

unittest と tempfile、mock した HTTP opener/応答・subprocess/hub/disk_usage を使用。実装担当のネットワーク禁止に従い HTTP サーバーも起動しない。実サービス・大容量取得・生成は単体/統合テストの前提にしない。副作用を呼び出し記録とファイル内容/hash/mtime で検査し、拒否と正常系を対にする。
実行は ComfyUI venv を原則とする。PyYAML が無いテスト環境では D-6 関連をスキップ理由付きでスキップし、合格に数えない。実機 D-6 正常系は同 venv の PyYAML で別途必須とする。

| 対応 AC / D | 故障注入・合否 |
| --- | --- |
| AC-2 | 取得が必要な base/int8/turbo 各々で EOF/拒否/非TTY と yes/flag。未同意は通信0件、同意後のみ取得呼出し |
| AC-3 / D-3 | 小サイズ manifest と各モデル別の欠落/過小/過大/incomplete（余分な途中も）/通常余分を一時配置。非変更・表示・終了コードと download/D-3 の一致 |
| AC-3 / D-3 | free=必要量-1/同値、N が実測より低い/高い、別ボリューム、作成後/取得直前も同じ N。全完了は free=0・未同意でも0、途中/不一致は未同意でも5。入口不存在/別実体は D-3 失敗、共有側不在は install が作成 |
| AC-3 | pip report の既存名（同版/更新/ダウングレード）→非変更5、新規だけ→同じ isolated/index で導入・pip check・既存版不変。URL/VCS/index/他ファイル参照拒否、pip 不在/失敗/期限超過7と案内。固定 HEAD+追跡変更なしなら未追跡を許容、異版/追跡変更拒否。bin/モデル入口は同実体保持、別実体/切れたリンク5、profile/env/シェル非変更 |
| AC-3 | index 指定入り pip 設定・insteadOf 入り git 設定があっても組み立てる argv と子の固定環境が変わらない。plan/install の同一 index と設定ファイル非参照を確認 |
| AC-5 / D-1,D-2,D-5 | 無応答/壊れた JSON/4ノード各欠落/Qwen 不在を HTTP スタブで個別注入。該当項目の原因と非ゼロ |
| AC-5 / D-4,D-6,D-7 | リポジトリ/登録項目各々の相対/不在/実行不可 ffmpeg、両方実行可能だが値相違→FAIL、未登録→リポジトリのみ。profile 欠落/不正/曖昧、対象キー無し/空、固定先 plugin 不在/別版と別 profile の正常値で補わないこと。安全 YAML/未知タグと全 env 目印の非表示・非変更を確認 |
| AC-5,AC-10 / D-8,D-9 | URL ポートの持ち主と同グループの子、持ち主無し UNKNOWN、別ポート正常、Harness 名の複数一致の和集合。各 PID の `*`/0.0.0.0/::/LAN/混在、権限不足/解析不能/待受無し、正常 IPv4/IPv6 と子の外部待受を検査。UDP は未確認と記録 |
| AC-6 | POST 拒否/node_errors、history エラー/未完了期限。不在動画/出力ルート逸脱は8。ffprobe 音声無し/異 codec/異解像度、ffmpeg デコード失敗を個別注入、両ツールが Save 固定入力由来であること |
| AC-7 / D-4 | 同名の workflow/parameters の id 以外が同内容→バイト不変0、固定入力/公開既定値等が相違→差分所在と削除再登録案内・非変更5。不正/非リスト/対象名重複・未知フィールド保持・原本変化、data-dir 作成/UUID4/起動中警告続行も確認 |
| AC-7 | verify は登録項目があれば登録項目とリポジトリの両方へ直接照合し、未登録時だけリポジトリのみ。不正 JSON/非リスト/対象名重複は2、D-4も登録項目側を FAIL とし、両経路を変異検証する。固定入力/構成相違は外部実行なしで8、6項目の履歴値は表示・記録し値の相違だけでは不合格にしない。動画実行物がリポジトリ由来であることを確認 |
| AC-9,AC-10 | パス逸脱/モデル配下・ライブラリのリンク、ローカル API の URL userinfo/非ループバックhost/redirect、秘密目印の応答、特殊文字プロンプト。拒否時の通信・外部実行0件と正常入力の成功。hub は固定 endpoint/revision・token=False・暗黙トークン無効と標準取得呼出しを検査し、親の endpoint/トークン設定を継承しないことを確認 |
| 共通 CLI | 配置の優先順位と実使用/診断の一致、旧 ffmpeg 上書き拒否、リンク経由の python/git/ffmpeg/ffprobe/lsof fixture、ProxyHandler({})、README の -I と共通モジュール読込。download の hub 不在/1.0未満、check の PyYAML 不在→1、それ以外は両方不在でも動くこと |
| AC-1,AC-4,AC-8,AC-12 | README/設定例/対応表/対処/実測の文書点検。実機必須の結果をスタブ成功で代替しない |

変異検証は要件に結びつく同意ゲート、SHA・サイズ照合、取得途中判定、残量0の扱い、容量の不等号、パス包含、ループバック制限、診断の集約、キー値非表示、公開6項目の集合、同名登録の同内容/別内容、動画検査3種（両ストリーム・解像度・全デコード）、D-4 の登録項目側の検査と verify の登録項目との照合・不正ライブラリ拒否に限る。一時コピーの実装を1箇所ずつ変更して意図したテストが失敗することを記録し、構文エラーは検出成功に数えない。任意の堅牢化を変異検証の必須対象にしない。
実機は固定 requirements の PyPI 導入・既存版不変・pip check、Turbo の標準転送による空の一時配置先への取得→同条件2回目、D-1〜D-9 全正常、直接スモークと768×448・5秒・steps=9・seed42、チャット同期スモークを確認する。チャットはツール名/引数・ライブラリ参照・実投入履歴のノード/固定入力/6項目差分・同じ動画検査を確認する。長時間条件の途中観測を完了成功とは扱わず、チャット期限と ComfyUI 継続の対処も文書点検する。UI 操作は対象機の実ブラウザ/画面で確認し、新規公開サービス/STG は設けない。
AC-4 の応答は時刻と対応する Ollama `/v1/chat/completions` 要求ログで提供元を裏付ける。AC-12 はチャット前後の測定時刻・稼働モデル・約21GBの実測・システムメモリを記録し、262144は当該機既定、推奨は文脈抑制/モデル解放/同時生成1件からの確認として区別する。async は未検証として記録する。

## 検証記録の置き場所と形式

`doc/verification/issue-1-verification.md` に UTF-8 Markdown のテキストだけを置く。各レコードは `ID,FR/AC/D,成果物,要件節,Issue設計節,マスター節,日付/時刻,固定版/条件,開始状態,状態3区分,手順,期待/実際,終了コード,証跡,対処,未確認範囲` を持つ。
区分は「クリーン状態で検証／既存環境で検証／未検証」。クリーンは当該導入対象・取得途中データが無い開始状態。前後の状態、容量の件数/範囲/実測free/有効free/N/R/余裕を記録し、AC-3 欄に空き容量側だけを下げる方式への置換根拠を残す。動画は条件（prompt/seed含む）、経過時間、保存先、存在、両ストリーム属性、全デコード終了コードを記録する。
同一入力の再投入は ComfyUI のキャッシュで再生成せず完了しうるため、時間は「生成を伴った実行」の値を記録する。履歴は ComfyUI 再起動で消えるので verify は同じ起動中に行う。チャット6項目は履歴値を表示・記録し、グラフ照合の合否は構成/固定入力（動画検査は別途）とする。UDP は診断対象外の未確認範囲に残す。
2026-10-12 の対象機での生成時間は submit 節の3条件を README と対応づけて記録し、448×768・15秒は完了結果48分とする。チャットの900000msと submit の7200秒の違い、長い生成の指示文でタイムアウトを明示する方法、出力ディレクトリ/履歴での完了確認を記す。実機項目に「チャット生成後の register 再実行0・D-4 PASS」「利用者の pip 設定ファイルと git 設定に別取得元があっても install の接続先が変わらない」を追加し、新規スクリプト分は未検証（実装後に orchestrator が実施）の枠を作る。
Harness のセッション記録で確認済みのスモーク呼出しは `comfyui_workflow` の `action: run`。引数はライブラリの `id`・`parameters`（seed 以外の5項目）・`mode: sync`・`timeout_ms: 900000`。この事実と証跡、履歴の6項目を収録し、固定入力は登録項目と直接照合、登録項目と AC-6 のリポジトリグラフの一致も記録する。
実投入グラフ・サーバーログは元データで時刻/固定入力を照合してからホームや個人識別パスを `~` に置換したテキストを収録する。重み・動画・未加工秘密ログは収録しない。リポジトリ全体と PR/Issue 貼付予定テキストを同じ秘密/個人パス検索で点検し、公開ファイル一覧と結果を記す。
対処表は D の FAIL/UNKNOWN 全原因（入口相違・登録固定入力相違含む）、容量不足、未同意、依存競合/事後検査失敗、pip 期限超過時の途中変更と pip check、必要ライブラリ不在/hub版不足、同名別内容のパネル削除再登録、互換性拒否（出力・対象版・本人承諾・公式 `dsh plugin allow-version ... --accept-risk` 手動操作）、チャット期限/生成継続、async/メモリを含む。テスト/変異の件数・実結果・D-6 スキップとノード/プラグイン事前確認の観点/版/日付/未確認範囲を記録し、未マージ修正を解消済みとしない。
対象機の提供された実測は ffmpeg 7.1.1（Homebrew）、ffprobe の版は未確認。実装担当は実サービス・動画ツールの実機コマンドを実行せず、新規スクリプト分は orchestrator が確認する。キャッシュ・生成物の追加容量も実測前に保証しない。テスト用一時領域は tempfile で管理し、確認後に今回作った領域のみ削除・不在確認して記録する。

## マスター設計書の構成

実装フェーズで `doc/design/master/architecture.md`（構成・責務・データフロー・対応版）、`operations.md`（CLI・manifest/workflow/設定形式・配置・診断・期限/容量・検証手順）、`security.md`（信頼境界・URL/パス/コマンド・秘密・非変更・残余リスク）を作る。
確定した現在の事実だけを現在形で記し、Issue番号・経緯・却下案は本書へ置く。全成果物/FR/ACの参照を検証記録から両層へ結び、実装差分と同じ単位でマスターを更新する。本段階ではマスターを作成しない。DB は無いので db-schema は不要。

## 却下した代替案

- シェル主体・スクリプト用ライブラリの追加導入：JSON/パス/秘密の扱いとテストを単純化するため venv の標準ライブラリを使い、download だけ既存 hub、check だけ既存 PyYAML を要求する。
- 可変 main/latest と一覧の都度取得：再現条件・判定基準が変わるため固定 SHA とレビュー済み一覧にする。
- 固定150GBゲート、必要量の上書き・実測より高い free 注入：残量と `min(実測,N)` を使い容量ゲートを緩めない。全完了は同意・容量要求・再取得なしで0。
- 自動 resume/サイズ修復/同名登録更新・同名の無条件成功：途中・不一致は非変更5。同名は workflow/parameters の id 以外を比較し同内容0/別内容5、本人のパネル削除後に再登録する。
- オフライン依存導入・既存依存更新・constraints・任意 index/利用者設定：isolated/明示 PyPI/子の設定隔離、事前計画拒否・事後版不変/pip check を使う。期限超過は途中変更案内で7。
- HF 標準転送への独自制限：対象機で未検証の配布ホスト制限・リダイレクト検査は採用せず、固定 endpoint/revision・トークン非送信・取得後サイズ照合を使う。
- 自前 YAML 読取・設定用環境変数での上書き：既存 PyYAML の安全なローダーと CLI 引数に統一し、独自の構文制限と設定消費者の増加を避ける。
- profile/env の自動適用、互換性例外の自動承諾：既存設定保護と明示承諾に反するため手順書だけにする。
- ffmpeg の Cellar パス・register/submit の個別上書き・PATH だけの診断：ワークフローファイルの固定入力を唯一の出どころにし、D-4 は登録項目も検査、動画ツールは同じ入力から導出する。
- プロセス名だけの ComfyUI/Ollama 同定・plugin/profile 探索：URL ポートの持ち主と実使用 profile の固定先を検査し、別環境を診断して正常扱いする食い違いを防ぐ。
- プラグイン公開6項目を認可境界とみなす案：任意投入を遮断できないため標準経路の契約と残余リスクを別々に記す。
- 成功応答/ファイル存在だけで生成合格、動画バイト一致：再生検査不足/要件外のため両ストリーム・解像度・全デコードを判定にする。
