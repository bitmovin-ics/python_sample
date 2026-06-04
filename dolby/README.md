# はじめに

このサンプルでは、Bitmovin Encoder API を使用して、Dolby Vision・Dolby Atmos エンコーディングを利用する方法を説明します。Bitmovin Encoder は Dolby 
社から提供されるエンコーディング用 SDK を Bitmovin Encoder API から呼び出すよう統合しており、Bitmovin Encoder API を利用することで Dolby 社
準拠のエンコードを行いつつ、クラウドを利用した分散エンコードを用いて高速に処理を実行することができます。本サンプルでは Python を用いたサンプルを説明します。

本サンプルディレクトリには複数のサンプルを含んでいますが、実装しているユースケースとしては Dolby Vision と Dolby Atmos を両方をエンコードするか、 Dolby Atmos 
のみをエンコードするかの２通りです。Dolby Atmos の入力として ADM (Audio Definition Model、wav 形式)、DAMF（Dolby Atmos Master 
Files）があり、それぞれ読み込み方を示すためにそれぞれサンプルを加えています。または入力ファイルの取得方法として S3 からダウンロードする場合、HTTPS 
でダウンロードする場合の実装を含んでいます。さらに、Dolby Atmos に加えて AAC ステレオを fallback として併載するマルチコーデック構成のサンプルも含みます。加えて、Dolby Vision 入力から Dolby Vision / HDR10 / SDR の 3 つの視聴体験を 1 つの HLS/DASH マニフェストで配信するマルチエンコーディング構成のサンプルも含みます。


1. Dolby Vision と Dolby Atmos の両方を含むサンプル
   ```text
   create_dolbyvision_dolbyatmos_adm_with_hls_dash.py
   create_dolbyvision_dolbyatmos_adm_with_hls_dash_https_input.py
   create_dolbyvision_dolbyatmos_damf_with_hls_dash.py
   create_dolbyvision_dolbyatmos_damf_with_hls_dash_https_input.py
   ```
2. Dolby Atmos のみを含むサンプル
   ```text
   create_audio_only_dolbyatmos_adm_with_hls_dash.py
   create_audio_only_dolbyatmos_damf_with_hls_dash.py
   ```
3. Dolby Vision + Dolby Atmos に AAC ステレオ fallback を加えたサンプル
   ```text
   create_dolbyvision_dolbyatmos_damf_aac_with_hls_dash.py
   ```
4. Dolby Vision 入力から Dolby Vision / HDR10 / SDR の 3 視聴体験を 1 つの HLS/DASH マニフェストで配信するサンプル（マルチエンコーディング + 結合マニフェスト構成、音声はいずれも Atmos DAMF + AAC ステレオ）
   ```text
   create_dolbyvision_hdr10_sdr_2ladder_profile81_with_hls_dash.py
   create_dolbyvision_hdr10_sdr_3ladder_profile5_single_dv_input_with_hls_dash.py
   create_dolbyvision_hdr10_sdr_3ladder_profile5_dv_and_sdr_inputs_with_hls_dash.py
   ```

- 特記事項
  - 本サンプルでは Fragmented MP4 形式で Muxing を行っています。Dolby Vision、Dolby Atmos ともに Fragmented MP4 および MP4 Muxing の両方をサポートしています。
  - 本サンプルでは、DRM は付与していませんが、DRM ライセンスをお持ちの場合は Dolby Vision、Dolby Atmos ともに DRM をかけることもできます。
  - Dolby Vision 用のメタデータとしては、xml ファイルを side car 方式で渡すか、メザニンにメタデータも同梱するかの２通りがありますが、本サンプルでは side car 方式のみを実装しています。
  - AAC fallback 付きサンプル (3 番) では、Atmos 非対応デバイス向けに AAC ステレオを併載しています。HLS では `aac` (DEFAULT=YES) と `atmos` (DEFAULT=NO, AUTOSELECT=YES) の 2 audio media group に分離し、各 video variant を両 group とペアリングして I-Frame playlist も付与しています (Atmos デコード可能なプレイヤーは `atmos` group が紐付いた variant を、非対応プレイヤーは `aac` group が紐付いた variant を選択する形)。DASH では Atmos / AAC をそれぞれ別 AdaptationSet として並列に提供し、プレイヤーは codec capability に基づいて選択します。
  - DV/HDR10/SDR 配信サンプル (4 番) は、同一の Dolby Vision input stream から異なるダイナミックレンジ (Dolby Vision / SDR / HDR10) を 1 つのエンコーディング内で混在出力できない制約 (API error code 2065) に対応するため、**ダイナミックレンジ毎に別エンコーディング**を作成し、全エンコーディングの完了後に全レンディションを横断する 1 つの HLS / DASH マニフェストを `manifests.{dash,hls}.start(StartManifestRequest(manifest_generator=ManifestGenerator.V2))` で post-encoding 生成します。並列実行される各エンコーディングは毎周期一括ポーリングで監視し、いずれかが失敗した場合は残りのエンコーディングを stop して即時に失敗を伝播します (fail-fast)。
  - 4 番の 3 本の違いは「DV ラダーのプロファイル」と「SDR の作り方」です。
    - `2ladder_profile81`: DV ラダーを Profile 8.1 (HDR10 互換) でエンコードし、1 本のラダーで Dolby Vision / HDR10 の両デバイスに配信します (HLS では SUPPLEMENTAL-CODECS による HDR10 フォールバック署名を想定。生成された playlist で 8.1 variant に SUPPLEMENTAL-CODECS が付与されているかご確認ください)。SDR は DV 入力からの HDR-SDR 変換 (トーンマッピング) で生成します。
    - `3ladder_profile5_single_dv_input`: DV ラダーは Profile 5 (純 DV・HDR10 非互換)、HDR10 は専用ラダーとして DV 入力から導出、SDR も DV 入力からの HDR-SDR 変換で生成します。3 系統が独立した、重複のない明快な構成です。
    - `3ladder_profile5_dv_and_sdr_inputs`: 上記の SDR を、HDR-SDR 変換ではなく**別途用意した SDR (BT.709) メザニン**から生成する構成です。グレーディング済みの SDR マスターをお持ちの場合に使用します (DV メザニンと同一内容・同一尺・同一フレームレートである必要があります)。

