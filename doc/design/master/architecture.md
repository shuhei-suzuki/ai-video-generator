# アーキテクチャ

## 構成と責務

ローカル単一利用者の macOS 26 / Apple Silicon / 128GB を対象とする。基準機は M5 Max。Comfy Desktop 1.1.6 は ComfyUI 0.39.2、Python 3.13.12、Manager V4.2.2 を含む。Ollama 0.33.3 は qwen3.8:27b-mlx を提供し、DeepSeek Harness Desktop 0.2.0-rc.2 と dsh-comfyui 0.5.4 がチャット経路を担う。対象機の ffmpeg は Homebrew 7.1.1、PyYAML は6.0.3、huggingface_hub は1.30.0である。ffprobe は ffmpeg と同じディレクトリの実行物を使う。

ComfyUI と Ollama の API はそれぞれ 127.0.0.1:8188 と 127.0.0.1:11434 で待ち受ける。Harness の待受ポートは動的で、ループバックのみを許す。認証・テナント・DB はない。

| 成果物 | 責務 |
| --- | --- |
| README / Harness 設定例 | 手動導入・本人同意・追記・運用案内 |
| scripts/h3_common.py | 配置・manifest・状態・URL・固定グラフ・動画・ライブラリ・外部処理の共通契約 |
| install_h3_node.py | 固定ノードと新規依存・モデル入口・venv bin の補助リンク |
| download_h3_models.py | 同意後の不足ファイルだけの取得・容量検査 |
| check_env.py | D-1〜D-9 の読み取り診断 |
| register_dsh_workflow.py | 原本を保持した追加・同名比較・原子置換 |
| submit_h3.py | 直接投入・完了待ち・履歴照合・保存動画検査 |
| tools/make_manifest.py | 固定 HF API からメタデータ一覧を生成・任意のサイズ照合 |
| tests/test_*.py | ネットワーク・GPU・実サービスを使わない故障注入 |

## 固定資材とデータフロー

ノードは Argus-AiTeam/ComfyUI-MiniMax-H3-MLX の ab1756d571ebb14fed3168354dae42966a04348b。モデルの repo/revision/include/local_dir は scripts/h3_common.py の MODELS と config/h3_models.manifest.json で照合する。

| モデル | 固定 SHA | 必須件数 / 合計バイト |
| --- | --- | --- |
| MiniMaxAI/MiniMax-H3 | 42ed227ee7df40d41602854ae760620d6eb651fe | FL2VA 指定6コンポーネント、66 / 77,770,657,762 |
| water1234/MiniMax-H3-MLX-Argus-Calibrated-INT8 | 70505b09c80e298e684d798d8e0f946937dcfad4 | 13 / 37,797,145,373 |
| water1234/MiniMax-H3-Turbo-v4-step600-EMA-MLX | 9771f9c606a50671bb94ee57191461602f02d1fc | 57 / 1,559,967,577 |

config の一覧がファイル名・バイトサイズの唯一の一覧である。合計は136件・117,127,770,712バイト。download と D-3 は同じ判定を使う。

workflows/minimax_h3_t2v_api.json がグラフの唯一の出どころである。node 1 ModelLoader → node 2 Generate → node 3 SaveVideo の接続である。ResultToComfyUI は D-2 の登録対象に含み、グラフでは使用しない。モデル・メモリ・キャッシュ・保存先・ffmpeg は固定入力であり、創作の公開値は prompt / width / height / duration_seconds / steps / seed の6項目だけである。

register はリポジトリのグラフそのままと公開6項目の実用既定値（prompt はグラフ由来、768×448・5秒・steps9・seed0 random）をライブラリへ保存する。直接 submit とグラフの既定値は64×64・1秒・steps5である。直接経路はグラフを複製して6項目だけ置換し、ComfyUI の /prompt に送る。チャット経路は Harness → Ollama の /v1/chat/completions → comfyui_workflow action=run → 登録 id を使う同期実行 → ComfyUI である。submit の verify は両経路の履歴をリポジトリと登録項目に照合する。公開値の違いは verify のグラフ合否に含めない。動画ツールの実行物は常にリポジトリの固定入力から導出する。

実行結果・開始状態・証跡・未確認範囲は [検証記録](../../verification/) に分離する。
