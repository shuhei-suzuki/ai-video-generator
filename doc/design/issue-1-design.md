# Issue #1 設計：ローカル動画生成環境の再現

## 概要

入力は `doc/requirements/issue-1-requirements.md` 全文と orchestrator の決定。macOS 26・Apple Silicon・128GB、Comfy Desktop 1.1.6（ComfyUI 0.39.2）、Ollama 0.33.3、Harness 0.2.0-rc.2、dsh-comfyui 0.5.4 を対象とする。
本書は実装の決定記録であり、全設計の実機検証済みという宣言ではない。参考試作の上限値・直接上書き・固定個人パスは採用しない。すべてのスクリプトは ComfyUI 仮想環境の Python 3.11 以上で実行し、標準ライブラリ＋同環境に既にある `huggingface_hub`・PyYAML のみを用いる。両ライブラリの未導入時は理由を表示して1で終了し、スクリプトのための追加導入はしない。POSIX シェルは README の起動例だけに留める。
利用者が Desktop・Ollama・Harness・ffmpeg・Qwen・プラグインを手動導入し、初回 GUI 起動、設定追記、互換性例外を承諾する。スクリプトはノード導入→同意付きモデル取得→登録→診断→直接生成を担当する。チャット生成は登録ライブラリを同期実行する。
Multi-Tenant Access Control：適用外（理由）：ローカル単一利用者向けのスクリプト群であり、テナント・認可の概念が無い。

### FR / AC / D と設計要素の対応

| 要件 | 受け入れ条件 | 診断 | 設計要素・検証 |
| --- | --- | --- | --- |
| FR-1 | AC-1 | — | README の構成・容量・配置・境界・順序、生成時間・チャット期限、実測記録への参照 |
| FR-2 | AC-2 | — | README の原文・確認日・制限、download の3モデル共通同意ゲート |
| FR-3 | AC-3 | D-3 | install の PyPI 導入計画・既存版保持、manifest、共通状態判定、残量・空き容量判定、標準 hub 取得・Turbo 再実行 |
| FR-4 | AC-4 | D-5〜D-7 | 設定例・手動例外、応答時刻と Ollama 要求ログの照合 |
| FR-5 | AC-5 | D-1〜D-9 | check_env の独立診断、D-6 の安全な YAML 読取、項目ごとの故障注入と実機正常系 |
| FR-6 | AC-6、AC-11 | D-1〜D-4 | API グラフ、submit の完了待ち・動画検査、直接2条件 |
| FR-7 | AC-7 | D-1〜D-7 | register の公開6項目、comfyui_workflow の同期呼出し証跡、実投入履歴の固定入力照合、チャット動画検査 |
| FR-8 | AC-8 | D-1〜D-9 | verification の成果物対応・状態3区分・証跡・全対処一覧 |
| 公開物の安全性 | AC-9 | — | 秘密・個人パスの文字列点検、公開ファイル一覧で重み不在確認 |
| 信頼境界・残余リスク | AC-10 | D-8、D-9 | URL 制限・待受検査、任意投入と ffmpeg_path の注意 |
| メモリ | AC-12 | — | README の併用指針、チャット前後の時刻付き実測 |

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
| `scripts/register_dsh_workflow.py` | 既存項目を保持したライブラリ追加・同名時の無変更成功 |
| `tests/test_*.py` | unittest、スタブ HTTP・コマンド・一時ディレクトリによる故障注入 |
| `doc/requirements/issue-1-requirements.md`、本書 | 既存要件は変更せず参照。本書は決定の履歴 |
| `doc/verification/issue-1-verification.md` | AC・D ごとの公開可能なテキスト検証記録 |
| `doc/design/master/{architecture,operations,security}.md` | 実装時に作る現在の正（後述） |

## 各スクリプトの仕様

### 共通 CLI・入出力・終了コード

