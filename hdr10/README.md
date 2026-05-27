# はじめに

このサンプルでは、Bitmovin Encoder API を使用して **HDR10** 出力のエンコードを **Per-Title** と組み合わせて行う方法を説明します。HDR10 のカラー情報（BT.2020 色域・SMPTE ST 2084 / PQ・10bit）とマスタリングメタデータを付与した H.265 映像を生成し、Per-Title により最適な ABR ラダーを自動展開しながら、AAC 音声とともに Fragmented MP4 で出力して HLS/DASH で配信します。本サンプルでは Python を用いた実装を示します。

本サンプルディレクトリには、HDR10 + Per-Title のエンコードを行うサンプルを 1 つ含みます。

1. HDR10 H.265 + AAC (FMP4) を Per-Title で HLS/DASH 配信するサンプル
   ```text
   create-hdr10-pertitle-encoding.py
   ```

- 特記事項
  - 映像は H.265 (`ProfileH265.MAIN10`)、`PixelFormat.YUV420P10LE` の 10bit でエンコードし、HDR10 のために以下を設定しています。
    - `ColorConfig`: `ColorSpace.BT2020_NCL` / `ColorPrimaries.BT2020` / `ColorTransfer.SMPTE2084`
    - `hdr=True`、`master_display='G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)L(10000000,1)'`
    - `max_content_light_level=800`、`max_picture_average_light_level=400`
  - 映像ストリームは `StreamMode.PER_TITLE_TEMPLATE` のテンプレートとして定義し、エンコード開始リクエストで `PerTitle(h265_configuration=H265PerTitleConfiguration(auto_representations=AutoRepresentation()))` を指定して、実際の ABR ラダーを Bitmovin Per-Title が自動展開します。
  - 音声は AAC 5.1ch (`AacChannelLayout.CL_5_1_BACK`)、128kbps / 48kHz を Fragmented MP4 形式で出力します。
  - クラウドリージョンは `AWS_AP_NORTHEAST_1`、encoder は `STABLE` を使用します。マニフェストはエンコード完了後に生成し、HLS は `HlsVersion.HLS_V8` を使用します。

## 前提条件

- HDR10 (H.265 10bit) エンコードに対応した Bitmovin Encoder
- Bitmovin Python SDK

## サンプルの利用方法

1. Bitmovin Encoder API Key と Organization ID を下記に設定します。
   ```python
   API_KEY = '<INSERT YOUR API KEY>'
   ORG_ID = '<INSERT YOUR ORG ID>'
   ```

2. 入出力の bucket の情報および入力ファイルパスを下記に設定します。サンプルでは入力例として https://4kmedia.org/ のファイル名を記述しています。
   ```python
   S3_INPUT_ACCESS_KEY = '<INSERT_YOUR_ACCESS_KEY>'
   S3_INPUT_SECRET_KEY = '<INSERT_YOUR_SECRET_KEY>'
   S3_INPUT_BUCKET_NAME = '<INSERT_YOUR_BUCKET_NAME>'

   INPUT_PATH = "hdr10/Sony Bravia OLED 4K Demo.mp4"  # from https://4kmedia.org/

   S3_OUTPUT_ACCESS_KEY = '<INSERT_YOUR_ACCESS_KEY>'
   S3_OUTPUT_SECRET_KEY = '<INSERT_YOUR_SECRET_KEY>'
   S3_OUTPUT_BUCKET_NAME = '<INSERT_YOUR_BUCKET_NAME>'
   ```

3. 必要に応じて、Per-Title の映像プロファイルを変更します。デフォルトでは H.265 MAIN10 を `PER_TITLE_TEMPLATE` モードで定義しています。
   ```python
   encoding_profiles_h265_pertitle = [
       dict(height=None, profile=ProfileH265.MAIN10, level=None, mode=StreamMode.PER_TITLE_TEMPLATE, aqs=1.2),
   ]
   ```

4. 必要に応じて、HDR10 のマスタリングメタデータ（`master_display`・`max_content_light_level`・`max_picture_average_light_level`）を入力素材に合わせて調整します。

5. サンプルコードを実行し、エンコードを開始します。

## 処理結果例

エンコードが終了すると、HDR10 (H.265 MAIN10 / 10bit / BT.2020 / PQ) の映像が Per-Title で複数の ABR variant に展開されて生成され、AAC 5.1ch 音声とともに Fragmented MP4 形式で出力されます。あわせて、それらを参照する HLS/DASH マニフェストがそれぞれ生成されます。

再生テストには HDR10 のストリーミング再生に対応したデバイス・プレイヤーが必要になります。
