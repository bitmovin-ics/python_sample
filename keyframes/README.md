# はじめに

このサンプルでは、Bitmovin Encoder API を使用して、API で keyframe（キーフレーム）を明示的に指定し、その位置でセグメントを区切るエンコードを行う方法を説明します。広告挿入（ad opportunity）などの特定の時刻でセグメント境界を強制的に発生させたい場合に利用するパターンです。本サンプルでは Python を用いた実装を示します。

通常、Fragmented MP4 のセグメントは `segment_length` で指定した一定間隔で区切られますが、`Keyframe` リソースを `segment_cut=True` で作成すると、指定した時刻に追加のキーフレームを挿入し、そこでセグメントを分割できます。これにより、規則的なセグメントグリッドとは別に、任意の時刻でセグメント境界を確実に発生させることができます。本サンプルでは H.264 + AAC ステレオを Fragmented MP4 で Muxing し、HLS / DASH の両マニフェストを生成します。

本サンプルディレクトリには、keyframe によるセグメント分割を扱う 2 つのサンプルを含みます。両者の違いは、`segment_cut=True` で指定する keyframe の時刻が、規則的なセグメント境界（および keyframe interval）と整列するか否かにあります。

1. segment aligned — keyframe 指定位置がセグメント境界と整列するサンプル
   ```text
   create_h264_aac_fmp4_hls_dash_with_keyframes_segment_aligned.py
   ```
2. segment non-aligned — keyframe 指定位置がセグメント境界と整列しないサンプル
   ```text
   create_h264_aac_fmp4_hls_dash_with_keyframes_segment_non_aligned.py
   ```

- 特記事項
  - 両サンプルとも、広告挿入位置として `ad_opportunity_placements = [0.32, 19.2]`（秒）を定義し、各時刻に対して `Keyframe(time=..., segment_cut=True)` を作成しています。`segment_cut=True` により、その時刻でセグメントが区切られます。
  - H.264 の Codec Configuration では `min_keyframe_interval` と `max_keyframe_interval` を同じ値に設定し、一定間隔でキーフレームが入る（固定 GOP の）構成にしています。
  - segment aligned サンプルでは、`segment_length = 5.76` 秒、`key_frame_interval = 1.92` 秒（fps=25）と設定されています。`segment_length` は `key_frame_interval` の整数倍（5.76 = 1.92 × 3）であり、規則的なセグメント境界がキーフレーム間隔のグリッド上に乗るように設計されています。出力 Profile は 360p / 540p / 1080p の 3 段です。
  - segment non-aligned サンプルでは、`segment_length = 6` 秒、`key_frame_interval = 2` 秒（fps=25）と設定されています。`ad_opportunity_placements` に指定した時刻（0.32, 19.2）は keyframe interval（2 秒）や segment length（6 秒）の整数倍ではないため、`segment_cut=True` によって挿入される分割位置が規則的なセグメントグリッドと整列しません。出力 Profile は 360p / 540p の 2 段です。
  - いずれのサンプルも DRM は付与していません。
  - マニフェスト生成には `ManifestGenerator.V2` を使用しています。

## 前提条件

- Bitmovin Encoder（`encoder_version='STABLE'` を指定）
- Keyframe API（`encoding.encodings.keyframes`）に対応した Bitmovin Python SDK

## サンプルの利用方法

1. Bitmovin Encoder API Key と Organization ID を下記に設定します。
   ```python
   API_KEY = '<INSERT YOUR API KEY>'
   ORG_ID = '<INSERT YOUR ORG ID>'
   ```

2. 入出力の bucket の情報および入力ファイルパスを下記に設定します。入出力ともに AWS S3 を利用します。
   ```python
   S3_INPUT_ACCESS_KEY = '<INSERT_YOUR_ACCESS_KEY>'
   S3_INPUT_SECRET_KEY = '<INSERT_YOUR_SECRET_KEY>'
   S3_INPUT_BUCKET_NAME = '<INSERT_YOUR_BUCKET_NAME>'

   INPUT_PATH = "{YOUR INPUT FILE PATH}"  # 例: "big_buck_bunny_1080p_h264.mov"

   S3_OUTPUT_ACCESS_KEY = '<INSERT_YOUR_ACCESS_KEY>'
   S3_OUTPUT_SECRET_KEY = '<INSERT_YOUR_SECRET_KEY>'
   S3_OUTPUT_BUCKET_NAME = '<INSERT_YOUR_BUCKET_NAME>'
   ```

3. 必要に応じて、セグメント長・キーフレーム間隔・フレームレート、およびセグメントを区切る位置（広告挿入位置）を変更します。下記は segment aligned サンプルの例です。
   ```python
   # Ad opportunity placements (expressed in seconds)
   ad_opportunity_placements = [0.32, 19.2]

   # Segment length in seconds
   segment_length = 5.76

   # Key frame interval in seconds
   key_frame_interval = 1.92

   # Frame rate
   fps = 25
   ```

4. 必要に応じて、出力エンコードの Profile を変更します。デフォルトでは、segment aligned サンプルは 360p / 540p / 1080p、segment non-aligned サンプルは 360p / 540p の H.264 と、128kbps / 48kHz の AAC ステレオを出力するよう設定されています。
   ```python
   encoding_profiles_h264 = [
       dict(height=360, bitrate=300000, level=None, mode=StreamMode.STANDARD),
       dict(height=540, bitrate=600000, level=None, mode=StreamMode.STANDARD),
       dict(height=1080, bitrate=1000000, level=None, mode=StreamMode.STANDARD),
   ]

   encoding_profiles_aac = [
       dict(bitrate=128000, rate=48_000),
   ]
   ```

5. サンプルコードを実行し、エンコードを開始します。エンコード完了後に HLS / DASH マニフェストの生成が実行されます。

## 処理結果例

エンコードが終了すると、H.264 + AAC の出力が Fragmented MP4 形式で生成され、それを参照する HLS / DASH マニフェスト（`stream.m3u8` / `stream.mpd`）がそれぞれ生成されます。`segment_cut=True` で指定した時刻ではセグメントが区切られるため、生成された各 media playlist / representation のセグメント境界を確認すると、指定した広告挿入位置でセグメントが分割されていることが確認できます。

segment aligned サンプルでは、指定したセグメント境界がキーフレーム間隔のグリッド上に乗る構成のためセグメント長が比較的揃った出力になります。一方 segment non-aligned サンプルでは、`segment_cut` による分割位置が規則的なセグメントグリッドと整列しないため、その前後で通常より短いセグメントが発生します。
