# はじめに

このサンプルでは、Bitmovin Encoder API を使用して、固定ビットレート (fixed-bitrate) の ABR エンコードを行う方法を説明します。H.264 映像と AAC ステレオ音声を、解像度・ビットレートを明示的に指定した複数のレンディションにエンコードし、それらを参照する HLS/DASH マニフェストを生成します。Per-Title のように品質に応じてビットレートを自動最適化するのではなく、各レンディションのビットレートを固定値で指定する構成です。本サンプルでは Python を用いた実装を示します。

本サンプルディレクトリには 12 個のサンプルを含んでいます。いずれも H.264 (FMP4 または MP4) + AAC ステレオの固定ビットレートエンコードという基本構成は共通で、出力先クラウド (AWS / Azure)、パッケージング (HLS のみ / HLS + DASH)、コンテナ (Fragmented MP4 / MP4)、オプション機能 (StreamCondition、サムネイル生成、SFTP 出力) の組み合わせで分かれています。目的に合わせて以下から選択してください。

1. HLS のみ・Fragmented MP4 (基本構成)
   ```text
   create_h264_aac_fmp4_fixed_bitrate_hls_on_aws.py
   create_h264_aac_fmp4_fixed_bitrate_hls_on_azure.py
   ```
2. HLS のみ・Fragmented MP4・StreamCondition 付き
   ```text
   create_h264_aac_fmp4_fixed_bitrate_hls_with_streamcondition_on_aws.py
   create_h264_aac_fmp4_fixed_bitrate_hls_with_streamcondition_on_azure.py
   ```
3. HLS + DASH・Fragmented MP4・StreamCondition 付き
   ```text
   create_h264_aac_fmp4_fixed_bitrate_dash_hls_with_streamcondition_on_aws.py
   create_h264_aac_fmp4_fixed_bitrate_dash_hls_with_streamcondition_on_azure.py
   ```
4. HLS + DASH・Fragmented MP4・StreamCondition + サムネイル生成付き
   ```text
   create_h264_aac_fmp4_fixed_bitrate_dash_hls_with_streamcondition_with_thumbnail_on_aws.py
   create_h264_aac_fmp4_fixed_bitrate_dash_hls_with_streamcondition_with_thumbnail_on_azure.py
   ```
5. HLS のみ・MP4 (HLS byte-range 方式)
   ```text
   create_h264_aac_mp4_fixed_bitrate_hls_on_aws.py
   create_h264_aac_mp4_fixed_bitrate_hls_on_azure.py
   ```
6. HLS + DASH・Fragmented MP4・SFTP 出力
   ```text
   create_h264_aac_fmp4_dash_hls_sftp_output_just_in_time.py
   create_h264_aac_fmp4_dash_hls_sftp_output_post_encoding.py
   ```

上記のうち 1〜5 は、出力先クラウドの違いで AWS 版 (`_on_aws.py`、入出力ともに Amazon S3) と Azure 版 (`_on_azure.py`、入出力ともに Azure Blob Storage) の 2 ファイルがペアで用意されています。6 の SFTP 出力サンプルは、入力は S3、出力は SFTP サーバーで、マニフェスト生成のタイミングが異なる 2 種類 (just-in-time / post-encoding) を用意しています。

- 特記事項
  - 映像は 360p (300kbps) と 540p (600kbps) の 2 レンディション、音声は 128kbps/48kHz と 64kbps/44.1kHz の 2 レンディションをいずれも固定ビットレート (`StreamMode.STANDARD`) で出力します。映像コーデックには `PresetConfiguration.VOD_HIGH_QUALITY` を指定しています。なお SFTP 出力サンプル (6 番) のみ、映像 360p (300kbps) 1 本・音声 64kbps 1 本のシンプルな構成です。
  - **StreamCondition**: 音声ストリームに `Condition(attribute="AUDIOSTREAMCOUNT", operator=GREATER_THAN, value="0")` を付与し、入力に音声トラックが 1 つ以上存在する場合のみ音声ストリームを生成する条件分岐です。音声を持たない入力でもエラーにせず処理を継続させたい場合に利用します。StreamCondition 付きサンプル (2〜4 番) で有効化しています。
  - **サムネイル生成**: 540p の映像ストリームを対象に、`THUMBNAIL_POSITION_IN_SECONDS = [10]` で指定した再生位置 (10 秒地点) のサムネイル画像 (JPEG) を `thumbnail/` 配下に出力します。`positions` に複数の秒数を指定すれば、複数枚のサムネイルを生成できます。サムネイル付きサンプル (4 番) で有効化しています。
  - **MP4 (HLS byte-range)**: MP4 サンプル (5 番) では `Fmp4Muxing` ではなく `Mp4Muxing` を使用し、`fragmented_mp4_muxing_manifest_type=FragmentedMp4MuxingManifestType.HLS_BYTE_RANGES`、`fragment_duration=4000` を指定しています。これにより、セグメントを多数のファイルに分割せず、レンディションごとに単一の MP4 ファイルを出力したうえで、HLS マニフェストからバイトレンジ参照で再生する構成になります。
  - **SFTP 出力 (just-in-time / post-encoding)**: 出力先に `SftpOutput` を使用するサンプル (6 番) では、マニフェスト生成のタイミングが 2 通りあります。
    - **just-in-time** (`..._just_in_time.py`): エンコード開始前に HLS/DASH マニフェストを定義し、`StartEncodingRequest` の `vod_hls_manifests` / `vod_dash_manifests` に渡したうえで `ManifestGenerator.V2` を指定します。エンコードと同時にマニフェストが生成されます。
    - **post-encoding** (`..._post_encoding.py`): まず `StartEncodingRequest()` でエンコードのみを実行し、エンコード完了後にあらためて HLS/DASH マニフェストを定義し、`manifests.hls.start()` / `manifests.dash.start()` を個別に呼び出して生成します。
  - 本サンプルでは DRM は付与していませんが、DRM ライセンスをお持ちの場合は DRM をかけることもできます。