パスの優先順位は明示 CLI 引数→Desktop 1.1.6 の既定配置。設定の上書きは CLI 引数だけとし、設定用の環境変数は設けない。`Path.home()` と `expanduser()` で実行時解決し、存在・実行可否・仮想環境を検査する。推測で別インスタンスを選ばず不明なら停止する。リポジトリ資材は `__file__` 起点で解決する。
既定インスタンスは `~/ComfyUI-Installs/ComfyUI`、本体は `<instance>/ComfyUI`、venv は `<instance>/.venv`。共有モデルは `~/ComfyUI-Shared/models/minimax_h3`、出力は `~/ComfyUI-Shared/output`。明示された共有モデルルートのリンクは入口として解決し、その実体を包含検査の基準にする。
共通指定は `--instance`、`--comfy-root`、`--venv`、`--models-dir`、`--output-dir`、`--manifest`、`--workflow`、`--ffmpeg`、`--ffprobe`。各 CLI は責務に必要なものだけを受ける。ffmpeg/ffprobe 既定値は `/opt/homebrew/bin/{ffmpeg,ffprobe}`。`--help` に既定値と上書き元を示す。
終了コードは 0=成功（完了済み・同名含む）、1=失敗または確認不能、2=引数・入力形式不正、3=未同意、4=容量不足、5=既存データとの競合（取得途中・サイズ不一致・別版・既存パッケージの入れ替え計画）、6=外部処理・API の失敗、7=期限超過、8=動画検査不合格。check_env は有効な引数で1項目でも異常なら1、全正常なら0。
stdout は対象・状態・集計・ID・保存先・検査結果、stderr は `項目/処理名: 原因分類; 対処`。HTTP 本文・env 値・profile 全文・未加工例外は表示しない。ログのホームは `~` にするが、実際の通信・コマンドには解決済みパスを使う。
HTTP 1要求30秒、診断1要求5秒、ポーリング2秒、生成全体7200秒、git/pip 各1800秒、動画検査各300秒を既定とする。`--http-timeout`、`--timeout`、`--poll-interval`、`--command-timeout` で対象の期限を正の有限値に上書きできる。期限は monotonic 時計、1要求も残り全体期限以下とする。

### install_h3_node.py

引数：共通配置・実行ファイル指定、`--git`（PATH から絶対パス解決）。入力：固定 GitHub ノード、同コミットの requirements、venv の導入済み配布物。出力：custom_nodes の対象1ディレクトリ、新規依存、補助リンク、前後のパッケージ差分。
変更前に対象ノード・venv・モデルリンクの競合と書込権限を全件確認し、ComfyUI を停止する手順を示す。固定コミット `ab1756d571ebb14fed3168354dae42966a04348b` を一時領域に取得し HEAD を照合する。既存対象は同コミット・clean のとき再利用し、別版・未追跡変更・非 Git は5で中止。ほかの custom_nodes は操作しない。
導入前に requirements の URL・VCS・追加 index・他ファイル参照の行を拒否して2で停止する。固定コミットの requirements は名前と版指定だけであることを確認済み。venv の Python で `-m pip list --format=json` により事前の名前・版を保存し、`-m pip install --dry-run --report <一時ファイル> -r requirements.txt` で計画を得る。正規化した名前が事前の集合に含まれる配布物が install 対象なら、同版も含め入れ替え計画として差分を表示し、何も変更せず5で停止する。計画取得の外部処理失敗は6、計画形式が読めず判断不能なら変更前に1。
入れ替えが無ければ同じ requirements で `-m pip install -r requirements.txt` を実行する。外部接続先は pip 既定の PyPI（`pypi.org`・`files.pythonhosted.org`）。事後に `-m pip check` と事前に存在した配布物の名前・版の不変を検査し、失敗・相違時は6で停止して差分を記録する（自動削除・巻き戻しなし）。対象機ではこの固定 requirements の PyPI 導入で既存パッケージの更新・ダウングレードが起きなかった。計画・前後差分・検査結果を検証記録に残す。
成功後にノードを配置する。venv/bin の ffmpeg・ffprobe は `lexists` で未配置時だけリンク作成し、既存ファイル・リンク・切れたリンクは状態表示して続行。instance の `models/minimax_h3` は共有モデルへのリンクを新設し、既存が同じ実体なら保持、異なる実体なら5で中止。失敗時は工程・安全な再実行方法を表示し、今回だけの未配置一時領域を片付ける。

### download_h3_models.py

引数：`--models base int8 turbo`（既定は3種全部、部分選択可）、`--models-dir`、`--manifest`、`--accept-license`、`--test-free-bytes N`。Python と既存ライブラリの前提は共通仕様に従う。入出力：manifest と現状→選択モデルの不足ファイル・hub メタデータ、対象/リビジョン/一覧/配置先/状態/必要量/空き容量の表示。
ネットワーク前にライセンス原文の固定リビジョン参照、2026-10-12 の確認日、非正本要約、米国・EU・英国・韓国の利用対象外、年商2,000万USD超の別途許諾、派生2モデルにも H3 条件が及ぶ前提を表示する。TTY の明示 `yes` または `--accept-license` のみ同意。EOF・非TTY・拒否は3、環境変数で同意を代替しない。各選択モデルを同意対象に含める。
共通判定はファイル単位で「完了=通常ファイルかつサイズ一致」「未取得=不存在」「取得途中=サイズが一覧より小さい、またはモデルの `.cache/huggingface/download/` 内の `.incomplete`」「サイズ不一致=大きいサイズ」。型不正・読取不能・逸脱は異常として拒否する。
一覧外のファイルは非変更で許容するが `.incomplete` は必須ファイルの一致より優先して取得途中と判定する。選択集合を全件事前走査し、取得途中・不一致が1つでもあれば全取得を開始せず5。利用者が自分で退避する対処だけを示し、resume・repair・force を提供しない。
残量 R は未取得ファイルの size 合計（Qwen を含めない）。R>0 の必要空き容量は `R + max(1 GiB, ceil(R×0.05))`。配置先の最寄り既存親から同一ボリュームの free を測り、配置先作成後にも再確認する。R=0 は容量要求・hub 呼び出しなしで0。GB と GiB・整数バイトを区別して表示する。
`--test-free-bytes` は容量不足検証専用であり、上書きするのは free の側だけ。必要量は常に manifest と現状から算出・表示し、「検証用空き容量」と記録する。AC-3 の必要量上書きという文言は今回の orchestrator 指示でこの方式に置き換える。
未取得ファイルだけ `hf_hub_download(repo_id, filename, revision=固定SHA, local_dir=..., token=False)` をそのまま使って順に取得する。対象機で成功した標準の転送経路を使い、配布ホストの許可リスト・リダイレクト検査を独自実装しない。各取得直前にも存在・逸脱・空きを再確認し、既存ファイルの上書きをしない。通信失敗は6、今回生じた途中データを削除せず表示する。取得後の全選択対象を再判定しサイズ一致時だけ0。存在とサイズの一致は暗号学的な完全性保証ではない。

