# 検証記録

## 読み方・対応

要件は [要件書](../requirements/issue-1-requirements.md)、決定は [設計書](../design/issue-1-design.md)、現在の契約は [architecture](../design/master/architecture.md) / [operations](../design/master/operations.md) / [security](../design/master/security.md) を参照する。提供元は2026-10-12〜13の対象機に関する orchestrator の実機確認事実である。原ログ・動画・個人パスは収録しない。終了コードや日時・prompt_id が提供されない場合は未提供と記し、推測で補わない。手作業・試作の記録と、コミット b38c0cb・b7e51f5・a8d0ade・fbe640a のスクリプト実行結果を分ける。fc87081 の request_json を使う実機再実行の成功とは読み替えない。

各レコードは ID / FR・AC・D / 成果物 / 要件節 / Issue設計節 / マスター節 / 日付・時刻 / 固定版・条件 / 開始状態 / 状態3区分 / 手順 / 期待・実際 / 終了コード / 証跡 / 対処 / 未確認範囲を持つ。クリーンはその導入対象と取得途中データが存在しない開始状態である。

| コミット | 対応 |
| --- | --- |
| b38c0cb | 実装 |
| 22e4ed7 | 実装レビュー round 1 の C1-01〜C1-06 への修正 |
| b7e51f5 | セキュリティ・契約レビュー round 1 への修正と実機検証結果の記録 |
| a8d0ade | C2-01・C2-02 への修正（HTTP 本文の完全性検査の維持と交換全体の期限） |
| fbe640a | セキュリティ・契約レビュー round 2 への修正（チャット例の検証区分、期限案内 1800000 / 3600000、許可先リンクの拒否、履歴不在の文言） |
| fc87081 | C3-01 への修正（ワーカーの終了を確認してから結果を読む） |

| FR / AC / D | 成果物 | 要件節 | Issue設計節 | マスター節 |
| --- | --- | --- | --- | --- |
| FR-1 / AC-1 | README | 構成・FR-1 | 概要・構成・データ形式 | architecture 構成 / operations 配置 |
| FR-2 / AC-2 | README・download | FR-2 | download・安全性 | security 信頼境界 |
| FR-3 / AC-3 / D-3 | install・download・h3_common・manifest・make_manifest | FR-3・冪等性 | install・download・データ形式 | operations 非変更再実行 |
| FR-4 / AC-4 / D-5〜D-7 | Harness YAML/env 例・README・check | FR-4・制約 | check・データ形式 | operations 配置・診断 |
| FR-5 / AC-5 / D-1〜D-9 | check・h3_common | 診断項目 | check | operations 診断 |
| FR-6 / AC-6・AC-11 | submit・workflow・h3_common | FR-6 | submit・データ形式 | architecture データフロー / operations 保存 |
| FR-7 / AC-7 / D-4 | register・submit・workflow | FR-7 | register・submit | operations 登録・保存 |
| FR-8 / AC-8 | 本記録・両層設計書 | FR-8 | 検証記録 | 全マスター |
| AC-9・AC-10 | .gitignore・README・全テキスト・tests | 公開安全性・信頼境界 | 安全性 | security 全節 |
| AC-12 | README・本記録 | メモリ | submit・検証記録 | operations 生成条件 |

## 構成・配置

| フィールド | 記録 |
| --- | --- |
| ID / FR・AC・D | HOST-01 / FR-1・FR-8 / AC-1・AC-8 |
| 成果物 / 要件節 | README・設定例 / 対象構成・確認済み事実 |
| Issue設計節 / マスター節 | 共通CLI・データ形式 / architecture 構成・operations 配置 |
| 日付・時刻 / 固定版・条件 | 2026-10-12（時刻未提供）、macOS26 / M5 Max / 128GB。Comfy Desktop1.1.6 / ComfyUI0.39.2 / Python3.13.12 / ManagerV4.2.2 / PyYAML6.0.3 / hub1.30.0 / Ollama0.33.3 / Harness0.2.0-rc.2 / dsh-comfyui0.5.4 / ffmpeg7.1.1 Homebrew |
| 開始状態 / 状態3区分 | アプリ導入後の対象機 / 既存環境で検証 |
| 手順 | 各版とインスタンス・共有先・venv の実配置を確認（提供事実） |
| 期待・実際 | 本体 ~/ComfyUI-Installs/ComfyUI/ComfyUI、venv はその .venv、共有モデル ~/ComfyUI-Shared/models、出力 ~/ComfyUI-Shared/output |
| 終了コード / 証跡 | スクリプト終了コード未提供 / 対象機の構成・実配置の提供テキスト |
| 対処 / 未確認範囲 | 別配置は明示CLI / CLIの再実行は下のLIVEレコード参照 / ffprobe版・他機体 |

## 容量と導入

| フィールド | 記録 |
| --- | --- |
| ID / FR・AC・D | INSTALL-01 / FR-1・FR-3・FR-8 / AC-1・AC-3・AC-8 / D-2・D-3 |
| 成果物 / 要件節 | README・install・manifest / 対象構成・FR-3 |
| Issue設計節 / マスター節 | install・データ形式 / architecture 固定資材・operations 非変更再実行 |
| 日付・時刻 / 固定版・条件 | 2026-10-12、ノード ab1756d571ebb14fed3168354dae42966a04348b、モデル3 SHA は architecture の表と同じ |
| 開始状態 / 状態3区分 | 当該導入対象と取得途中データが無いクリーン状態 / クリーン状態で検証 |
| 手順 | 公式 dmg の署名・公証確認、初回 GUI、固定ノード配置、pip install --dry-run 後導入、pip check、固定3リビジョン取得、再起動後の登録確認（手作業） |
| 期待・実際 | Notarized Developer ID。既存配布物の変更なし・14個追加・pip check 問題なし。4ノード登録。全136件サイズ一致（base66件77,770,657,762 / int8 13件37,797,145,373 / turbo57件1,559,967,577 bytes）。合計117,127,770,712 bytes ≈117.13GB ≈109GiB。baseはFL2VA指定6コンポーネントのみ |
| 終了コード / 証跡 | 個別終了コード未提供 / 手作業導入・pip check・サイズ全件一致の提供結果 |
| 対処 / 未確認範囲 | 競合は本人の退避、pip check確認 / クリーンノード導入・base/int8取得・実測free（既存installとTurbo等のCLI実機はLIVEレコード参照）、キャッシュ/生成物追加容量 |

AC-3 の容量不足注入は「必要量の上書き」から **空き容量側を下げる `min(実測,N)`** に置換する。manifest由来の必要量を維持し、不足だけを再現してゲートを緩めないためである。R=0の完了済み経路とTurbo初回・2回目のCLI実機結果は下のLIVEレコードに記録する。

