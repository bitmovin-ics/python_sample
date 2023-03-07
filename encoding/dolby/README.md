# はじめに

このサンプルでは、Bitmovin Encoder API を使用して、Dolby Vision・Dolby Atmos エンコーディングを利用する方法を説明します。Bitmovin Encoder は Dolby 
社から提供されるエンコーディング用 SDK を Bitmovin Encoder API から呼び出すよう統合しており、Bitmovin Encoder API を利用することで Dolby 社
準拠のエンコードを行いつつ、クラウドを利用した分散エンコードを用いて高速に処理を実行することができます。本サンプルでは Python を用いたサンプルを説明します。

本サンプルディレクトリには複数のサンプルを含んでいますが、実装しているユースケースとしては Dolby Vision と Dolby Atmos を両方をエンコードするか、 Dolby Atmos 
のみをエンコードするかの２通りです。Dolby Atmos の入力として ADM (Audio Definition Model、wav 形式)、DAMF（Dolby Atmos Master 
Files）があり、それぞれ読み込み方を示すためにそれぞれサンプルを加えています。または入力ファイルの取得方法として S3 からダウンロードする場合、HTTPS 
でダウンロードする場合の実装を含んでいます。


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

- 特記事項
  - 本サンプルでは Fragmented MP4 形式で Muxing を行っています。Dolby Vision、Dolby Atmos ともに Fragmented MP4 および MP4 Muxing の両方をサポートしています。
  - 本サンプルでは、DRM は付与していませんが、DRM ライセンスをお持ちの場合は Dolby Vision、Dolby Atmos ともに DRM をかけることもできます。
  - Dolby Vision 用のメタデータとしては、xml ファイルを side car 方式で渡すか、メザニンにメタデータも同梱するかの２通りがありますが、本サンプルでは side car 方式のみを実装しています。

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

5. 必要に応じて、出力エンコードの Profile を変更します。デフォルトでは Dolby Vision は 1080p/540p、Dolby Atmos は 448kbps/48Hz のみを出力するよう設定されています。
   ```python
   encoding_profiles_h265_dolbyvision = [
       dict(height=1080, bitrate=2_000_000, level=None, aqs=0.5, mode=StreamMode.STANDARD, dynamic_range=H265DynamicRangeFormat.DOLBY_VISION),
       dict(height=540, bitrate=1_000_000, level=None, aqs=1.2, mode=StreamMode.STANDARD, dynamic_range=H265DynamicRangeFormat.DOLBY_VISION)
   ]
   
   encoding_profiles_atmos = [
       dict(bitrate=448000, rate=48_000)
   ]
   ```
   
6. サンプルコードを実行し、エンコードを開始します。

## 処理結果例

エンコードが終了すると、Dolby Vision および Dolby Atmos に対応した出力が　Fragmented MP4 形式で出力され、その出力を参照する Manifest ファイルが HLS/DASH でそれぞれ生成されます。

再生テストには Dolby Vision および Dolby Atmos のストリーミング再生に対応したデバイスが必要になります。お持ちのデバイスが Dolby Vision および Dolby Atmos をサポートしているかをご確認ください。最新の macOS/iOS の Safari は両フォーマットともサポートしています。


