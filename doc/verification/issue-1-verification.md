# 検証記録

## 読み方・対応

要件は [要件書](../requirements/issue-1-requirements.md)、決定は [設計書](../design/issue-1-design.md)、現在の契約は [architecture](../design/master/architecture.md) / [operations](../design/master/operations.md) / [security](../design/master/security.md) を参照する。提供元は2026-10-12の対象機に関する orchestrator の実機確認事実である。原ログ・動画・個人パスは収録しない。終了コードや日時・prompt_id が提供されない場合は未提供と記し、推測で補わない。以下の既存実機成功を新しいスクリプトの実機合格とは扱わない。

各レコードは ID / FR・AC・D / 成果物 / 要件節 / Issue設計節 / マスター節 / 日付・時刻 / 固定版・条件 / 開始状態 / 状態3区分 / 手順 / 期待・実際 / 終了コード / 証跡 / 対処 / 未確認範囲を持つ。クリーンはその導入対象と取得途中データが存在しない開始状態である。

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
| 対処 / 未確認範囲 | 別配置は明示CLI / 新規resolverの実機・ffprobe版・他機体 |

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
| 対処 / 未確認範囲 | 競合は本人の退避、pip check確認 / 新規install・downloadの実機、R・余裕・実測free・有効free・Nの実数、キャッシュ/生成物追加容量 |

AC-3 の容量不足注入は「必要量の上書き」から **空き容量側を下げる `min(実測,N)`** に置換する。manifest由来の必要量を維持し、不足だけを再現してゲートを緩めないためである。R=0の完了済み経路とTurbo初回・2回目の新規CLI実機は下の未検証枠で記録する。

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
| 対処 / 未確認範囲 | GUI PATHのffmpeg解決失敗には固定絶対パスとvenv binリンク / 新規submitの実機・prompt_id・原グラフ全文・同サイズ改変 |

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
| 対処 / 未確認範囲 | 共用を減らす・生成期限を明示 / 新規submit実機・prompt_id・原文・他条件の再現率 |

## チャット生成・提供元

| フィールド | 記録 |
| --- | --- |
| ID / FR・AC・D | CHAT-SMOKE / FR-4・FR-7・FR-8 / AC-4・AC-7 / D-4〜D-7 |
| 成果物 / 要件節 | register・submit・設定例・README / FR-4・FR-7・AC-7 |
| Issue設計節 / マスター節 | register・submit・検証記録 / architecture データフロー・operations 保存 |
| 日付・時刻 / 固定版・条件 | 2026-10-12、HOST-01構成、qwen3.8:27b-mlx、スモーク64×64・1秒・steps5。履歴seed3105209621。プロンプトは指定あり（原文未提供） |
| 開始状態 / 状態3区分 | desktop設定・ダミーキー・プラグイン・試作のライブラリ登録済み、Harness再起動後 / 既存環境で検証 |
| 手順 | 登録ワークフロー一覧と対象ノード取得、ライブラリidから同期実行、実投入グラフを元データで照合、動画検査と同時刻Ollamaログを照合 |
| 期待・実際 | 成功61秒。呼出し comfyui_workflow action=run、ライブラリid、parametersにprompt/width/height/duration_seconds/steps、mode=sync、timeout_ms=900000。履歴の3ノード構成と固定入力が登録グラフと一致、差分は公開6項目だけ。seedはランダム化。H.26464×64・39フレーム＋AAC stereo、MP4存在、全デコード成功 |
| 終了コード / 証跡 | ツール・デコードの数値未提供 / 同時刻のOllama POST /v1/chat/completions 13:10:37・13:11:12・13:12:08・13:12:22、4件とも200。元グラフ照合の提供結果。生ログ・id・原グラフ全文は未提供 |
| 対処 / 未確認範囲 | 同期を使い、完了は同じComfyUI起動中の履歴で確認 / 新規register/verify実機、原グラフ全文の収録、async、ツール承認機構 |

| フィールド | 記録 |
| --- | --- |
| ID / FR・AC・D | CHAT-15S / FR-6・FR-7・FR-8 / AC-6・AC-7参考・AC-12 |
| 成果物 / 要件節 | README・submit / 確認済み事実・メモリ |
| Issue設計節 / マスター節 | submit・検証記録 / operations 生成条件 |
| 日付・時刻 / 固定版・条件 | 2026-10-12、HOST-01構成、チャット448×768・15秒・steps9（seed・prompt原文未提供） |
| 開始状態 / 状態3区分 | チャット環境導入済み / 既存環境で検証 |
| 手順 | チャットから生成、チャット期限後もComfyUIの継続・完了を確認 |
| 期待・実際 | ComfyUI計測48分で完了成功。H.264448×768・361フレーム＋AAC stereo、MP4存在、全デコード成功。チャット同期は15分期限のため先にタイムアウトしうるが生成は継続 |
| 終了コード / 証跡 | 数値未提供・デコード成功 / 提供された15秒完了結果（40分前後の途中観測を完了値に使わない） |
| 対処 / 未確認範囲 | 指示文に900000ms期限を明示。再投入せず出力/履歴を確認。submitは7200秒 / 新規CLI・正確な公開6値・繰返し成功率 |

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
| 対処 / 未確認範囲 | 既存設定を保持し再適用、本人の手動例外 / 上流未マージ修正は未適用・async未検証・新規D-6/D-7実機 |

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
| 対処 / 未確認範囲 | 外部公開禁止・CORS/--listen禁止 / 新規D-8/D-9全PID検査・UDP |

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