### check_env.py

引数：共通資材指定、`--comfy-url`、`--ollama-url`、`--profile-dir`、`--env-file`、`--plugin-dir`、`--comfy-process`、`--ollama-process`、`--harness-process`、`--lsof`、`--ps`。URL・ディレクトリ・プロセス名を個別に差し替えて故障注入する。読み取り専用で最後まで診断し、`D-n PASS/FAIL/UNKNOWN: 原因; 対処` を各行表示する。

| ID | 確認方法・失敗時の表示と対処 |
| --- | --- |
| D-1 | `GET /system_stats` の成功・期待 JSON。無応答/不正応答→API 起動・指定 URL 確認 |
| D-2 | `GET /object_info` で要件の4ノードを各々確認。欠落名を表示→ノード導入・再起動 |
| D-3 | 3モデル全部を download と同じ一覧・状態判定。欠落/サイズ/途中/読取不能を表示→不足取得または本人による退避 |
| D-4 | 実効グラフの保存ノードの ffmpeg_path が絶対パス・通常ファイル・実行可。不存在/不可→本体導入・`--ffmpeg` 見直し |
| D-5 | Ollama `GET /api/tags` で API 応答と `qwen3.8:27b-mlx`。不在→手動 pull、無応答→起動 |
| D-6 | desktop profile の llm-pi-ai/agent-default-model、ollama URL/API/model/apiKeyEnv の整合と env 内対象キーの非空存在。欠落/曖昧/未解決→既存設定を保持して手動追記 |
| D-7 | 導入先 package.json の name=`dsh-comfyui`・version=`0.5.4`。未導入/別版→手動導入、例外は承諾後のみ |
| D-8 | ps で ComfyUI/Ollama の PID と子を特定し、lsof の全 TCP LISTEN を解析。外部待受→ループバック設定、無出力/権限不足/不明→確認不能 |
| D-9 | Harness 本体・子プロセスが存在し、全動的待受も lsof でループバックのみ。未起動/待受無し/不明→起動して再診断 |

D-6 は ComfyUI 仮想環境の PyYAML の `yaml.safe_load` 相当を使う。SafeLoader を基に、未知のタグ（`!!js` など）は値を解釈せず不透明な値として読むローダーとし、任意オブジェクトを生成するローダーは使わない。安全に読める通常の YAML 構文を独自に制限しない。対象外 id は読み飛ばし、読取不能・想定外の構造・対象設定の重複や曖昧さ・確認対象が不透明な値なら UNKNOWN、推測で PASS にしない。env は行ごとにキー名（任意の export 接頭辞対応）を先に判定し、対象キーだけ引用を除いた非空判定、他の値は分割・保持せず全値を非表示。空の引用値・対象キー重複・展開が必要な値は解決済みとしない。source/eval・シェル展開はしない。
profile 既定は `~/.dsh/profiles/desktop`、env は `~/.dsh/.env`。plugin-dir は `~/.dsh` 内の導入領域から name 一致の package.json を探索し、一意に導入を確定できなければ UNKNOWN として明示指定を案内する。検索対象・実機配置は検証記録に残す。
ps の完全なプロセス名/argv で対象を識別し、正規表現や部分一致だけで全待受を決めない。lsof は `-nP -a -p <PID集合> -iTCP -sTCP:LISTEN -F...` の機械形式を解析し、IPv4/IPv6 の実アドレスを検査する。`*`・`0.0.0.0`・`::`・LAN アドレスは FAIL、127/8 と `::1` だけ PASS。各サービスの確認不能も非ゼロとする。

### submit_h3.py

