# はじめに

このサンプルでは、Bitmovin Encoder API を使用して **Deinterlace (インターレース解除) フィルター** を適用したエンコードを行う方法を説明します。インターレース素材（フィールド構造を持つ映像）を入力とし、Deinterlace フィルターで progressive へ変換しながら H.264 + AAC の Fragmented MP4 を生成し、HLS/DASH で配信します。本サンプルでは Python を用いた実装を示します。

本サンプルディレクトリには、Deinterlace フィルターを適用したサンプルを 1 つ含みます。

1. Deinterlace フィルター適用 H.264 + AAC (FMP4) を HLS/DASH で配信するサンプル
   ```text
   create_h264_aac_fmp4_hls_dash_with_deinterlace_filter.py
   ```

- 特記事項
  - 映像ストリームに `DeinterlaceFilter` を `StreamFilter` (position=0) として適用しています。フィルターの設定は次の通りです。
    - `parity=PictureFieldParity.AUTO`: フィールドの優先順位（パリティ）を自動判定します。
    - `mode=DeinterlaceMode.FRAME`: フレーム単位でインターレース解除を行います。
    - `frame_selection_mode=DeinterlaceFrameSelectionMode.ALL`: すべてのフレームを処理対象とします。
    - `auto_enable=DeinterlaceAutoEnable.META_DATA_AND_CONTENT_BASED`: 入力のメタデータと映像内容の両方からインターレースを判定し、必要な場合のみフィルターを有効化します。
  - 映像は H.264 (`PresetConfiguration.VOD_STANDARD`)、デフォルトでは 1080p / 2Mbps の 1 プロファイル、音声は AAC ステレオ 128kbps / 48kHz を Fragmented MP4 形式で出力します。
  - クラウドリージョンは `CloudRegion.AUTO`、encoder は `STABLE` を使用します。
  - マニフェスト (HLS/DASH) はエンコード開始リクエスト (`StartEncodingRequest`) に渡して `ManifestGenerator.V2` で生成します。HLS では映像 variant に audio group `audio` を紐付けます。

## 前提条件

- Bitmovin Encoder を利用可能な Bitmovin アカウント
- Bitmovin Python SDK

## サンプルの利用方法

1. Bitmovin Encoder API Key と Organization ID を下記に設定します。
   ```python
   API_KEY = '<INSERT YOUR API KEY>'
   ORG_ID = '<INSERT YOUR ORG ID>'
   ```

2. 入出力の bucket の情報および入力ファイルパスを下記に設定します。入力にはインターレース素材を指定します。
   ```python
   S3_INPUT_ACCESS_KEY = '<INSERT YOUR ACCESS KEY>'
   S3_INPUT_SECRET_KEY = '<INSERT YOUR SECRET KEY>'
   S3_INPUT_BUCKET_NAME = '<INSERT YOUR BUCKET NAME>'

   INPUT_PATH = "<INSERT YOUR INPUT PATH>"

   S3_OUTPUT_ACCESS_KEY = '<INSERT YOUR ACCESS KEY>'
   S3_OUTPUT_SECRET_KEY = '<INSERT YOUR SECRET KEY>'
   S3_OUTPUT_BUCKET_NAME = '<INSERT YOUR BUCKET NAME>'
   ```

3. 必要に応じて、出力エンコードのプロファイルを変更します。デフォルトでは映像は 1080p / 2Mbps の 1 プロファイル、音声は 128kbps / 48kHz のみを出力します。
   ```python
   encoding_profiles_h264 = [
       dict(height=1080, bitrate=2_000_000, level=None, mode=StreamMode.STANDARD),
   ]

   encoding_profiles_aac = [
       dict(bitrate=128000, rate=48_000)
   ]
   ```

4. 必要に応じて、Deinterlace フィルターのパラメータを変更します。
   ```python
   deinterlace_filter = bitmovin_api.encoding.filters.deinterlace.create(
       deinterlace_filter=DeinterlaceFilter(
           parity=PictureFieldParity.AUTO,
           mode=DeinterlaceMode.FRAME,
           frame_selection_mode=DeinterlaceFrameSelectionMode.ALL,
           auto_enable=DeinterlaceAutoEnable.META_DATA_AND_CONTENT_BASED
       )
   )
   ```

5. サンプルコードを実行し、エンコードを開始します。

## 処理結果例

エンコードが終了すると、Deinterlace フィルターで progressive 化された H.264 + AAC の出力が Fragmented MP4 形式で生成され、それを参照する HLS/DASH マニフェストがそれぞれ生成されます。インターレース素材特有のフィールドのちらつきが解消された映像が再生できます。
