# 運用契約

## 配置と起動

インスタンスは ~/ComfyUI-Installs/ComfyUI、本体はその下の ComfyUI、venv は本体直下の .venv、モデルは ~/ComfyUI-Shared/models/minimax_h3、出力は ~/ComfyUI-Shared/output である。共通 resolver は CLI 明示指定を優先し、別インスタンスを推測しない。実行は venv/bin/python -I、Python 3.11以上であり、共通モジュールを importlib で明示ロードする。

手動導入・初回 GUI・ライセンス原文・例外承諾・Qwen pull・既存項目を保持する設定追記は README の手順で利用者本人が行う。スクリプトは管理者権限を要求しない。install は `<comfy-root>/custom_nodes` と `main.py` を事前に確認し、無ければ何も作らず1で初回 GUI 起動と --comfy-root を案内する。共有モデルディレクトリの作成（未存在時）と `<comfy-root>/models/minimax_h3` へのリンク作成を行い、既存の同実体は保持、別実体・切れたリンクは5で停止する。install の実行物指定は --venv と --git のみである。download の取得時だけ既存 hub>=1.0、check_env の YAML 診断だけ既存 PyYAML を使う。

## データ形式・非変更再実行

manifest は schema=1、base/int8/turbo 各1件で、固定 repo/revision/include/local_dir と files の相対POSIXパス・非負整数サイズ・total_bytes の合計を検査する。モデルは通常ファイルの存在とバイト一致で完了、欠落は未取得、過小サイズまたは cache/download の .incomplete は途中、過大サイズは不一致である。余分な通常ファイルを保持し、途中データは優先して拒否する。完了済みは再取得しない。同サイズ改変の完全性は保証しない。

未取得残量 R>0 の必要量は R+max(1GiB,ceil(R×5%))。最寄り既存親の配置先ボリュームで、作成前・後・各取得直前に空きを検査する。--test-free-bytes N は毎回 min(実測,N) を使う。R=0 は同意・容量・hub 読込なしで0。異常があれば同意前に5で原本を保持し、本人の退避後再実行を案内する。複数の同時取得は運用外である。model_summary はモデルごとの完了 N / 全 M 件と未完了ファイルを表示し、download/check_env/make_manifest の --verbose だけ全件を表示する。取得ループは1ファイル1行の取得 i/n・パス・サイズを表示し、容量表示は開始時と値の変化時だけ行う。容量検査は全確認地点で行う。

ライブラリは ~/.dsh/data/dsh-comfyui/workflows.json に置く。register は id / name / description / workflow / parameters / tags / updatedAt を追加する。id は UUID4、parameters の id も UUID4、既定値は prompt がグラフの値、width=768、height=448、duration_seconds=5.0、steps=9、seed=0（random）、max は設けない。workflow はリポジトリのグラフそのままであり、グラフと直接 submit のスモーク既定値は変えない。既存 workflow 全体・parameters の id 以外・description・tags を登録する内容と比較して同内容はバイト不変0、相違は差分所在を表示し非変更5。本人がパネルで削除して再登録する。未知フィールド・他項目・順序・既存権限を保持する。既存項目のキー名と id は json.dumps でエスケープして表示する。英語2000字以内の description は MLX on Apple Silicon のステレオ音声付き text-to-video、comfyui_workflow action: run へ id と parameters を渡す同期実行、英語の場面と音、32倍数の幅・高さ、横768×448/縦448×768、15秒までの運用目安、timeout_ms の上限3600000と5秒1800000/15秒3600000の指定、同時1本、出力の minimax_h3/、モデルパスと ffmpeg_path の保持を案内する。起動中は警告し同時更新を保証しない。同じ親の一時ファイルを fsync し原本の stat/内容を再確認して replace する。新規ファイルは0600である。

Harness は ~/.dsh/profiles/desktop/cordis.patch.yml の llm-pi-ai / agent-default-model と ~/.dsh/.env の OLLAMA_API_KEY を使う。API は openai-completions、baseURL は http://127.0.0.1:11434/v1、モデルは qwen3.8:27b-mlx、contextWindow=65536、maxTokens=8192、input=[text,image]。設定例は手動追記専用である。

## 診断と期限

| ID | 検査対象 |
| --- | --- |
| D-1 | /system_stats 応答 |
| D-2 | 4クラスの個別 /object_info |
| D-3 | 共通一覧の全件・途中判定とモデル入口の実体一致 |
| D-4 | リポジトリと登録 Save ffmpeg の絶対パス・実行可否・値一致。ffprobe 有無は補足 |
| D-5 | Ollama /api/tags と Qwen |
| D-6 | 指定 profile の必要設定・対象キーの非空存在（値非表示） |
| D-7 | 同じ profile の node_modules/dsh-comfyui/package.json の name と version=0.5.4 |
| D-8 | URL ポート所有 PID と同グループの子の全 TCP LISTEN |
| D-9 | 完全名 Harness と子・複数一致の和集合の全 TCP LISTEN |

未登録だけは D-4 でリポジトリを検査する。不正 JSON・非リスト・対象名重複は FAIL、verify は2であり未登録に代替しない。診断は最後まで PASS/FAIL/UNKNOWN を表示し、対処は FAIL/UNKNOWN にだけ付ける。一つでも FAIL/UNKNOWN なら1。ps/lsof の解析不能・持ち主不在・待受無しは UNKNOWN。UDP と CORS 設定は診断対象外である。

HTTP30秒（診断5秒）、poll2秒、生成全体7200秒、git/pip1800秒、動画検査各300秒を既定とする。指定は正の有限値である。生成中のHTTPは全体残り期限以下を使う。hub の個別大容量転送には全体期限を設けない。

## 保存・再生検査と生成条件

履歴の completed と実投入グラフを確認し、Save の minimax_h3_video の filename/subfolder/type=output から出力ルート内の通常 MP4 を解決する。両ストリーム H.264 / AAC、履歴の要求解像度、ffmpeg -nostdin -v error -xerror の全デコードを合否条件とする。フレーム数と指定秒数の一致は要求しない。ffmpeg は固定 Save 入力、ffprobe は同じディレクトリ由来であり、不在・実行不可の ffprobe は1、動画不合格は8、検査期限は7である。

チャットは mode=sync を標準とし、5秒なら timeout_ms=1800000、15秒なら3600000を指定する。dsh-comfyui 0.5.4 の timeout_ms は最小5000・上限3600000・既定900000である。既定900000では長い生成がチャット側で先にタイムアウトしうる。ComfyUI は継続するため再投入せず出力・履歴を確認する。履歴は同じ ComfyUI 起動中に検査する。verify-history の ID が履歴に無ければ待たずに2で、実行中・待機中の可能性（完了後に再実行）と再起動による履歴消失を案内する。再投入せず出力ディレクトリと ComfyUI の画面で状態を確認する。公開値の型不正は8で専用の原因を表示する。照合結果はリポジトリのワークフローと登録 id（または登録項目なし）を明示する。

実行時間・実機結果・開始状態・証跡・未確認範囲は [検証記録](../../verification/) を参照する。

メモリ併用を無条件保証せず、必要な文脈への削減・モデル解放・同時生成1件から確認する。

終了コードは0成功、1失敗/確認不能、2入力不正、3未同意、4容量不足、5競合、6外部処理失敗、7期限超過、8動画/履歴不合格。install は事前検査 / 取得 / 計画 / 依存導入 / 事後検査 / 配置 / リンクの工程、仮想環境の変更状態、再実行の可否を表示する。依存導入開始後の失敗は途中変更の可能性を表示し、そのまま再実行せず本人の pip check・配布物差分・配置確認を要求する。
