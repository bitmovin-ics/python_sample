# はじめに

このサンプルでは、Bitmovin Encoder API を使用して、WebVTT 字幕付きの HLS ストリームをエンコードする方法を説明します。映像（H.264）・音声（AAC ステレオ）のエンコードに加えて、入力として渡した WebVTT ファイル（`.vtt`）を字幕トラックとして取り込み、HLS マニフェストに字幕（Subtitles）メディアとして関連付けます。本サンプルでは Python を用いた実装を示します。

字幕は入力 bucket 上の WebVTT ファイルを `FileInputStream`（`file_type=FileInputStreamType.WEBVTT`）として取り込み、`WebVttConfiguration` と `ChunkedTextMuxing` を用いてセグメント化された WebVTT として出力します。HLS マニフェストでは `SubtitlesMediaInfo` を用いて字幕を `SUBTITLE` グループに登録します。

本サンプルディレクトリには 4 つのサンプルを含みます。サンプルの軸は、出力コンテナ（Fragmented MP4 / MP4）と出力先クラウド（AWS / Azure）の組み合わせです。

1. Fragmented MP4 で出力するサンプル
   ```text
   create_h264_aac_fmp4_fixed_bitrate_hls_vtt_on_aws.py
   create_h264_aac_fmp4_fixed_bitrate_hls_vtt_on_azure.py
   ```
2. MP4（HLS byte-range）で出力するサンプル
   ```text
   create_h264_aac_mp4_fixed_bitrate_hls_vtt_on_aws.py
   create_h264_aac_mp4_fixed_bitrate_hls_vtt_on_azure.py
   ```

- 特記事項
  - 字幕は新規生成ではなく、入力として用意済みの WebVTT ファイル（サンプルでは `sintel/subtitles_en.vtt`、言語 `en`）を取り込んでいます。映像・音声と同じ入力 bucket 上に配置されている前提です。
  - 字幕の Muxing には `ChunkedTextMuxing`（`segment_length=10.0`、セグメント命名 `en_webvtt_seg_%number%.vtt`）を使用し、HLS マニフェストには `SubtitlesMediaInfo`（`group_id="SUBTITLE"`、`uri="subtitles_en.m3u8"`）として登録しています。
  - 映像は固定ビットレート（fixed bitrate）の H.264 で、`PresetConfiguration.VOD_HIGH_QUALITY` を使用し、360p / 540p の 2 段を出力します。音声は AAC ステレオで 128kbps / 48kHz と 64kbps / 44.1kHz の 2 段を出力します。
  - コンテナによる違い:
    - FMP4 版は `Fmp4Muxing`（`segment_length=6`、`segment_%number%.m4s`）でセグメント化された Fragmented MP4 を出力します。
    - MP4 版は `Mp4Muxing` で単一ファイルの MP4 を出力し、`fragmented_mp4_muxing_manifest_type=FragmentedMp4MuxingManifestType.HLS_BYTE_RANGES`、`fragment_duration=4000`(ms) を指定することで、HLS から byte-range で参照できる形で配信します。
  - 本サンプルは HLS マニフェストのみを生成します（DASH は生成しません）。マニフェストはエンコード開始時に `StartEncodingRequest(vod_hls_manifests=..., manifest_generator=ManifestGenerator.V2)` でエンコードと同時に生成されます。
  - HLS のバージョンは `HLS_V4` を指定しています。
  - いずれのサンプルも DRM は付与していません。
  - クラウドによる違いは入出力ストレージ（AWS は S3、Azure は Blob Storage）と `cloud_region`（AWS は `AWS_AP_NORTHEAST_1`、Azure は `AZURE_JAPAN_EAST`）です。

## 前提条件

- Bitmovin Encoder（`encoder_version='STABLE'` を指定）
- WebVTT / ChunkedTextMuxing に対応した Bitmovin Python SDK

## サンプルの利用方法

1. Bitmovin Encoder API Key と Organization ID を下記に設定します。
   ```python
   API_KEY = '<INSERT YOUR API KEY>'
   ORG_ID = '<INSERT YOUR ORG ID>'
   ```

2. 入出力ストレージの情報および入力ファイルパスを設定します。利用するクラウドに応じて設定項目が異なります。

   AWS（S3）を利用するサンプルの場合:
   ```python
   S3_INPUT_ACCESS_KEY = '<INSERT_YOUR_ACCESS_KEY>'
   S3_INPUT_SECRET_KEY = '<INSERT_YOUR_SECRET_KEY>'
   S3_INPUT_BUCKET_NAME = '<INSERT_YOUR_BUCKET_NAME>'

   S3_OUTPUT_ACCESS_KEY = '<INSERT_YOUR_ACCESS_KEY>'
   S3_OUTPUT_SECRET_KEY = '<INSERT_YOUR_SECRET_KEY>'
   S3_OUTPUT_BUCKET_NAME = '<INSERT_YOUR_BUCKET_NAME>'
   ```

   Azure（Blob Storage）を利用するサンプルの場合:
   ```python
   AZURE_INPUT_ACCOUNT_NAME = '<INSERT_YOUR_AZURE_ACCOUNT_NAME>'
   AZURE_INPUT_ACCOUNT_KEY = '<INSERT_YOUR_AZURE_ACCOUNT_KEY>'
   AZURE_INPUT_CONTAINER_NAME = '<INSERT_YOUR_CONTAINER_NAME>'

   AZURE_OUTPUT_ACCOUNT_NAME = '<INSERT_YOUR_AZURE_ACCOUNT_NAME>'
   AZURE_OUTPUT_ACCOUNT_KEY = '<INSERT_YOUR_AZURE_ACCOUNT_KEY>'
   AZURE_OUTPUT_CONTAINER_NAME = '<INSERT_YOUR_CONTAINER_NAME>'
   ```

3. 入力となる映像ファイルと WebVTT 字幕ファイルのパスを設定します。サンプルでは Sintel の映像と英語字幕を指定しています。
   ```python
   INPUT_PATH = "sintel/Sintel.2010.1080p.mkv"
   INPUT_VTT_PATH = "sintel/subtitles_en.vtt"
   ```

4. 必要に応じて、出力エンコードの Profile を変更します。デフォルトでは 360p / 540p の H.264 と、128kbps / 48kHz・64kbps / 44.1kHz の AAC ステレオを出力するよう設定されています。
   ```python
   encoding_profiles_h264 = [
       dict(height=360, bitrate=300000, level=None, mode=StreamMode.STANDARD),
       dict(height=540, bitrate=600000, level=None, mode=StreamMode.STANDARD),
   ]

   encoding_profiles_aac = [
       dict(bitrate=128000, rate=48_000),
       dict(bitrate=64000, rate=44_100)
   ]
   ```

5. サンプルコードを実行し、エンコードを開始します。エンコードの開始と同時に HLS マニフェストの生成が実行されます。

## 処理結果例

エンコードが終了すると、H.264 + AAC の出力（FMP4 版は Fragmented MP4、MP4 版は HLS byte-range 用の MP4）が生成され、それを参照する HLS マニフェスト（`stream.m3u8`）が生成されます。マニフェストには映像・音声に加えて、`SUBTITLE` グループの WebVTT 字幕（`subtitles_en.m3u8`、言語 `en`）が含まれ、対応プレイヤーで字幕表示を切り替えて再生できます。