## 前提条件

- Bitmovin Encoder バージョン 2.31.0 以降

## サンプルの利用方法

1. Bitmovin Encoder API Key と Organization ID を下記に設定します。
   ```python
   API_KEY = '<INSERT YOUR API KEY>'
   ORG_ID = '<INSERT YOUR ORG ID>'
   ```

2. 入出力の bucket の情報および入力ファイルパスを下記に設定します。
   ```python
   S3_INPUT_ACCESS_KEY = '<INSERT YOUR ACCESS KEY>'
   S3_INPUT_SECRET_KEY = '<INSERT YOUR SECRET KEY>'
   S3_INPUT_BUCKET_NAME = '<INSERT YOUR BUCKET NAME>'

   S3_OUTPUT_ACCESS_KEY = '<INSERT YOUR ACCESS KEY>'
   S3_OUTPUT_SECRET_KEY = '<INSERT YOUR SECRET KEY>'
   S3_OUTPUT_BUCKET_NAME = '<INSERT YOUR BUCKET NAME>'
   ```

3. Dolby Vision のメザニンファイルとメタデータファイルのパスを下記に設定します。例として、https://opencontent.netflix.com に含まれる SolLevante 
   のファイル名をサンプルでは記述しています。
   ```python
   DOLBY_VISION_INPUT_PATH = "netflix-opencontent/SolLevante/dolbyvision/sollevante_j2k.mxf"
   DOLBY_VISION_INPUT_METADATA = "netflix-opencontent/SolLevante/dolbyvision/sollevante_j2k_sidecar.xml"
   ```

4. Dolvy Atmos のメザニンファイルを下記いずれかに記載します。ADM の場合は ".wav" ファイルへのパス、DAMF の場合は ".atmos" ファイルへのパスを記載します。
   ```python
   DOLBY_ATMOS_ADM_PATH = 'netflix-opencontent/SolLevante/atmos-adm/sollevante_lp_v01_DAMF_Nearfield_48k_24b_24.wav'
   DOLBY_ATMOS_DAMF_PATH = 'netflix-opencontent/SolLevante/atmos-damf/sollevante_lp_v01_DAMF_Nearfield_48k_24b_24/sollevante_lp_v01_DAMF_Nearfield_48k_24b_24.atmos'
   ```

5. AAC fallback 付きサンプル (3 番) を使う場合は、AAC ステレオ用メザニン (2ch PCM/WAV) のパスも設定します。
   ```python
   AAC_2_0_INPUT_PATH = '<INSERT_AAC_2_0_MEZZANINE_PATH>'
   ```

6. DV/HDR10/SDR 配信サンプル (4 番) のうち `dv_and_sdr_inputs` を使う場合は、SDR (BT.709) 用メザニンのパスも設定します。
   ```python
   SDR_INPUT_PATH = '<INSERT_SDR_VIDEO_MEZZANINE_PATH>'
   ```

7. 必要に応じて、出力エンコードの Profile を変更します。デフォルトでは Dolby Vision は 1080p/540p、Dolby Atmos は 448kbps/48Hz のみを出力するよう設定されています。
   ```python
   encoding_profiles_h265_dolbyvision = [
       dict(height=1080, bitrate=2_000_000, level=None, aqs=0.5, mode=StreamMode.STANDARD, dynamic_range=H265DynamicRangeFormat.DOLBY_VISION),
       dict(height=540, bitrate=1_000_000, level=None, aqs=1.2, mode=StreamMode.STANDARD, dynamic_range=H265DynamicRangeFormat.DOLBY_VISION)
   ]
   
   encoding_profiles_atmos = [
       dict(bitrate=448000, rate=48_000)
   ]
   ```
   なお、AAC fallback 付きサンプル (3 番) は 2160p / 1080p / 720p / 540p の 4 段 Dolby Vision ABR ラダーと、Atmos + AAC ステレオの 2 音声を出力する構成で定義されています。DV/HDR10/SDR 配信サンプル (4 番) は各ダイナミックレンジにつき 2160p / 1080p / 720p / 540p の 4 段ラダーを出力します。
   
8. サンプルコードを実行し、エンコードを開始します。

## 処理結果例

エンコードが終了すると、Dolby Vision および Dolby Atmos に対応した出力が　Fragmented MP4 形式で出力され、その出力を参照する Manifest ファイルが HLS/DASH でそれぞれ生成されます。

再生テストには Dolby Vision および Dolby Atmos のストリーミング再生に対応したデバイスが必要になります。お持ちのデバイスが Dolby Vision および Dolby Atmos をサポートしているかをご確認ください。最新の macOS/iOS の Safari は両フォーマットともサポートしています。