引数：`--prompt`、`--width`、`--height`、`--seconds`、`--steps`、`--seed` の公開6項目、共通 workflow/output/ffmpeg/ffprobe、`--comfy-url`、期限指定。後者は利用者の運用設定であり LLM 公開パラメータではない。モデルパス・保存先 prefix をグラフ編集引数として提供しない。`--no-wait` は提供しない。
入力：検証済み API グラフと6項目。出力：prompt_id、生成条件、経過時間、実投入グラフの照合結果、保存先・存在・ストリーム・デコード判定。スモーク既定は64×64・1秒・steps=5・seed=0、プロンプトはシーンと音の固定例。幅/高さは正の32倍数、秒数は正の有限数、steps は2以上の整数、seed は非負整数、prompt は非空文字列。上限を新設せず大きい値の費用・メモリを案内する。
固定グラフを複製し Generate ノードの6フィールドだけ置換、ffmpeg の運用指定がある場合だけ Save ノードを置換。構成・固定入力を検証して `POST /prompt`、node_errors/拒否は6。`GET /history/<prompt_id>` で対象 ID の error は6、completed を期限内で待ち、未完了は7（サーバーのジョブを自動停止・再投入しない）。
履歴の実投入グラフを照合し、Save ノードの出力 filename/subfolder/type=output を検証して output-dir 内の通常動画へ解決する。絶対パス・`..`・リンク逸脱・不明な出力構造・動画不在を拒否する。stdout の文字列を保存先とは見なさない。
ffprobe の JSON で H.264 映像と AAC 音声の両ストリーム・要求解像度を検査、ffmpeg `-v error -xerror -i <絶対動画パス> -map 0:v:0 -map 0:a:0 -f null -` で全フレームをデコードし非ゼロ/エラーは8。検査期限超過は7。秒数と実測フレーム数の一致を合否にしない。
チャット動画の同じ検査には `--verify-history ID` を用意し、新規投入せず履歴のグラフ・出力を検査する。公開6項目と運用指定を反映した期待グラフと照合し、シードをランダム化した場合は履歴の値を明示して検査・記録する。
README と検証記録に、2026-10-12 の対象機での目安として64×64・1秒・steps=5は約1分、768×448・5秒・steps=9は約10〜14分、448×768・15秒・steps=9は1ステップ3〜5分・合計40分前後を載せる。最後の条件は実行中の観測であり、完了後の値は検証記録で確定する。生成全体の既定期限は7200秒を維持する。
チャット同期実行ではエージェントが `timeout_ms: 900000`（15分）で呼んだため、長い生成はチャット側が先にタイムアウトしうる。その場合も ComfyUI 側の生成は継続する。長い生成では指示文でタイムアウトを明示し、完了は出力ディレクトリか実行履歴で確認する対処を README と検証記録に載せる。

### register_dsh_workflow.py

引数：`--workflow`、`--data-dir`（既定 `~/.dsh/data/dsh-comfyui`）、`--ffmpeg`。入力：API グラフと workflows.json、出力：名前 `minimax-h3-t2v` の1項目追加、または同名時の「変更なし」。公開6項目の既定値はグラフのスモーク値から生成し、上限 max は付けない。
JSON 不正・リスト以外・不正な既存項目は変更せず2。同名が存在すれば既存ファイルをバイト単位で保持して0。ほかの項目の値・未知フィールド・順序を保持し、新規項目だけ追加する。登録時は Harness を終了し他ライブラリ書き手を止める手順を README に明記する。
既存ファイルのリンクを拒否し、権限を保持した同一ディレクトリの一時ファイルへ UTF-8 JSON を書き、flush/fsync→元の stat と内容再確認→`os.replace`→親ディレクトリ fsync。新規は0600。途中エラー・元の変化は非ゼロで原本を保持し、一時ファイルを除去。協調しない他プロセスとの同時更新を保証しないため停止前提を省略しない。

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
Loader 固定入力は low_memory/stream_blocks=true、group=2、memory_limit_gb=32、memory_pressure_guard/load_vision=false、LoRA scale=1/alpha=0、sigma shifts=0、dense_dequant_profile=off。Generate 固定入力は drop_adaln=true、block_cache/cache_text_conditioning=false、threshold=0.12/depth=0.75/max_consecutive=2。Save 固定入力は filename_prefix=`minimax_h3/ComfyUI`、crf=18、ffmpeg_path=`/opt/homebrew/bin/ffmpeg`（Cellar 版番号パスを埋め込まない）。
ライブラリ項目は `id,name,description,workflow,parameters,tags,updatedAt`。parameters は各々 `id,name,label,type,nodeId,inputKey,default` と numberKind/min/step または seed の random を持つ。name/inputKey 集合は prompt,width,height,duration_seconds,steps,seed と完全一致、nodeId=`2`。モデル/ffmpeg/保存先は固定値で公開しない。
設定例は YAML の `id: llm-pi-ai`→`config.providers.ollama` に `api: openai-completions`、`baseURL: http://127.0.0.1:11434/v1`、`apiKeyEnv: OLLAMA_API_KEY`、model id=`qwen3.8:27b-mlx`、contextWindow=65536、maxTokens=8192、input=[text,image]。`id: agent-default-model` に provider=ollama/model 同上。`.env` 例はダミー1行。適用は利用者が既存項目を保持して追記し、スクリプトで YAML を再保存しない。