## 新規スクリプトの実機検証枠

次の表の **各行を独立したレコード**とし、共通フィールドを次のように定める。日付・時刻=未実施、固定版・条件=HOST-01と固定SHA、開始状態=表記の計画（実測未記録）、状態3区分=**未検証（実装後に orchestrator が実施）**、期待・実際=期待は表、実際は未実施、終了コード=未取得、証跡=未取得、未確認範囲=当該新規CLIの実機動作全体。成功と読み替えない。

| ID / FR・AC・D | 成果物 / 要件節 / Issue設計節 / マスター節 | 開始状態・手順 | 期待 / 対処 |
| --- | --- | --- | --- |
| LIVE-INSTALL / FR-3 / AC-3 | install / FR-3 / install / operations 非変更 | 当該ノード無し・ComfyUI停止、固定requirements導入 | 新規依存のみ・既存版不変・pip check / 競合は保持 |
| LIVE-INSTALL-CONFIG / FR-3 / AC-3 | install / 権限・FR-3 / install / security 配布 | pip設定ファイルとgit設定に別取得元がある状態、install | 明示PyPI・固定GitHubから変わらない / 子隔離を確認 |
| LIVE-TURBO / FR-3 / AC-3・D-3 | download / AC-3 / download / operations 非変更 | tempfileの空の配置先、本人同意のTurbo取得→同条件2回目 | 初回0・全件サイズ一致、2回目0・変更/再取得無し / R/free/N/余裕/mtimeを記録 |
| LIVE-DIAGNOSTIC / FR-5 / AC-5・D-1〜D-9 | check / 診断 / check / operations 診断 | 導入・登録・3サービス起動済み、全診断 | 全PASS・終了0 / 該当DのREADME対処表 |
| LIVE-DIRECT-SMOKE / FR-6 / AC-6・AC-11 | submit・workflow / FR-6 / submit / operations 保存 | 稼働ComfyUI、スモーク投入 | 完了・出力存在・H.264/AAC・64×64・全デコード0 / エラー6・期限7・不合格8 |
| LIVE-DIRECT-5S / FR-6 / AC-6 | submit / AC-6 / submit / operations 保存 | 768×448・5秒・steps9・seed42投入 | 同じ動画検査合格 / 状態・メモリ・期限確認 |
| LIVE-CHAT / FR-4・FR-7 / AC-4・AC-7 | register・submit・設定例 / FR-7 / register・submit / architecture フロー | 登録→チャット同期スモーク→verify | ツールid/引数・実投入グラフ・6項目・動画・Ollamaログ照合 / 任意投入を区別 |
| LIVE-CHAT-REREGISTER / FR-7 / AC-7・D-4 | register・check / 冪等性・FR-7 / register・check / operations 登録 | チャット生成後 register再実行・D-4診断 | register0・バイト不変・D-4 PASS / 別内容はパネル削除再登録 |
| LIVE-MEMORY / FR-8 / AC-12 | README・本記録 / メモリ / 検証記録 / operations 生成 | チャット前後・稼働モデル・時計時刻を記録 | 文脈・Qwen/全体使用量の追跡 / 文脈・モデル・同時実行削減 |

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
| 対処 / 未確認範囲 | 必須故障の修正と再実行 / 実機枠の全項目、独立レビュー、Python3.11での実行（コードは3.11以上対応） |

ローカル結果: `python3 -m unittest discover -s tests -v` は84件成功、失敗0・エラー0・スキップ0、終了0（Python3.14.6）。このうち1件は下の20変異を別プロセスの単体テストで検査する。全CLI6本の `-I --help` も成功。PyYAML 不在時は3件のYAMLテストを理由付きスキップする。hubはスタブを使うため不在でもテスト可能で、hub不在/旧版の終了1を別途注入する。

変異結果: 以下20件すべてで指定テストが失敗する。構文をcompileで確認してから実行し、構文エラー・ネットワーク失敗・スキップを検出成功に数えない。原実装の内容不変と一時コピーの削除・不在をテストで確認する。

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
| 対処 / 未確認範囲 | 個人パスは~、秘密は収録しない / PR・Issue・独立レビュー未実施 |

公開ファイル一覧は冒頭の対応表と README、.gitignore、configの3資材、workflow、scriptsの6ファイル、tools/make_manifest.py、tests/support.py・test_common.py・test_download.py・test_install.py・test_check_env.py・test_submit.py・test_register.py・test_manifest_and_docs.py・test_mutations.py、要件書・Issue設計書・マスター3書・本記録である。新規26ファイルと設計書1ファイルの変更を引き渡す。テスト用一時領域は tempfile の context/cleanup で削除し、変異コピーも終了後不在を確認する。既存worktreeは成果物引渡しのため保持し、commit/push・その後のクリーンアップはorchestratorが担当する。