## 前提条件

- Bitmovin Encoder

## サンプルの利用方法

1. Bitmovin Encoder API Key と Organization ID を下記に設定します。
   ```python
   API_KEY = '<INSERT YOUR API KEY>'
   ORG_ID = '<INSERT YOUR ORG ID>'
   ```

2. 入出力の情報および入力ファイルパスを設定します。設定する内容はサンプルの種類によって異なります。

   AWS 版サンプル (`_on_aws.py`) では、入出力ともに Amazon S3 の認証情報とバケット名を設定します。
   ```python
   S3_INPUT_ACCESS_KEY = '<INSERT_YOUR_ACCESS_KEY>'
   S3_INPUT_SECRET_KEY = '<INSERT_YOUR_SECRET_KEY>'
   S3_INPUT_BUCKET_NAME = '<INSERT_YOUR_BUCKET_NAME>'

   INPUT_PATH = "sintel/Sintel.2010.1080p.mkv"

   S3_OUTPUT_ACCESS_KEY = '<INSERT_YOUR_ACCESS_KEY>'
   S3_OUTPUT_SECRET_KEY = '<INSERT_YOUR_SECRET_KEY>'
   S3_OUTPUT_BUCKET_NAME = '<INSERT_YOUR_BUCKET_NAME>'
   ```

   Azure 版サンプル (`_on_azure.py`) では、入出力ともに Azure Blob Storage のアカウント名・アカウントキー・コンテナ名を設定します。
   ```python
   AZURE_INPUT_ACCOUNT_NAME = '<INSERT_YOUR_AZURE_ACCOUNT_NAME>'
   AZURE_INPUT_ACCOUNT_KEY = '<INSERT_YOUR_AZURE_ACCOUNT_KEY>'
   AZURE_INPUT_CONTAINER_NAME = '<INSERT_YOUR_CONTAINER_NAME>'

   INPUT_PATH = "sintel/Sintel.2010.1080p.mkv"

   AZURE_OUTPUT_ACCOUNT_NAME = '<INSERT_YOUR_AZURE_ACCOUNT_NAME>'
   AZURE_OUTPUT_ACCOUNT_KEY = '<INSERT_YOUR_AZURE_ACCOUNT_KEY>'
   AZURE_OUTPUT_CONTAINER_NAME = '<INSERT_YOUR_CONTAINER_NAME>'
   ```

   SFTP 出力サンプル (6 番) では、入力は S3、出力は SFTP サーバーのホスト名・ユーザー名・パスワード・ポート番号を設定します。
   ```python
   S3_INPUT_ACCESS_KEY = '<INSERT_YOUR_ACCESS_KEY>'
   S3_INPUT_SECRET_KEY = '<INSERT_YOUR_SECRET_KEY>'
   S3_INPUT_BUCKET_NAME = '<INSERT_YOUR_BUCKET_NAME>'

   INPUT_PATH = "big_buck_bunny_1080p_h264_short.mov"

   SFTP_OUTPUT_HOST_NAME = '<INSERT_YOUR_SFTP_HOST_NAME>'
   SFTP_OUTPUT_USER_NAME = '<INSERT_YOUR_SFTP_USER_NAME>'
   SFTP_OUTPUT_PASSWORD = '<INSERT_YOUR_SFTP_PASSWORD>'
   SFTP_OUTPUT_PORT_NUMBER = 22
   ```

3. 必要に応じて、出力エンコードの Profile を変更します。デフォルトでは映像は 360p/540p、音声は 128kbps/64kbps を出力するよう設定されています。
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

4. サムネイル付きサンプル (4 番) を使う場合は、必要に応じてサムネイルを生成する再生位置 (秒) を変更します。
   ```python
   THUMBNAIL_POSITION_IN_SECONDS = [10]
   ```

5. サンプルコードを実行し、エンコードを開始します。

## 処理結果例

エンコードが終了すると、固定ビットレートでエンコードされた H.264 + AAC の出力が生成され、それを参照する HLS (DASH 対応サンプルでは HLS と DASH の両方) マニフェストが生成されます。Fragmented MP4 サンプルではセグメント化された出力が、MP4 サンプルではレンディションごとの単一 MP4 ファイル (HLS からバイトレンジ参照) が出力されます。

StreamCondition 付きサンプルでは、入力に音声トラックが存在する場合のみ音声ストリームが生成されます。サムネイル付きサンプルでは、加えて `thumbnail/` 配下にサムネイル画像が生成されます。SFTP 出力サンプルでは、指定した SFTP サーバー上に出力ファイルとマニフェストが生成されます (just-in-time 版はエンコードと同時に、post-encoding 版はエンコード完了後にマニフェストが生成されます)。