## 安全性設計（信頼境界・入力検証・外部コマンド・外部 URL・秘密情報）

信頼するのは本人の配置先・venv・運用指定と事前確認した固定ノード。manifest、HTTP 応答、履歴、既存 JSON は入力として型・構造を検証する。ノードと依存は実行コードであり固定版だけで安全とは扱わず、実装前に読み込み・外部処理・配布条件を確認し、日付・版・観点・未確認範囲を記録する。
manifest の path/local_dir は絶対パス、空要素、`.`/`..`、NUL、バックスラッシュを拒否し、resolve 後もモデルルート内かを Path の包含判定で確認する。配下のリンクは cache を含め拒否して、読み書き直前にも再検査する。FIFO/デバイスも拒否する。同時のディレクトリ差し替えは信頼する単一利用者の運用外とし、複数取得を禁止して検査と使用の間の競合を抑える。
JSON は重複キー・非有限数・不正型を拒否、HTTP JSON は16MiB、profile/env は各4MiB、その他設定 JSON は16MiBを上限にする。プロンプトはデータとして JSON 化し、コマンドや YAML に埋め込まない。検証前の副作用を避け、ファイル出力先は profile/env と重なる指定を拒否する。
外部コマンドは subprocess の引数リスト・shell=False、実行ファイルは絶対パス・通常ファイル・実行可を検査。全スクリプトの Python は ComfyUI venv、git/ps/lsof は指定または PATH 解決、ffmpeg は固定入力と同じ実行物を使う。argv の固定オプションと絶対ファイル operand を分ける。親環境から読むのは HOME と必要最小限の PATH・locale だけとし、子にもこの最小環境だけを渡す。秘密・proxy・任意 Git/pip 設定の環境変数を継承しない。管理者権限・hook 無効化・シェル設定変更をしない。
ComfyUI/Ollama は `http` または `https`、host は IP リテラルの127/8または `::1` のみ（localhost は使わず DNS を避ける）、port は1〜65535。userinfo/query/fragment を拒否、ComfyUI は空/root パス、Ollama は空/root または `/v1` のみ。proxy と redirect は使わずループバック別ポートを許す。
外部接続は固定 GitHub repo（`github.com`）、固定 HF repo の標準転送経路、pip 既定の PyPI（`pypi.org`・`files.pythonhosted.org`）を使い、TLS を検証する。HF API/取得のエンドポイントは `https://huggingface.co` に固定し、`HF_ENDPOINT` を継承しない。標準 hub クライアントの配布経路に独自のホスト許可リストやリダイレクト検査を追加しない。
hub の初期化前に隔離した実行環境で暗黙トークンを無効に固定し、取得には `token=False` を指定する。manifest 再生成の HF API にもトークンを送らない。固定リビジョンと取得後のサイズ照合を用いるが、存在・サイズ一致は暗号学的な完全性保証ではない。D-6 は対象キーの非空存在だけを見る。どの値も表示・変更せず、対象外の値を取得しない。設定例に実キーを入れない。
`~/.dsh` の永続書込みは workflows.json だけ。全 CLI の実体解決済み書込先にこの制限を適用し、register の許可先以外は引数による迂回も拒否する。原子的置換に必要な同じ親の一時ファイルは成功/失敗とも残さない。`--data-dir` が `~/.dsh` 内なら指定ライブラリの親だけを許し、profile/env 配下を拒否する。外の検証用一時配置先は許可する。既存 JSON の破損・非リスト時は原本非変更で停止する。
標準経路の6項目制限は `comfyui_run` の任意投入を遮断しない。ffmpeg_path は任意実行物を受け得るため、README に外部公開禁止、未調査のツール承認/無効化は利用者判断、第三者の文章・ファイルをそのまま実行させない注意を記す。

## 影響範囲分析

変更対象は新規追加のみ。既存コード・API 契約・DB は無く、既存要件は読み取りだけ。調査時のファイル一覧は要件書のみで既存呼び出し元なし（行番号を持つ既存コード参照は該当なし）。新設共通モジュールの消費者は上記6 CLI と tests。実装時に定数・env・一覧・パスの全参照を rg で再確認する。

