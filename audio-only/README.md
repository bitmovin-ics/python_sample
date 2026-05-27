# はじめに

このサンプルでは、Bitmovin Encoder API を使用して **音声のみ (Audio-Only)** の AAC エンコードを行い、HLS/DASH で配信する方法を説明します。映像を含まず音声トラックのみを Fragmented MP4 でエンコードし、それを参照する HLS/DASH マニフェストを生成するため、音楽配信やポッドキャスト、ラジオ的なユースケースに利用できます。本サンプルでは Python を用いた実装を示します。

本サンプルディレクトリには、音声のみの AAC エンコードを行うサンプルを 1 つ含みます。

1. 音声のみ (AAC) の FMP4 を HLS/DASH で配信するサンプル
   ```text
   create_aac_only_fmp4_hls_dash.py
   ```

- 特記事項
  - 入力ファイルから音声トラックを `IngestInputStream` (`StreamSelectionMode.AUDIO_RELATIVE`) で取り込み、映像ストリームは作成しません。サンプルでは MP3 ファイルを入力として想定しています。
  - 音声は AAC ステレオ (`AacChannelLayout.CL_STEREO`)、デフォルトでは 128kbps / 48kHz の 1 プロファイルのみを Fragmented MP4 形式で出力します。
  - マニフェストはエンコード完了後に生成します。DASH では音声のみの AdaptationSet を、HLS では音声レンディション (`AudioMediaInfo`) のみを定義します（映像 variant は含みません）。
  - クラウドリージョンは `AWS_AP_NORTHEAST_1`、encoder は `STABLE`、マニフェスト生成には `ManifestGenerator.V2` を使用します。

## 前提条件

- Bitmovin Encoder を利用可能な Bitmovin アカウント
- Bitmovin Python SDK

## サンプルの利用方法

1. Bitmovin Encoder API Key と Organization ID を下記に設定します。
   ```python
   API_KEY = '<INSERT YOUR API KEY>'
   ORG_ID = '<INSERT YOUR ORG ID>'
   ```

2. 入出力の bucket の情報および入力ファイルパスを下記に設定します。入力には音声トラックを含むファイル（サンプルでは MP3）を指定します。
   ```python
   S3_INPUT_ACCESS_KEY = '<INSERT_YOUR_ACCESS_KEY>'
   S3_INPUT_SECRET_KEY = '<INSERT_YOUR_SECRET_KEY>'
   S3_INPUT_BUCKET_NAME = '<INSERT_YOUR_BUCKET_NAME>'

   AUDIO_INPUT_PATH = '/path/to/your/input/audio.mp3'

   S3_OUTPUT_ACCESS_KEY = '<INSERT_YOUR_ACCESS_KEY>'
   S3_OUTPUT_SECRET_KEY = '<INSERT_YOUR_SECRET_KEY>'
   S3_OUTPUT_BUCKET_NAME = '<INSERT_YOUR_BUCKET_NAME>'
   ```

3. 必要に応じて、出力する音声プロファイル（ビットレート・サンプリングレート）を変更します。デフォルトでは 128kbps / 48kHz の 1 プロファイルのみを出力します。
   ```python
   audio_encoding_profiles = [
       dict(bitrate=128000, rate=48_000)
   ]
   ```

4. サンプルコードを実行し、エンコードを開始します。

## 処理結果例

エンコードが終了すると、音声のみの AAC 出力が Fragmented MP4 形式で生成され、それを参照する HLS/DASH マニフェストがそれぞれ生成されます。映像トラックは含まれず、音声のみの再生が可能なストリームが出力されます。
