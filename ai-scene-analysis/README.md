# はじめに

このサンプルでは、Bitmovin Encoder API を使用して **AI Scene Analysis (AISA)** を有効にしたエンコードを行う方法を説明します。AI Scene Analysis はエンコード開始時に動画のシーンを AI で解析し、通常の HLS/DASH 出力に加えて、シーン記述メタデータやシーン境界での広告挿入用マーカーを自動生成する機能です。本サンプルでは Python を用いた実装を示します。

本サンプルディレクトリには、Per-Title H.264 + AAC (FMP4) の HLS/DASH エンコードに AI Scene Analysis を組み合わせた 1 サンプルを含みます。

```text
create_per_title_h264_aac_fmp4_dash_hls_with_ai_scene_analysis_on_aws.py
```

- 特記事項
  - 本サンプルでは AI Scene Analysis の以下 3 機能を 1 つのエンコードでまとめて有効化しています。
    - **asset description**: 動画のシーンを記述した JSON ファイルを出力先に生成します（`ai/` 配下）。
    - **automatic ad placement**: 検出した全シーン境界に対して、マニフェストへ SCTE cue tag を挿入します。
    - **output language codes**: AI が生成する記述の言語を指定します（本サンプルでは `ja`, `en`）。
  - AI Scene Analysis は現時点で **BETA エンコーダー**が必要です。サンプル内の `encoder_version='BETA'` は、機能が GA となった際に `'STABLE'` へ切り替えてください。最新状況は [Bitmovin Developer Docs](https://developer.bitmovin.com/) をご確認ください。
  - 映像は Per-Title テンプレート（単一ストリーム）で定義しており、実際の ABR ラダーはエンコード時に Bitmovin Per-Title が自動展開します。

## 前提条件

- AI Scene Analysis に対応した Bitmovin Encoder（BETA エンコーダー）
- AI Scene Analysis 関連クラスを含む Bitmovin Python SDK

## サンプルの利用方法

1. Bitmovin Encoder API Key と Organization ID を下記に設定します。
   ```python
   API_KEY = '<INSERT YOUR API KEY>'
   ORG_ID = '<INSERT YOUR ORG ID>'
   ```

2. 入出力の bucket の情報および入力ファイルパスを下記に設定します。
   ```python
   S3_INPUT_ACCESS_KEY = '<INSERT_YOUR_ACCESS_KEY>'
   S3_INPUT_SECRET_KEY = '<INSERT_YOUR_SECRET_KEY>'
   S3_INPUT_BUCKET_NAME = '<INSERT_YOUR_BUCKET_NAME>'

   INPUT_PATH = "{YOUR INPUT FILE PATH}"

   S3_OUTPUT_ACCESS_KEY = '<INSERT_YOUR_ACCESS_KEY>'
   S3_OUTPUT_SECRET_KEY = '<INSERT_YOUR_SECRET_KEY>'
   S3_OUTPUT_BUCKET_NAME = '<INSERT_YOUR_BUCKET_NAME>'
   ```

3. 必要に応じて、AI が生成する記述の出力言語（ISO 639-1）を変更します。
   ```python
   AI_OUTPUT_LANGUAGE_CODES = ["ja", "en"]
   ```

4. サンプルコードを実行し、エンコードを開始します。

## 処理結果例

エンコードが終了すると、Per-Title で展開された H.264 + AAC の出力が Fragmented MP4 形式で生成され、それを参照する HLS/DASH マニフェストがそれぞれ生成されます。あわせて AI Scene Analysis により、出力先の `ai/` 配下にシーン記述 JSON が生成され、HLS/DASH マニフェストにはシーン境界での SCTE cue tag が挿入されます。