| 実行時の利用者環境 | 誰が読むか／触るか・影響・対応 |
| --- | --- |
| ComfyUI custom_nodes の対象ディレクトリ | install が新設/同版確認、check D-2 が API 経由で確認。固定版競合は停止 |
| ComfyUI venv と bin | 全スクリプトが同環境の Python/hub/PyYAML を使用。install が PyPI 新規依存・補助リンク、D-6 が PyYAML、submit が動画ツール使用。導入計画・事後検査による既存版保持、既存リンク保持で互換性保護 |
| 共有 models と instance の models リンク | install がリンク新設、download が未取得分/cache 作成、D-3 が全件読取。大容量・帯域影響は残量計算/部分選択、既存データ非変更 |
| ComfyUI output | サーバーが動画保存、submit が履歴と動画読取・デコード。生成/検査の時間・GPU/メモリ/追加容量を記録 |
| `~/.dsh/data/dsh-comfyui/workflows.json` | register が保持追加/原子置換、Harness が読取・実行。停止前提・同名無変更で既存項目保護 |
| Harness profile・`~/.dsh/.env` | D-6 が安全な YAML ローダーで必要設定を読み、env の対象キー存在だけ確認。未知タグは不透明、読取不能/構造不正は UNKNOWN。書換え禁止、設定例適用は本人の手作業 |
| シェル設定・他のカスタムノード | 全スクリプトで書込みなし。対象外ディレクトリの非変更を回帰検証 |

| 定数・閾値・入力 | 誰が読むか／変更時の波及 |
| --- | --- |
| ノード SHA、モデル3 SHA、repo/include/local_dir | install、make_manifest、download、D-3、README、tests。更新は一覧再生成と全消費者照合が必要 |
| 固定 requirements・pip 導入計画・HF endpoint/トークン非送信 | install の事前/事後検査、download/make_manifest の接続、tests、README/verification。既存版保持・標準転送・上書き設定の非継承を照合 |
| ポート8188/11434、URL規則、動的 Harness 待受 | check、submit、設定例、tests。別ポート正常系と非ループバック拒否を双方検証 |
| Desktop/共有パス、bin、ffmpeg 固定入力、dsh ライブラリパス | 全 CLI、API グラフ、設定例、README、tests。登録/投入/D-4 を同じ実効パスに揃える |
| 各タイムアウト・ポーリング間隔 | 共通 HTTP/command、check、submit、download の転送、make_manifest、期限テスト。submit の7200秒とチャット呼出しの900000msを区別し、生成時間の目安・継続確認を README/verification に記録 |
| 容量余裕1GiB/5%、150GB暫定目安 | download と容量テスト、README/verification。R=0 と選択残量だけの判定を維持 |
| 必須ファイル一覧136件（base66/int8 13/turbo57） | make_manifest が生成、download/D-3 が読む、tests が欠落/件数/合計/余分/途中を検査、設計/README が参照 |
| 公開6項目・固定3ノード・4登録ノード・ライブラリ名 | 共通グラフ、submit/register/D-2/D-4、Harness、履歴照合、tests。集合完全一致を検証 |

スクリプトが親環境から読む変数は次の最小限だけで、値を記録しない。配置・URL・実行物・入力ファイル・プロセス名の上書きは CLI 引数だけを全消費者で使う。

| 環境変数 | 誰が読むか |
| --- | --- |
| `HOME` | 共通 resolver のホーム解決。子にも渡す |
| `PATH` | git/ps/lsof の実行物探索と子プロセス用の最小経路 |
| locale（`LANG`・必要な `LC_*`） | 子プロセスの文字コード・表示制御に必要な分だけ渡す |

入力データ一覧は manifest 全件、API グラフ、profile、env ファイルの対象キー名、plugin package.json、workflows.json、HTTP 履歴/タグ/object_info、ps/lsof 出力、固定 requirements、pip 導入計画・前後の配布物一覧。各読者は上記仕様と対応する。`OLLAMA_API_KEY` は Harness 用設定であり、D-6 は env ファイル内の存在だけを確認し、プロセス環境から読まない。hub のエンドポイント・暗黙トークン無効化は内部の固定設定で、利用者の上書き入力ではない。必要設定以外のデータは読み出し/出力を増やさず、版ずれ自動検出や他アプリ移行は別スコープとする。

## テスト方針（故障注入の方法と AC の対応、変異検証の対象）

unittest と tempfile、ThreadingHTTPServer（127.0.0.1 の空きポート）、mock した subprocess/hub/disk_usage を使用。実サービス・大容量取得・生成は単体/統合テストの前提にしない。副作用を呼び出し記録とファイル内容/hash/mtime で検査し、拒否と正常系を対にする。
実行は ComfyUI venv を原則とする。PyYAML が無いテスト環境では D-6 関連をスキップ理由付きでスキップし、合格に数えない。実機 D-6 正常系は同 venv の PyYAML で別途必須とする。

