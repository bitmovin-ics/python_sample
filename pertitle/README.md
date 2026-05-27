# はじめに

このサンプルでは、Bitmovin Encoder API を使用して **Per-Title エンコーディング** を行う方法を説明します。Per-Title エンコーディングは、入力コンテンツの複雑さをエンコード時に解析し、タイトルごとに最適な ABR ラダー (解像度・ビットレートの組み合わせ) を自動的に決定する機能です。あらかじめ固定のラダーを用意するのではなく、Per-Title テンプレートを定義しておくことで、実際のレンディションをエンコーダーが自動展開します。本サンプルでは Python を用いたサンプルを説明します。

本サンプルディレクトリには複数のサンプルを含んでおり、それぞれ「コーデック (H.264 / H.265 / VP9)」「コンテナ (FMP4 / TS / WebM)」「パッケージング (DASH / HLS)」「入力構成 (単一入力 / 音声・映像を別入力)」「SDK の記述スタイル」が異なります。いずれも入出力に AWS S3 を利用し、`AWS_AP_NORTHEAST_1` リージョンでエンコードします。

1. H.264 + AAC の Per-Title サンプル群
   ```text
   create_per_title_encoding_h264_openapi.py
   create_per_title_encoding_h264_separate_av_inputs.py
   create_per_title_h264_aac_fmp4_ts_dash_hls_on_aws.py
   ```
2. H.265 (HEVC) + AAC の Per-Title サンプル
   ```text
   create_per_title_h265_aac_fmp4_dash_hls_on_aws.py
   ```
3. VP9 + AAC の Per-Title サンプル
   ```text
   create_per_title_vp9_aac_webm_fmp4_dash_on_aws.py
   ```

各サンプルの違いは以下のとおりです。

- `create_per_title_encoding_h264_openapi.py` — H.264 + AAC を FMP4 (DASH 用) と TS (HLS 用) に出力する Per-Title サンプルです。`StreamInput` に `input_id` / `input_path` / `selection_mode` を直接指定する OpenAPI / 旧来スタイルの記述で実装されており、出力パスは実行時刻 (`datetime`) を含むパスを使用します。マニフェスト生成は既定のジェネレーターを使用します。
- `create_per_title_encoding_h264_separate_av_inputs.py` — H.264 + AAC を FMP4 (DASH) と TS (HLS) に出力するサンプルですが、映像と音声を**別々の入力ファイル**から取り込みます (映像は video-only の mp4、音声は audio-only の wav を `IngestInputStream` で取得)。音声は 128kbps/48kHz と 64kbps/44.1kHz の 2 プロファイルを出力します。
- `create_per_title_h264_aac_fmp4_ts_dash_hls_on_aws.py` — H.264 + AAC を、DASH 用に FMP4、HLS 用に TS の 2 種類の Muxing として出力する標準的な Per-Title サンプルです (単一入力、マニフェストは `ManifestGenerator.V2`)。
- `create_per_title_h265_aac_fmp4_dash_hls_on_aws.py` — H.265 (HEVC) + AAC を FMP4 (CMAF) で出力するサンプルです。**単一の FMP4 Muxing を DASH と HLS の両方のマニフェストから参照**します。
- `create_per_title_vp9_aac_webm_fmp4_dash_on_aws.py` — VP9 を WebM コンテナで出力し、音声は AAC を FMP4 (sidecar) として出力する DASH サンプルです。映像 (WebM) と音声 (FMP4) を別コンテナで提供します。

- 特記事項
  - すべてのサンプルで映像ストリームを Per-Title テンプレート (`PER_TITLE_TEMPLATE` / `PER_TITLE_TEMPLATE_FIXED_RESOLUTION_AND_BITRATE`) として定義しています。`encoding_profiles_*` に並ぶ各エントリはあくまでテンプレートであり、実際の ABR ラダー (レンディション) はエンコード時に Bitmovin Per-Title が自動展開します。`PER_TITLE_TEMPLATE_FIXED_RESOLUTION_AND_BITRATE` のエントリには、`min` / `max` ビットレートや複雑度に基づくビットレート選択 (`BitrateSelectionMode.COMPLEXITY_RANGE`) などの追加設定を付与しています。
  - 展開後の各レンディションで出力パスが衝突しないよう、`{height}p_{bitrate}_{uuid}` のようなプレースホルダーを出力パスに用いています (`{uuid}` を含めることで、他のプレースホルダーが重複しても一意性が保たれます)。`create_per_title_encoding_h264_openapi.py` のみ `{height}p_{bitrate}` を使用しています。
  - 各サンプルとも、Per-Title のレンディション数はエンコード完了後に確定するため、エンコードを実行してから (`EncodingMode.THREE_PASS`) DASH / HLS マニフェストを生成しています。マニフェスト生成時は Muxing 一覧を走査し、Per-Title テンプレートの Stream (`PER_TITLE_TEMPLATE` を含む mode) はスキップして、展開済みのレンディションのみを Representation / Variant として追加します。
  - 映像コーデック設定には Hulu 推奨に準拠したチューニングを適用しています。H.264 / H.265 では解像度に応じて Profile や adaptive quantization strength を、VP9 では出力解像度に応じて `cpu_used` / `tile_columns` を切り替えています。
  - 本サンプル群では DRM は付与していません。DRM 付きの Per-Title サンプルは `drm/` ディレクトリを参照してください。

## 前提条件

- Bitmovin Encoder アカウントと API Key
- Per-Title エンコーディングを利用可能な Bitmovin Encoder
- 入出力に使用する AWS S3 バケット
- 音声・映像を別入力にするサンプル (`create_per_title_encoding_h264_separate_av_inputs.py`) では、映像のみ・音声のみのファイルをそれぞれ用意してください。

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
   音声・映像を別入力にするサンプルでは、単一の `INPUT_PATH` の代わりに映像用・音声用のパスをそれぞれ設定します。
   ```python
   VIDEO_INPUT_PATH = '/path/to/your/input/video_only.mp4'
   AUDIO_INPUT_PATH = '/path/to/your/input/audio_only.wav'
   ```

3. 必要に応じて、Per-Title テンプレート (ABR ラダーのもとになる定義) を変更します。各エントリはテンプレートであり、実際のレンディションはエンコード時に自動展開されます。
   ```python
   encoding_profiles_h264_pertitle = [
       {"height": 180, "profile": ProfileH264.BASELINE, "level": None, "mode": StreamMode.PER_TITLE_TEMPLATE, "aqs": 1.2},
       # ...
       {"height": 1080, "profile": ProfileH264.HIGH, "level": None, "mode": StreamMode.PER_TITLE_TEMPLATE, "aqs": 0.5},
   ]
   ```

4. サンプルコードを実行し、エンコードを開始します。

## 処理結果例

エンコードが終了すると、Per-Title によって展開された各レンディションが、サンプルのコーデック・コンテナに従って出力先 S3 に生成されます (H.264 サンプルは FMP4 と TS、H.265 サンプルは FMP4、VP9 サンプルは映像が WebM・音声が FMP4)。続いて、それらを参照するマニフェストが生成されます。DASH と HLS の両方を生成するサンプル (H.264 サンプル群と H.265 サンプル) と、DASH のみを生成するサンプル (VP9 サンプル) があります。

H.265 サンプルでは単一の FMP4 Muxing を DASH と HLS の双方から参照し、VP9 サンプルでは WebM の映像レンディションと FMP4 の音声を組み合わせて DASH を構成します。生成されたマニフェスト (`stream.mpd` / `stream.m3u8`) をプレイヤーで再生することで、Per-Title により最適化された ABR ストリーミングを確認できます。