## 直接生成

| フィールド | 記録 |
| --- | --- |
| ID / FR・AC・D | DIRECT-SMOKE / FR-6・FR-8 / AC-6・AC-11 / D-1〜D-4 |
| 成果物 / 要件節 | workflow・submit・README / FR-6・AC-11 |
| Issue設計節 / マスター節 | submit・検証記録 / operations 保存・生成条件 |
| 日付・時刻 / 固定版・条件 | 2026-10-12、HOST-01構成、64×64・1秒・steps5・seed0。スモーク出典は固定ノード README。プロンプトの原文は未提供（新規固定例と同一とは断定しない） |
| 開始状態 / 状態3区分 | ノードと3モデル導入済み、ComfyUI起動中 / 既存環境で検証 |
| 手順 | 試作で固定APIグラフを直接投入、完了・保存・両ストリームと全デコードを確認 |
| 期待・実際 | 成功、生成を伴う約52秒、MP4存在。H.26464×64・24fps・39フレーム＋AAC stereo32kHz、全デコード成功。保存先は ~/ComfyUI-Shared/output/minimax_h3/ 配下（個別ファイル名未提供） |
| 終了コード / 証跡 | 試作・デコード終了コードの数値未提供、エラー無しの成功報告 / 提供された直接スモーク結果 |
| 対処 / 未確認範囲 | GUI PATHのffmpeg解決失敗には固定絶対パスとvenv binリンク / 原グラフ全文・同サイズ改変（b38c0cb/b7e51f5の実機submitとprompt_idはLIVE-DIRECT-SMOKEおよび追加記録参照） |

| フィールド | 記録 |
| --- | --- |
| ID / FR・AC・D | DIRECT-5S / FR-6・FR-8 / AC-6 / D-1〜D-4 |
| 成果物 / 要件節 | workflow・submit・README / FR-6・AC-6 |
| Issue設計節 / マスター節 | submit・検証記録 / operations 保存・生成条件 |
| 日付・時刻 / 固定版・条件 | 2026-10-12、HOST-01構成、768×448・5秒・steps9・seed42。プロンプト原文未提供 |
| 開始状態 / 状態3区分 | 導入済みComfyUI、途中Qwen応答とGPU共用 / 既存環境で検証 |
| 手順 | 試作の直接投入・完了待ち・保存・動画検査 |
| 期待・実際 | 成功、生成を伴う845秒、H.264768×448・24fps・124フレーム＋AAC stereo、全デコード成功。MP4存在、出力/minimax_h3配下。通常1step約60秒・GPU共用区間約100秒 |
| 終了コード / 証跡 | 数値未提供・デコード成功 / 提供された直接5秒結果 |
| 対処 / 未確認範囲 | 共用を減らす・生成期限を明示 / a8d0adeのsubmit実機はLIVE-DIRECT-5S参照 / この試作のprompt_id・原文・他条件の再現率 |

## チャット生成・提供元

| フィールド | 記録 |
| --- | --- |
| ID / FR・AC・D | CHAT-SMOKE / FR-4・FR-7・FR-8 / AC-4・AC-7 / D-4〜D-7 |
| 成果物 / 要件節 | register・submit・設定例・README / FR-4・FR-7・AC-7 |
| Issue設計節 / マスター節 | register・submit・検証記録 / architecture データフロー・operations 保存 |
| 日付・時刻 / 固定版・条件 | 2026-10-12、HOST-01構成、qwen3.8:27b-mlx、スモーク64×64・1秒・steps5。履歴seed3105209621。promptは A golden retriever puppy running on a sunny beach, waves crashing softly |
| 開始状態 / 状態3区分 | desktop設定・ダミーキー・プラグイン・試作のライブラリ登録済み、Harness再起動後 / 既存環境で検証 |
| 手順 | 登録ワークフロー一覧と対象ノード取得、ライブラリidから同期実行、実投入グラフを元データで照合、動画検査と同時刻Ollamaログを照合 |
| 期待・実際 | 成功61秒。呼出し comfyui_workflow action=run、ライブラリid、parametersにprompt/width/height/duration_seconds/steps、mode=sync、timeout_ms=900000。履歴の3ノード構成と固定入力が登録グラフと一致、差分は公開6項目だけ。seedはランダム化。H.26464×64・39フレーム＋AAC stereo、MP4存在、全デコード成功 |
| 終了コード / 証跡 | ツール・デコードの数値未提供 / 同時刻のOllama POST /v1/chat/completions 13:10:37・13:11:12・13:12:08・13:12:22、4件とも200。元グラフ照合の提供結果。生ログ・id・原グラフ全文は未提供 |
| 対処 / 未確認範囲 | 同期を使い、完了は同じComfyUI起動中の履歴で確認 / リポジトリ版の登録項目によるチャット生成、原グラフ全文の収録、async、ツール承認機構。試作版の履歴verifyはLIVE-CHAT-VERIFY参照 |

| フィールド | 記録 |
| --- | --- |
| ID / FR・AC・D | CHAT-15S / FR-6・FR-7・FR-8 / AC-6・AC-7参考・AC-12 |
| 成果物 / 要件節 | README・submit / 確認済み事実・メモリ |
| Issue設計節 / マスター節 | submit・検証記録 / operations 生成条件 |
| 日付・時刻 / 固定版・条件 | 2026-10-12、HOST-01構成、チャット448×768・15秒・steps9（seed・prompt原文未提供） |
| 開始状態 / 状態3区分 | チャット環境導入済み / 既存環境で検証 |
| 手順 | チャットから timeout_ms=900000 で生成、チャット期限後もComfyUIの継続・完了を確認 |
| 期待・実際 | ComfyUI計測48分で完了成功。H.264448×768・361フレーム・15.04秒＋AAC stereo、MP4存在、全デコード成功。チャット同期は15分期限のため先にタイムアウトしうるが生成は継続 |
| 終了コード / 証跡 | 数値未提供・デコード成功 / 提供された15秒完了結果（40分前後の途中観測を完了値に使わない） |
| 対処 / 未確認範囲 | 指示文に15秒なら上限3600000ms（60分）の期限を明示。再投入せず出力/履歴を確認。submitは7200秒 / 900000を超えるtimeout_msを指定したチャット実行は未実施（長い期限指定の実行記録なし）・正確な公開6値・繰返し成功率 |

## 設定・互換性・待受・メモリ・事前確認