| 対応 AC / D | 故障注入・合否 |
| --- | --- |
| AC-2 | base/int8/turbo 各々で EOF/拒否/非TTY と yes/flag。未同意は通信0件、同意後のみ取得呼出し |
| AC-3 / D-3 | 小サイズ manifest と各モデル別の欠落/過小/過大/incomplete（余分な途中も）/通常余分を一時配置。非変更・表示・終了コードと download/D-3 の一致 |
| AC-3 | R と余裕の境界 free=必要量-1/同値、検証専用 free 指定、別配置先ボリューム、全完了時 free=0。必要量が fixture 都合で変更されないこと |
| AC-3 | pip report に既存名（同版/更新/ダウングレード）を含む計画→差分表示・5・変更0件、URL/VCS/追加 index/他ファイル参照→導入前拒否。新規だけの計画→同じ requirements で導入・pip check・既存名/版保持検査。pip 失敗/事後版変化、既存/切れた bin リンク、異なるモデルリンクと既存ノード/profile/env/シェル設定の内容保持 |
| AC-5 / D-1,D-2,D-5 | 無応答/壊れた JSON/4ノード各欠落/Qwen 不在を HTTP スタブで個別注入。該当項目の原因と非ゼロ |
| AC-5 / D-4,D-6,D-7 | 不在/実行不可 ffmpeg、profile 欠落/不正/曖昧/想定外構造、対象キー無し/空、plugin 不在/別版。PyYAML の通常構文と未知タグ（対象外は不透明なまま、確認対象なら UNKNOWN）を検査し、任意オブジェクト生成が無いことを確認。env の全キーに目印値を置き、stdout/stderr に全目印が無くファイル非変更 |
| AC-5,AC-10 / D-8,D-9 | ps/lsof スタブで各サービスの `*`/0.0.0.0/::/LAN、混在、非ゼロ/無出力/解析不能、Harness 未起動。正常IPv4/IPv6と子の外部待受も検査 |
| AC-6 | POST 拒否/node_errors、history 実行エラー/未完了期限/完了だが不在動画。ffprobe 音声無し/異 codec/異解像度、ffmpeg デコード失敗を別々に注入 |
| AC-7 | 不正/非リストライブラリ、同名/別項目/未知フィールド、書込失敗/原本変化。公開集合・スモーク値・既存項目保持・同名バイト不変 |
| AC-9,AC-10 | パス逸脱/リンク、ローカル API の URL userinfo/非ループバックhost/redirect、秘密目印の応答、特殊文字プロンプト。拒否時の通信・外部実行0件と正常入力の成功。hub は固定 endpoint/revision・token=False・暗黙トークン無効と標準取得呼出しを検査し、親の endpoint/トークン設定を継承しないことを確認 |
| 共通 CLI | 明示引数と既定値の優先順位、親環境に任意の設定値があっても配置/URL/実行物を変更しないこと、全スクリプトの venv 前提・既存ライブラリ不在時の理由表示と終了を検査 |
| AC-1,AC-4,AC-8,AC-12 | README/設定例/対応表/対処/実測の文書点検。実機必須の結果をスタブ成功で代替しない |

変異検証は一時コピーの実装を1箇所ずつ変更し、同意削除、SHA照合削除、サイズ比較反転、incomplete 無視、R=0 容量要求、容量不等号反転、pip の入れ替え計画拒否/事後版検査削除、パス包含/ローカル API の URL 制限/HF endpoint 固定削除、D の集約を常時0、キー値出力、待受を部分的に許可、公開入力に固定入力追加、JSON 非リスト上書き、AAC/解像度/デコード検査削除を対象とする。各々の意図したテストが失敗することを記録し、単なる構文エラーを検出成功に数えない。
実機は固定 requirements の PyPI 導入・既存版不変・pip check、Turbo の標準転送による空の一時配置先への取得→同条件2回目、D-1〜D-9 全正常、直接スモークと768×448・5秒・steps=9・seed42、チャット同期スモークを確認する。チャットはツール名/引数・ライブラリ参照・実投入履歴のノード/固定入力/6項目差分・同じ動画検査を確認する。長時間条件の途中観測を完了成功とは扱わず、チャット期限と ComfyUI 継続の対処も文書点検する。UI 操作は対象機の実ブラウザ/画面で確認し、新規公開サービス/STG は設けない。
AC-4 の応答は時刻と対応する Ollama `/v1/chat/completions` 要求ログで提供元を裏付ける。AC-12 はチャット前後の測定時刻・稼働モデル・約21GBの実測・システムメモリを記録し、262144は当該機既定、推奨は文脈抑制/モデル解放/同時生成1件からの確認として区別する。async は未検証として記録する。

## 検証記録の置き場所と形式