| フィールド | 記録 |
| --- | --- |
| ID / FR・AC・D | HARNESS-SETUP / FR-4・FR-8 / AC-4・AC-8 / D-6・D-7 |
| 成果物 / 要件節 | YAML/env例・README / FR-4・制約 |
| Issue設計節 / マスター節 | check・データ形式 / operations 配置・security キー |
| 日付・時刻 / 固定版・条件 | 2026-10-12、Harness0.2.0-rc.2 / dsh-comfyui0.5.4 / Ollama0.33.3 |
| 開始状態 / 状態3区分 | 手作業導入時、対象設定・プラグイン導入前 / クリーン状態で検証 |
| 手順 | キー欠落・互換性拒否を確認し、利用者の手作業追記と明示承諾後の完全一致例外・add・再起動 |
| 期待・実際 | No API key for provider: ollama は ~/.dsh/.env の非秘密ダミー値で解消。installation rejected: Plugin dsh-comfyui@0.5.4 is incompatible with dsh 0.2.0-rc.2: peerDependencies ... を確認。本人承諾後 dsh plugin --profile desktop allow-version dsh-comfyui@0.5.4 --dsh-version 0.2.0-rc.2 --accept-risk、続けてadd同版で導入。Harnessは実行中にcordis.patch.ymlを自己再保存 |
| 終了コード / 証跡 | 数値未提供 / 拒否出力・対象版・承諾と導入の提供事実 |
| 対処 / 未確認範囲 | 既存設定を保持し再適用、本人の手動例外 / 上流未マージ修正は未適用・async未検証（b38c0cb/b7e51f5/a8d0adeのD-6/D-7はLIVE-DIAGNOSTICおよび追加記録参照） |

| フィールド | 記録 |
| --- | --- |
| ID / FR・AC・D | LISTEN-01 / FR-5・FR-8 / AC-5・AC-10 / D-8・D-9 |
| 成果物 / 要件節 | check・README / 信頼境界・診断 |
| Issue設計節 / マスター節 | check・安全性 / operations 診断・security URL |
| 日付・時刻 / 固定版・条件 | 2026-10-12、HOST-01構成、Harness観測ポート19387（動的） |
| 開始状態 / 状態3区分 | 3サービス起動中 / 既存環境で検証 |
| 手順 | 待受を実機確認（手作業・提供事実） |
| 期待・実際 | ComfyUI127.0.0.1:8188、Ollama127.0.0.1:11434、Harness127.0.0.1:19387、いずれもループバックのみ |
| 終了コード / 証跡 | スクリプト終了コード未提供 / 提供されたTCP待受結果 |
| 対処 / 未確認範囲 | 外部公開禁止・CORS/--listen禁止 / UDP（b38c0cb/b7e51f5/a8d0adeのD-8/D-9はLIVE-DIAGNOSTICおよび追加記録参照） |

| フィールド | 記録 |
| --- | --- |
| ID / FR・AC・D | MEMORY-01 / FR-8 / AC-12 |
| 成果物 / 要件節 | README・本記録 / メモリ |
| Issue設計節 / マスター節 | submit・検証記録 / operations 生成条件 |
| 日付・時刻 / 固定版・条件 | 2026-10-12、チャット前後と15秒生成中（測定時計時刻未提供）、HOST-01、Qwen稼働 |
| 開始状態 / 状態3区分 | Qwenと動画モデルの併用 / 既存環境で検証 |
| 手順 | システム全体空き率とQwen占有・Ollama文脈長・Harness設定を確認 |
| 期待・実際 | 空き率前後40〜60%、15秒生成中41〜44%、Qwen約20〜21GB。Ollama既定262144、HarnesscontextWindow65536 |
| 終了コード / 証跡 | 該当なし / 提供された実測。262144は当該機の既定で推奨ではない |
| 対処 / 未確認範囲 | 文脈抑制・モデル解放・同時実行削減・生成1件から確認 / 他条件での安定性・時刻付き生測定・無条件併用保証 |

| フィールド | 記録 |
| --- | --- |
| ID / FR・AC・D | PRECHECK-01 / FR-8 / AC-8・AC-10 |
| 成果物 / 要件節 | README・security / FR-8・残余リスク |
| Issue設計節 / マスター節 | 安全性・検証記録 / security 信頼境界 |
| 日付・時刻 / 固定版・条件 | 2026-10-12、ノードab1756d・npm dsh-comfyui0.5.4 |
| 開始状態 / 状態3区分 | 固定ソース・配布物の読取 / 既存環境で検証 |
| 手順 | 外部通信・eval/exec・pickle・外部コマンド・install script・外部URLを事前確認 |
| 期待・実際 | ノードに外部通信・eval/exec・pickle読込なし、ffmpeg引数リスト起動1箇所。プラグインにinstall scriptなし、外部URLはループバックと例示、プロセス起動はファイルマネージャー1箇所 |
| 終了コード / 証跡 | 該当なし / 提供された事前確認結果、実装担当は固定ノード入力・保存記述・requirementsとプラグイン型/保存処理を読取 |
| 対処 / 未確認範囲 | 信頼できない入力をエージェントに実行させない / 依存パッケージの中身未確認。全面的安全性保証ではない |

基本モデルの取得範囲には Python ファイルが24件含まれる（FL2VA/audio_vae/*.py 9件・FL2VA/video_vae/*.py 15件）。固定コミットのノードのソースに importlib・__import__・exec・eval・runpy の使用は無く（2026-10-12、文字列検索で確認）、これらのファイルをノードが実行する経路は見つかっていない。ファイルの中身自体は未確認。

## スクリプトの実機検証結果

次の表の **各行を独立したレコード**とする。共通フィールドは日付=2026-10-12（時計時刻未提供）、対象=b38c0cb のスクリプトと HOST-01 の固定版、実行=ComfyUI 仮想環境の Python `-I -B`、証跡=orchestrator が提供した実機出力・前後比較である。通常の開始状態は手作業で導入済みの既存環境。クリーンは表の一時配置先だけに適用する。期待は各CLIの契約、実際と終了コードは表に記す。未検証行には実際・終了コード・証跡は無い。b7e51f5・a8d0ade の再実行結果は下の追加記録に分ける。

| ID / FR・AC・D | 成果物 / 要件節 / Issue設計節 / マスター節 | 開始状態 / 状態3区分・手順 | 実際・終了コード / 対処・未確認範囲 |
| --- | --- | --- | --- |
| LIVE-INSTALL / FR-3 / AC-3 | install / FR-3 / install / operations 非変更 | 手作業で導入済み / 既存環境で検証。引数なし | 0、既存版不変 / pip check PASS、追加配布物なし、ノード追跡ファイル不変、ffmpegとモデル入口リンクの作成時刻不変。未確認: ノード無しからの新規CLI導入、wheel限定・事前checkの再実行はb7e51f5の追加記録参照 |
| LIVE-INSTALL-CONFIG / FR-3 / AC-3 | install / 権限・FR-3 / install / security 配布 | 別取得元を持つ利用者pip/git設定下 / 未検証 | 理由: 該当設定下の実機installは未実施。argv・子環境隔離は単体テストのみ。本人の設定を保持して実機で確認する |
| LIVE-DOWNLOAD-EXISTING / FR-3 / AC-3・D-3 | download / AC-3 / download / operations 非変更 | 3モデル既存 / 既存環境で検証。引数なし | 0、すべて完了済み・変更なし。同意要求・取得なし |
| LIVE-CONSENT / FR-2 / AC-2 | download / FR-2 / download / security 信頼境界 | 空の一時配置先 / クリーン状態で検証。Turbo・標準入力なし・同意フラグなし | ライセンス表示後3、配置先不作成。本人の同意無しでは取得しない |
| LIVE-TURBO / FR-3 / AC-3・D-3 | download / AC-3 / download / operations 非変更 | 空のtempfile配置先 / クリーン状態で検証。本人が3モデルのライセンス同意済み、Turboを同意フラグ付き取得→同条件2回目 | 初回0、57件・1,559,967,577 bytes。R=1559967577・余裕=1073741824・必要=2633709401 bytes、実測free未提供。2回目0・完了済み・再取得なし。未確認: base/int8のクリーンCLI取得 |
| LIVE-CAPACITY / FR-3 / AC-3 | download / AC-3 / download / operations 非変更 | 別の空の一時配置先 / クリーン状態で検証。--test-free-bytes 1000 | 有効free=1000、4、配置先不作成。必要量を維持し空き側だけ下げる方式で不足を再現する |
| LIVE-MODEL-FAULTS / FR-3 / AC-3・D-3 | download / AC-3 / download / operations 非変更 | Turbo取得済みの一時配置先 / 既存環境で検証。1回ずつ故障注入 | README.mdへ1バイト追加→5、conversion_manifest.jsonを半分に切詰め→5、.cache/huggingface/download/probe.incomplete→5、復元→0。各実行前後の全ファイルのサイズ/mtime/小さいファイルのSHA-256は不変。自動修復無し |
| LIVE-DIAGNOSTIC / FR-5 / AC-5・D-1〜D-9 | check / 診断 / check / operations 診断 | 導入・試作登録・3サービス起動済み / 既存環境で検証。引数なし | 全PASS・0。D-3全136件完了と入口一致、D-4登録固定入力一致・ffprobe有り、D-8/D-9全TCP LISTENがループバック。lsof機械形式の実出力を解析。UDP/CORSは対象外 |
| LIVE-DIRECT-SMOKE / FR-6 / AC-6・AC-11 | submit・workflow / FR-6 / submit / operations 保存 | 稼働ComfyUI / 既存環境で検証。既定スモーク・--timeout 1200 | 0、prompt_id=ce519269-ce90-4f8e-b2f2-2fc9f8ded5d4、51.4秒、promptはワークフロー既定、64×64・1秒・steps5・seed0。履歴照合PASS、~/ComfyUI-Shared/output/minimax_h3/ComfyUI_00005_.mp4、H.26464×64/AAC/全フレームデコード成功 |
| LIVE-DIRECT-5S / FR-6 / AC-6 | submit / AC-6 / submit / operations 保存 | 2026-10-13、a8d0ade、導入済みComfyUI / 既存環境で検証。--width 768 --height 448 --seconds 5 --steps 9 --seed 42 --timeout 3600、promptはワークフロー既定 | 0、prompt_id=11d9178a-8f2d-4a8d-8b69-73614651064b、完了551.8秒（ComfyUI計測551.32秒）。Qwen未ロード・開始時メモリ空き率61%。履歴照合PASS、~/ComfyUI-Shared/output/minimax_h3/ComfyUI_00007_.mp4、H.264768×448/AAC/全フレームデコード成功。ComfyUI仮想環境のPython -I -B、証跡はorchestrator提供結果、時計時刻未提供。未確認: 他条件の再現率 |
| LIVE-CHAT-VERIFY / FR-7 / AC-7 | submit / FR-7 / submit / operations 保存 | 試作ライブラリでチャット生成済み / 既存環境で検証。--verify-history c014abbc-8117-4a5d-902d-05512c6b7d50 | 0、prompt="A golden retriever puppy running on a sunny beach, waves crashing softly"、64×64・1.0秒・steps5・seed3105209621。登録試作版とリポジトリ双方の固定入力一致、ComfyUI_00003_.mp4検査PASS |
| LIVE-CHAT / FR-4・FR-7 / AC-4・AC-7 | register・submit・設定例 / FR-7 / register・submit / architecture フロー | リポジトリ版の項目を登録してチャット生成 / 未検証 | 理由: 実機ライブラリには同名の試作版がありregisterは5で拒否した。本人が試作版をパネルで削除して登録し直した後に実施する。試作版チャットの履歴照合成功とは区別する |
| LIVE-REGISTER / FR-7 / AC-7 | register / FR-7 / register / operations 登録 | 空のtempfileライブラリ / クリーン状態で検証。1回目→2回目 | 1回目登録0（Harness起動中警告）、2回目変更なし0、workflows.jsonのSHA-256は両回同一。b7e51f5の説明文と実用既定値の登録は追加記録参照。fbe640a の期限案内を含む登録の実機結果は追加記録参照 |
| LIVE-CHAT-REREGISTER / FR-7 / AC-7・D-4 | register・check / 冪等性・FR-7 / register・check / operations 登録 | 試作同名項目のある実機ライブラリ / 既存環境で検証。引数なしregisterとcheck | registerは同名別内容（原本保持）5、ライブラリ非変更。checkのD-4はPASS（固定入力一致）。この登録項目はリポジトリ版の同内容ではないため、同内容0を実機ライブラリで確認したとは扱わない |
| LIVE-MEMORY / FR-8 / AC-12 | README・本記録 / メモリ / 検証記録 / operations 生成 | Qwen稼働と15秒生成 / 既存環境で検証 | MEMORY-01とCHAT-15Sの実測を参照。15秒動画は48分、H.264448×768・361フレーム・15.04秒、AACステレオ、全フレームデコード成功、生成中空き率41〜44%。測定時計時刻は未提供 |
| LIVE-ASYNC / FR-7 / AC-7 | README / FR-7 / register・submit / architecture フロー | async実行 / 未検証 | 理由: 今回の構成でasync実行を行っていない。標準はsync、未検証を成功扱いしない |

セッション記録から抽出した呼出しは `comfyui_workflow` の `{"action":"run","id":"<ライブラリの id>","parameters":{"duration_seconds":1,"height":64,"prompt":"A golden retriever puppy running on a sunny beach, waves crashing softly","steps":5,"width":64},"mode":"sync","timeout_ms":900000}`。`comfyui_run` によるグラフの直接指定は呼ばれていない。長時間では既定900000msによりチャット側だけ先にタイムアウトしうるがComfyUI側は継続し完了するため、再投入しない。

S1-01 の修正前実機確認: writable は ~/.dsh/.env を拒否する一方、大文字小文字違いの ~/.DSH/.env・~/.Dsh/profiles/desktop/cordis.patch.yml と別マウント経路のホーム別名を許可した。いずれも samefile で同実体だった。修正の単体テストは偽ホーム・大小別名・リンク・別マウント経路相当の別名で保護と許可を確認する。2026-10-13、b7e51f5 の writable に ~/.dsh/.env・~/.DSH/.env・大文字小文字違いのprofile配下・別マウント経路のホーム別名を与えた読み取り確認では、4件とも2で拒否しファイル非変更（orchestrator提供）。

ライセンス原文リンク: 基本モデルLICENSE・INT8 LICENSE・Turbo README.mdの固定リビジョンURLはすべてHTTP 200（2026-10-12、orchestrator提供）。内容の要約は非正本。

### スクリプトの実機再実行（追加、2026-10-13）

提供元は orchestrator。対象機・固定サービス版は HOST-01 と同じ、ComfyUI 仮想環境の Python `-I -B` を使う。開始状態は導入済みの既存環境で、空の一時ライブラリと依存解決用の空の仮想環境だけをクリーン状態とする。時計時刻は未提供。以下は指定コミットの実行結果であり、fc87081 の request_json を使う実機再実行の検証ではない。

| ID / FR・AC・D | 対象 / 開始状態・手順 | 実際・終了コード / 未確認範囲 |
| --- | --- | --- |
| LIVE-DIAGNOSTIC-RECHECK / FR-5 / AC-5・D-1〜D-9 | b7e51f5 と a8d0ade / 既存環境で検証。check_env.py 引数なし | 両コミットとも全PASS・0。b7e51f5はbase66/int8 13/turbo57件すべて完了と要約表示 |
| LIVE-DOWNLOAD-RECHECK / FR-3 / AC-3・D-3 | b7e51f5 / 3モデル既存、download_h3_models.py 引数なし | すべて完了済み・変更なし、0。新規取得ではない。空の配置先へのTurbo取得はb38c0cbのLIVE-TURBO参照 |
| LIVE-INSTALL-RECHECK / FR-3 / AC-3 | b7e51f5 / 導入済み環境、install_h3_node.py 引数なし。事前pip check・wheel限定の版 | 既存版不変 / pip check PASS、追加配布物なし、0。ノード無しからの新規CLI導入は未確認 |
| LIVE-REGISTER-RECHECK / FR-7 / AC-7 | b7e51f5 / 空の一時配置先、register_dsh_workflow.py --data-dir <空の一時ディレクトリ> を2回 | 初回登録0、2回目変更なし0。実用既定値・当該コミットの説明文での登録。fbe640a の期限案内を含む登録の実機結果は追加記録参照 |
| LIVE-DIRECT-SMOKE-RECHECK / FR-6 / AC-6・AC-11 | b7e51f5 / 稼働ComfyUI、submit_h3.py --seed 7。64×64・1秒・steps5、promptはワークフロー既定 | 0、prompt_id=a78027a3-00d6-4c8b-a327-9592c719f106、34.6秒。履歴照合PASS: ノード構成・固定入力 / リポジトリのワークフロー / 登録項目なし。新規投入ではライブラリを読まずリポジトリだけと照合。~/ComfyUI-Shared/output/minimax_h3/ComfyUI_00006_.mp4、H.26464×64/AAC/全フレームデコード成功 |
| LIVE-HISTORY-ABSENT / FR-7 / AC-7 | b7e51f5 / submit_h3.py --verify-history does-not-exist | 履歴に無いID、待たずに2。後続の実行中・待機中の案内文変更は未確認 |
| LIVE-WRITE-PROTECTION / AC-9・AC-10 | b7e51f5 / 上記S1-01の4パスをwritableで読み取り確認 | 4件とも2で拒否、ファイル非変更。後続の許可先ディレクトリリンク拒否は実機未確認 |
| LIVE-WHEEL-PLAN / FR-3 / AC-3 | b7e51f5の固定requirements / ComfyUIと同じPython3.13.12の空のvenv、pip --isolated install --dry-run --only-binary :all: --index-url https://pypi.org/simple --report <一時ファイル> -r requirements.txt | 57件すべてwheelで計画成立。導入はしていない、終了コードの数値未提供 |

AC-6 の5秒直接生成は a8d0ade の LIVE-DIRECT-5S で記録する。単独実行は551.8秒（約9分）、Qwen応答とGPU共用した試作実行は845秒（約14分）。a8d0ade の単体テストは111件成功との提供結果である。

dsh-comfyui 0.5.4 の `lib/tools.js` で確認された `comfyui_workflow` のスキーマは timeout_ms 最小5000・最大3600000（60分）・既定900000。スモークと15秒のチャット実行は900000であり、5秒1800000・15秒3600000の案内は生成時間に基づく期限指定例で、指定したチャット実行の成功記録ではない。

未実施: リポジトリ版の登録項目によるチャット生成（実機の同名試作版を本人が削除し再登録してから実施）、768×448・5秒のチャット実行と900000を超えるtimeout_msを指定したチャット実行（実行記録なし）、別取得元を持つ利用者pip/git設定下のinstall（該当設定で実行していない）、async（同期のみ）、Python3.11/3.12（対象機は3.13.12）。

a8d0ade の外部変異検証は一時コピーを使い、対照実行成功、以下6件すべて検出との提供結果である。HTTP実装はこの修正作業では変更しない。

| 変異 | 落ちたテスト | 提供結果 |
| --- | --- | --- |
| joinの全体期限を外す | test_http_deadline_bounds_reads_inside_the_chunk_parser | FAIL |
| 実行中の交換を完了扱い | test_http_deadline_bounds_reads_inside_the_chunk_parser | ERROR |
| readをread1に戻す | test_http_body_shorter_than_content_length_is_a_failure | FAIL |
| HTTPプロトコル例外の分類を外す | test_http_protocol_errors_are_classified_not_raised | ERROR |
| HTTPプロトコル例外の分類を外す | test_http_body_shorter_than_content_length_is_a_failure | ERROR |
| 不正JSON本文の分類を外す | test_http_invalid_json_body_is_an_http_failure | FAIL |

## ローカル単体テスト・変異検証

| フィールド | 記録 |
| --- | --- |
| ID / FR・AC・D | LOCAL-01 / FR-2〜FR-8 / AC-2〜AC-12のローカル範囲 / D-1〜D-9故障注入 |
| 成果物 / 要件節 | tests/test_*.py・全CLI / FR・安全性・冪等性 |
| Issue設計節 / マスター節 | テスト方針 / operations 診断・security 各節 |
| 日付・時刻 / 固定版・条件 | 2026-10-12、システムPython3.14.6、unittest・mock・tempfile、ネットワーク/実サービス/GPUなし |
| 開始状態 / 状態3区分 | テスト対象のデータは毎回tempfile内に新規作成 / クリーン状態で検証 |
| 手順 | python3 -m unittest discover -s tests -v、要件由来の変異を一時コピーへ1箇所ずつ適用 |
| 期待・実際 | テストと変異の最終結果は下表へ記録する |
| 終了コード / 証跡 | 最終実行結果を下表へ記録する。実機成功の代替にはしない |
| 対処 / 未確認範囲 | 必須故障の修正と再実行 / 実機表の未検証項目、b38c0cb の独立レビュー（後続のレビュー記録を参照）、Python3.11での実行（コードは3.11以上対応） |

b38c0cb のローカル結果: `python3 -m unittest discover -s tests -v` は84件成功、失敗0・エラー0・スキップ0、終了0（Python3.14.6）。このうち1件は下の20変異を別プロセスの単体テストで検査する。全CLI6本の `-I --help` も成功。PyYAML 不在時は3件のYAMLテストを理由付きスキップする。hubはスタブを使うため不在でもテスト可能で、hub不在/旧版の終了1を別途注入する。

b38c0cb の変異結果: 以下20件すべてで指定テストが失敗する。構文をcompileで確認してから実行し、構文エラー・ネットワーク失敗・スキップを検出成功に数えない。原実装の内容不変と一時コピーの削除・不在をテストで確認する。

| 変異 | 落ちたテスト（test_*.py のメソッド名） | 結果 |
| --- | --- | --- |
| 同意呼出しを省略 | test_consent_each_model_non_tty_no_transfer | 検出 |
| revision 照合を省略 | test_manifest_sha_repo_scope | 検出 |
| サイズ一致を <= に変更 | test_conflict_each_model_precedes_consent | 検出 |
| .incomplete 判定を省略 | test_size_incomplete_extra_shared_d3 | 検出 |
| 完了済みを5に変更 | test_all_complete_no_hub_no_consent_no_capacity | 検出 |
| 容量境界を < から <= に変更 | test_capacity_boundary_and_clamp | 検出 |
| パス包含を常に真 | test_output_missing_invalid_and_escape | 検出 |
| URLループバック制限を省略 | test_local_url_loopback | 検出 |
| 診断集約を all から any に変更 | test_aggregate_any_failure_unknown | 検出 |
| 対象キーの値を表示 | test_target_key_never_printed | 検出 |
| 公開6項目の集合検査を省略 | test_parameters_exact_six_no_max | 検出 |
| 同名同内容も競合扱い | test_same_content_different_ids_byte_unchanged | 検出 |
| 同名別内容を許容 | test_different_workflow_and_parameter_nonchange | 検出 |
| AAC存在を架空の値で代替 | test_video_missing_audio_wrong_codec_wrong_resolution | 検出 |
| 解像度照合を省略 | test_video_missing_audio_wrong_codec_wrong_resolution | 検出 |
| デコードエラーを無視 | test_video_decode_failure_and_timeout | 検出 |
| D-4登録項目側を検査しない | test_d4_repository_and_registration_both_checked | 検出 |
| D-4不正ライブラリを未登録扱い | test_d4_bad_library_fails_not_unregistered | 検出 |
| verify登録項目との照合を省略 | test_verify_registered_and_repository_both_no_execution | 検出 |
| verify不正ライブラリを未登録扱い | test_verify_bad_library_never_fallback | 検出 |

対応するテストファイルは test_common.py / test_download.py / test_check_env.py / test_register.py / test_submit.py、変異の再現処理は tests/test_mutations.py である。HTTPはmockしたopener/応答で検査し、実装中のネットワーク禁止に従ってHTTPサーバーも起動しない。

## 公開物点検・後片付け

| フィールド | 記録 |
| --- | --- |
| ID / FR・AC・D | PUBLIC-01 / FR-8 / AC-9・AC-10 |
| 成果物 / 要件節 | README・config・workflows・scripts・tools・tests・doc・.gitignore / 公開安全性 |
| Issue設計節 / マスター節 | 安全性・検証記録 / security 公開資料 |
| 日付・時刻 / 固定版・条件 | 2026-10-12、公開テキストの文字列検索・ファイル一覧 |
| 開始状態 / 状態3区分 | 実装成果物の作業ツリー / 既存環境で検証 |
| 手順 | 個人絶対パス・秘密目印・モデル重み・未加工例外表示を点検、manifestの複製内容一致、要件書非変更とgit diffを確認 |
| 期待・実際 | 個人絶対パス・秘密形式の文字列検索は0件、重み不在。manifestは提供原本とcmpでバイト一致。要件書のgit diffは空、設計書は補足・実機訂正と必要な実装明確化だけ。テストのSECRET目印はスタブ値であり実キーではない |
| 終了コード / 証跡 | 点検結果を最終報告へ記載。PR/Issue貼付予定テキストはorchestratorが同じ検索を実施 |
| 対処 / 未確認範囲 | 個人パスは~、秘密は収録しない / PR・Issue公開操作は未実施。独立レビューの状態は末尾のレビュー記録参照 |

公開ファイル一覧は冒頭の対応表と README、.gitignore、configの3資材、workflow、scriptsの6ファイル、tools/make_manifest.py、tests/support.py・test_common.py・test_download.py・test_install.py・test_check_env.py・test_submit.py・test_register.py・test_manifest_and_docs.py・test_mutations.py、要件書・Issue設計書・マスター3書・本記録である。22e4ed7 は C1-01〜C1-06 への修正を含む。tests/test_review_fixes.py は b7e51f5 で追加された。22e4ed7 は単体91件成功、同コミットの期限・HTTP例外・envコメント・待受・submit配線・helpの9変異すべて検出との結果が提供されている。テスト用一時領域は tempfile の context/cleanup で削除し、変異コピーも終了後不在を確認する。


## b7e51f5 に含まれる修正差分のローカル検証（2026-10-13）

対象は 22e4ed7 から b7e51f5 への修正差分である。ネットワーク・実サービス・実際の ~/.dsh は使わず、偽ホーム/tempfile/mock、単体テストと全6CLIの --help だけで検証する。`python3 -B -m unittest discover -s tests -v` は108件成功、失敗0・エラー0・スキップ0、終了0。追加17テストを含む。大文字小文字違いの保護テストも今回の一時ボリュームでは実行し成功（case-sensitiveのボリュームでは理由付きskip）する。別マウント経路相当はディレクトリリンクと、その別名を保持するresolveスタブでdev/inode比較を検証し、OSのmount操作は行わない。

変異は既存20件＋追加33件＝53件すべて検出する。各変異前の同じ対象テストは成功し、1箇所の一時コピー変異後に意図したテストが失敗する。構文エラー・スキップ・ネットワーク失敗は検出として数えない。原本バイト不変と一時コピーの削除を確認し、git diffで意図した修正差分だけが残ることを確認する。22e4ed7のHTTP期限・HTTP例外、envコメント判定、サービス別待受、help既定値、submit配線は変更を巻き戻さず、対応する既存テストも成功する。要件書とワークフローファイルのgit diffは空である。

| 同型のクラス | 点検 / 直接修正 | 点検結果 |
| --- | --- | --- |
| 包含・実体一致 | 7 / 4 | inside・writable・check_link・D-3を変更。safe_model_path・inspect_models・output_videoは共通修正を消費し既存回帰も確認 |
| writableの書込CLI | 4 / 1 | make_manifest・register・download・installを全点検。installは事前順序も変更。4CLIすべて別名拒否2・原本のバイト/stat不変（installのinstance/venv/models-dirも検査） |
| 外部プロセス/デコード | 3 / 3 | command・listenersのstdin=DEVNULL、ffmpeg -nostdin。git子環境1 / 1も非対話固定 |
| pip計画/導入 | 2 / 2 | 共通install_argsで両方wheel限定、事前check1 / 1追加、失敗全7工程を点検し状態表示を統一 |
| モデル状態表示 | 4 / 4 | download初回/最終、check、makeの全消費者で集計・verboseを配線 |
| 容量呼出し | 3 / 3 | 作成前/作成後/各取得前の検査を保持し表示の前回値を引継ぐ |
| 既存項目由来の端末表示 | 3 / 3 | registerの差分キー・既存id、verifyの登録idをJSONエスケープ。新規UUIDと形式検査後prompt_idは該当せず |

追加変異の個別結果:

| 変異 | 落ちたテスト | 結果 |
| --- | --- | --- |
| 実体を文字列比較へ戻す | test_mount_alias_identity_all_writers_preserve_original | 対照成功・変異検出 |
| 書込保護を外す | test_symlink_alias_all_writers_preserve_original | 対照成功・変異検出 |
| 未存在要素のcasefoldを外す | test_allowed_paths_missing_components_and_existing_case_distinction | 対照成功・変異検出 |
| 既存実体の大小を文字列許可 | test_allowed_paths_missing_components_and_existing_case_distinction | 対照成功・変異検出 |
| command標準入力を継承 | test_all_child_input_is_closed | 対照成功・変異検出 |
| listeners標準入力を継承 | test_all_child_input_is_closed | 対照成功・変異検出 |
| git対話を許可 | test_all_child_input_is_closed | 対照成功・変異検出 |
| ffmpeg対話を許可 | test_decode_disables_stdin | 対照成功・変異検出 |
| 完了ファイルを常時表示 | test_model_summary_verbose_and_pass_remedies | 対照成功・変異検出 |
| PASSにも対処を表示 | test_model_summary_verbose_and_pass_remedies | 対照成功・変異検出 |
| 容量を毎回表示 | test_capacity_only_prints_changes_but_always_checks | 対照成功・変異検出 |
| 取得進捗を外す | test_acquire_missing_only_revision_token_recheck | 対照成功・変異検出 |
| Comfy構成検査を外す | test_missing_comfy_structure_no_creation_or_commands | 対照成功・変異検出 |
| pip事前checkを外す | test_precheck_and_wheel_failure_are_nonchanging | 対照成功・変異検出 |
| wheel限定を外す | test_install_failure_stage_changed_and_no_blind_retry | 対照成功・変異検出 |
| 計画失敗を6へ戻す | test_precheck_and_wheel_failure_are_nonchanging | 対照成功・変異検出 |
| 変更状態を未変更へ戻す | test_install_failure_stage_changed_and_no_blind_retry | 対照成功・変異検出 |
| 失敗工程を消す | test_failure_reports_acquisition_postcheck_placement_and_link | 対照成功・変異検出 |
| 登録既定値をスモークへ戻す | test_practical_defaults_graph_unchanged_and_agent_description | 対照成功・変異検出 |
| 説明文の期限を欠落 | test_practical_defaults_graph_unchanged_and_agent_description | 対照成功・変異検出 |
| 登録説明文の配線を外す | test_practical_defaults_graph_unchanged_and_agent_description | 対照成功・変異検出 |
| description比較を外す | test_description_tags_and_terminal_control_characters | 対照成功・変異検出 |
| tags比較を外す | test_description_tags_and_terminal_control_characters | 対照成功・変異検出 |
| 既存idを未加工表示 | test_description_tags_and_terminal_control_characters | 対照成功・変異検出 |
| 既存キー名を未加工表示 | test_description_tags_and_terminal_control_characters | 対照成功・変異検出 |
| 履歴不在の配線を外す | test_missing_verify_id_fails_immediately | 対照成功・変異検出 |
| 公開型不正を固定入力不一致表示 | test_history_public_type_message_and_comparison_targets | 対照成功・変異検出 |
| 照合相手を非表示 | test_history_public_type_message_and_comparison_targets | 対照成功・変異検出 |
| download verbose配線を外す | test_verbose_reaches_all_summary_consumers | 対照成功・変異検出 |
| check verbose配線を外す | test_verbose_reaches_all_summary_consumers | 対照成功・変異検出 |
| make verbose配線を外す | test_verbose_reaches_all_summary_consumers | 対照成功・変異検出 |
| 診断verbose引数を捨てる | test_full_diagnostics_api_faults_individual | 対照成功・変異検出 |
| 追加cacheを必須件数へ混入 | test_model_summary_verbose_and_pass_remedies | 対照成功・変異検出 |

b7e51f5・a8d0adeの実機再実行は追加記録とLIVE-DIRECT-5S参照。Python3.11/3.12、リポジトリ版登録項目によるチャット生成、900000を超えるtimeout_msを指定したチャット実行、別取得元設定下のinstall、asyncは未実施（理由は追加記録）。このローカル記録自体は独立再レビューの証跡ではない。補助編集スクリプトは削除済み。

## fbe640a（セキュリティ・契約レビュー round 2 修正）のローカル検証（2026-10-13）

対象は a8d0ade から fbe640a への修正差分である。ネットワーク・実サービス・実際の ~/.dsh を使わず、単体テストとテスト内の全6CLIの --help だけを実行する。TMPDIRとtempfileの一時配置先を作業ディレクトリ内に固定し、偽ホーム・mock・一時コピーを使う。単体113件（追加2件・既存テストの補強を含む）は成功、失敗0・エラー0・スキップ0、終了コード0。初回に追加テストのimport漏れとMarkdownへのPython構文検査を検出して修正し、リンク変異が引数不足のERRORではなく拒否欠落のFAILになるようテストを補強した後、全件を再実行した。

変異は既存53件＋追加13件＝66件すべて検出。追加13件は各対照実行が成功し、各1箇所の変異で意図したテストがFAILになる。Python変異の構文検査を維持し、構文エラー・ネットワーク失敗・スキップは検出に数えない。原実装のバイト不変・変異コピーの削除を検査し、git diffで修正差分だけが残ることを確認する。request_json の本文は a8d0ade と一致し、tests/test_common.py・要件書・workflow のgit diffは空である。

| 追加変異 | 対象テスト | 最終結果 |
| --- | --- | --- |
| 許可先ディレクトリリンクを許可 | test_allowed_directory_links_refused_without_profile_changes | 対照成功 / FAIL |
| 許可先の親リンクを許可 | 同上 | 対照成功 / FAIL |
| 15秒期限を短縮 | test_practical_defaults_graph_unchanged_and_agent_description | 対照成功 / FAIL |
| ツール上限を誤案内 | 同上 | 対照成功 / FAIL |
| 長い期限の未検証を消す | 同上 | 対照成功 / FAIL |
| 単独生成時間を誤案内 | 同上 | 対照成功 / FAIL |
| 共用生成時間を誤案内 | 同上 | 対照成功 / FAIL |
| 履歴不在で実行中の可能性を消す | test_missing_verify_id_fails_immediately | 対照成功 / FAIL |
| 履歴不在で再投入を案内 | 同上 | 対照成功 / FAIL |
| スモーク検証範囲を消す | test_chat_examples_distinguish_verified_calls_and_generation_conditions | 対照成功 / FAIL |
| 5秒チャットの未検証を消す | 同上 | 対照成功 / FAIL |
| 15秒チャットの未検証を消す | 同上 | 対照成功 / FAIL |
| 15秒指示例の期限を誤案内 | 同上 | 対照成功 / FAIL |

同型表現の全文検索は、開始HEADの追跡テキストの timeout_ms・旧期限・成功・実機・verified・検証済み・確認済み・未検証・未実施・工程表現・履歴不在の該当行を単位とし、160箇所点検 / 39箇所修正。残りは要件、契約、対象コミットを区別した既存結果、明記済みの未確認範囲である。READMEと全マスターの工程・時点依存の記述も点検する。旧期限値・旧分数の記述は残らず、マスターへの追記は現在の契約だけである。書込先の消費者はmake_manifest/register/download/installの4CLIを点検し、library=Trueの呼出しはregisterの2箇所だけ。既存回帰テストで他CLIの拒否と通常の登録を確認する。

設計書とマスター operations/security は、ツールの期限上限・許可先ディレクトリリンクの非変更拒否・履歴不在の案内を反映する。fbe640a の実機再実行とセキュリティ・契約レビュー round 3 の承認は下の追加記録を参照する。b7e51f5/a8d0ade の実機結果とは区別する。補助スクリプトと一時検証領域は除去済み。

## fbe640a の実機再実行（追加、2026-10-13）

提供元は orchestrator。対象機・固定サービス版は HOST-01 と同じ、ComfyUI 仮想環境の Python を `-I -B` で実行した。開始状態は導入済みの既存環境で、空の一時ライブラリだけをクリーン状態とする。時計時刻は未提供。

| ID / FR・AC・D | 対象 / 開始状態・手順 | 実際・終了コード / 未確認範囲 |
| --- | --- | --- |
| LIVE-DIAGNOSTIC-FBE640A / FR-5 / AC-5・D-1〜D-9 | fbe640a / 既存環境で検証。check_env.py | D-1〜D-9 すべて PASS、終了コード0 |
| LIVE-REGISTER-FBE640A / FR-7 / AC-7 | fbe640a / 空の一時配置先でクリーン状態を検証。register_dsh_workflow.py --data-dir <空の一時ディレクトリ> を2回 | 1回目は登録で0、2回目は「変更なし」で0 |
| LIVE-REGISTER-CONFLICT-FBE640A / FR-7 / AC-7 | fbe640a / 試作版の同名項目がある実機ライブラリ、既存環境で検証。register_dsh_workflow.py 引数なし | 「同名別内容（原本保持）」で5。差分所在を JSON で表示、ライブラリは変更なし |

fc87081 の `scripts/h3_common.py`（`request_json`）を使う実機の再実行は未実施。変更はワーカーの終了を確認してから結果を読む順序だけであり、fbe640a の実機結果とは区別する。

## fc87081 のローカル単体テスト・変異検証（2026-10-13）

orchestrator 提供結果: fc87081 の単体テストは114件成功。C3-01 の修正に対する変異検証は一時コピーで行い、対照実行は成功、以下6件すべて検出した。

| 変異 | 対象テスト | 提供結果 |
| --- | --- | --- |
| 結果の読み取りを生存確認より前に戻す | test_http_outcome_is_read_only_after_the_worker_finished | ERROR |
| 生存確認を外す | test_http_deadline_bounds_reads_inside_the_chunk_parser | ERROR |
| join の期限を外す | test_http_deadline_bounds_reads_inside_the_chunk_parser | FAIL |
| read() を read1() に戻す | test_http_body_shorter_than_content_length_is_a_failure | FAIL |
| HTTP プロトコル例外の分類を外す | test_http_protocol_errors_are_classified_not_raised | ERROR |
| 不正 JSON 本文の分類を外す | test_http_invalid_json_body_is_an_http_failure | FAIL |

## レビュー記録

Severity は提供されたものだけを記し、未提供は推測で補わない。

実装レビュー（Sol）:

round 4 で承認（必須修正ゼロ、対象 HEAD f5ee39f）。

| ID | Severity | 状態 |
| --- | --- | --- |
| C1-01〜C1-06 | 未提供 | 解消 |
| C2-01・C2-02 | 未提供 | 解消 |
| C3-01 | Low | 解消（round 4 で確認） |

セキュリティ・契約レビュー（Opus）:

round 3 で承認（必須修正ゼロ）。

| ID | Severity | 状態 |
| --- | --- | --- |
| S1-01・K1-01・K1-02 | 未提供 | 解消 |
| K2-01 | 未提供 | 解消 |
| S3-01・K3-01・K3-02 | 未提供（任意指摘） | 反映済み |