`doc/verification/issue-1-verification.md` に UTF-8 Markdown のテキストだけを置く。各レコードは `ID,FR/AC/D,成果物,要件節,Issue設計節,マスター節,日付/時刻,固定版/条件,開始状態,状態3区分,手順,期待/実際,終了コード,証跡,対処,未確認範囲` を持つ。
区分は「クリーン状態で検証／既存環境で検証／未検証」。クリーンは当該導入対象・取得途中データが無い開始状態。実行の前後で状態を記す。容量は件数/範囲/整数バイト/free/R/余裕を記録し、実測と暫定目安を分ける。動画は条件（prompt/seed含む）、経過時間、保存先、存在、両ストリーム属性、全デコード終了コードを記録する。
2026-10-12 の対象機での生成時間は submit 節の3条件を README と対応づけて記録し、448×768・15秒の約40分は途中観測と明記して完了後に確定する。チャットの900000msと submit の7200秒の違い、長い生成の指示文でタイムアウトを明示する方法、出力ディレクトリ/履歴での完了確認を記す。
Harness のセッション記録で確認済みのスモーク呼出しは `comfyui_workflow` の `action: run`。引数はライブラリの `id`・`parameters`（公開6項目のうち seed 以外の5項目）・`mode: sync`・`timeout_ms: 900000` であり、グラフを直接指定する `comfyui_run` ではなかった。この事実と証跡を収録し、ランダム化された seed は実投入履歴で照合する。
実投入グラフ・サーバーログは元データで時刻/固定入力を照合してからホームや個人識別パスを `~` に置換したテキストを収録する。重み・動画・未加工秘密ログは収録しない。リポジトリ全体と PR/Issue 貼付予定テキストを同じ秘密/個人パス検索で点検し、公開ファイル一覧と結果を記す。
対処表は D-1〜D-9 の FAIL/UNKNOWN 全原因、容量不足、未同意、依存競合（入れ替え計画と事後検査失敗の差分）、既存 hub/PyYAML 不在、互換性拒否（拒否出力・対象完全一致版・利用者の承諾事実・公式 `dsh plugin allow-version ... --accept-risk` 手動操作）、チャット同期期限と生成継続、async 制約、メモリ逼迫を含む。上流未マージ修正を解消済みとしない。テスト/変異の対象・件数・実結果・D-6 スキップ理由と、ノード/プラグインの事前確認日・観点・版・未確認範囲を残す。
ffmpeg/ffprobe の対象版は実装時の `-version` 実測で確定して記録し、現在は未確定。キャッシュ・生成物の追加容量も実測前に保証しない。テスト用一時領域は作成パスを非公開で管理し、確認後に今回作った領域のみ削除・不在確認して記録する。

## マスター設計書の構成

実装フェーズで `doc/design/master/architecture.md`（構成・責務・データフロー・対応版）、`operations.md`（CLI・manifest/workflow/設定形式・配置・診断・期限/容量・検証手順）、`security.md`（信頼境界・URL/パス/コマンド・秘密・非変更・残余リスク）を作る。
確定した現在の事実だけを現在形で記し、Issue番号・経緯・却下案は本書へ置く。全成果物/FR/ACの参照を検証記録から両層へ結び、実装差分と同じ単位でマスターを更新する。本段階ではマスターを作成しない。DB は無いので db-schema は不要。

## 却下した代替案

- シェル主体・スクリプト用ライブラリの追加導入：JSON/パス/秘密の扱いとテストを単純化するため、ComfyUI venv の標準ライブラリ＋既存 hub/PyYAML を使う。
- 可変 main/latest と一覧の都度取得：再現条件・判定基準が変わるため固定 SHA とレビュー済み一覧にする。
- 固定150GBゲート、必要量のテスト上書き：再取得不要時や部分選択で誤拒否するため残量計算と free の注入にする。
- 自動 resume/サイズ修復/同名登録更新：取得途中・既存項目を破壊し得るため非変更拒否または同名成功とする。
- オフライン依存導入・pip による既存依存更新・任意 index 接続：対象機で検証できた既定 PyPI 導入に揃え、事前計画で既存配布物の入れ替えを拒否し、事後の版不変と pip check を確認する。
- HF 標準転送への独自制限：対象機で未検証の配布ホスト制限・リダイレクト検査は採用せず、固定 endpoint/revision・トークン非送信・取得後サイズ照合を使う。
- 自前 YAML 読取・設定用環境変数での上書き：既存 PyYAML の安全なローダーと CLI 引数に統一し、独自の構文制限と設定消費者の増加を避ける。
- profile/env の自動適用、互換性例外の自動承諾：既存設定保護と明示承諾に反するため手順書だけにする。
- ffmpeg の Cellar パス、PATH だけの診断：版更新/GUI PATH で壊れるため prefix 絶対パスを固定入力にする。
- プラグイン公開6項目を認可境界とみなす案：任意投入を遮断できないため標準経路の契約と残余リスクを別々に記す。
- 成功応答/ファイル存在だけで生成合格、動画バイト一致：再生検査不足/要件外のため両ストリーム・解像度・全デコードを判定にする。
