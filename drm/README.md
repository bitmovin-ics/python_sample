# はじめに

このサンプルでは、Bitmovin Encoder API を使用して、DRM (Digital Rights Management) で暗号化した VOD ストリームをエンコードする方法を説明します。Bitmovin Encoder では、エンコードした Muxing に対して各種 DRM システム (Widevine / PlayReady / FairPlay) の暗号化を付与し、HLS / DASH / Smooth Streaming のマニフェストに content protection 情報を埋め込んだ状態で出力することができます。本サンプルでは Python を用いたサンプルを説明します。

本サンプルディレクトリには複数のサンプルを含んでおり、それぞれ「コーデック (H.264 / H.265 / VP9)」「DRM システムと暗号化方式 (Widevine / PlayReady / FairPlay、CENC CTR / CBC、FairPlay AES-CBC)」「パッケージング (DASH / HLS / Smooth Streaming)」「Per-Title の有無」の組み合わせが異なります。いずれも入出力に AWS S3 を利用し、`AWS_AP_NORTHEAST_1` リージョンでエンコードします。

1. H.264 + AAC を Fragmented MP4 に格納し、CBC モードの CENC で Widevine / PlayReady / FairPlay をまとめて付与するサンプル (固定 ABR ラダー、DASH/HLS)
   ```text
   create_h264_aac_fmp4_cenc_cbc_drm_wv_pr_fp_dash_hls_on_aws.py
   ```
2. Per-Title H.264 + AAC で、DASH 用に FMP4 + CENC (Widevine / PlayReady)、HLS 用に TS + FairPlay を別々に付与するサンプル
   ```text
   create_per_title_h264_aac_fmp4_ts_drm_wv_pr_fp_dash_hls_on_aws.py
   ```
3. Per-Title H.264 + AAC を Fragmented MP4 (ismv / isma) に格納し、CENC PlayReady で暗号化して Smooth Streaming で配信するサンプル
   ```text
   create_per_title_h264_aac_mp4_cenc_drm_pr_smooth_on_aws.py
   ```
4. Per-Title H.265 + AAC で、単一の FMP4 Muxing に DASH 用 CENC (Widevine / PlayReady) と HLS 用 FairPlay の 2 つの DRM を付与するサンプル
   ```text
   create_per_title_h265_aac_fmp4_drm_wv_pr_fp_dash_hls_on_aws.py
   ```
5. Per-Title VP9 (WebM) + AAC (FMP4) で、CENC Widevine のみを付与して DASH で配信するサンプル
   ```text
   create_per_title_vp9_aac_webm_fmp4_cenc_drm_wv_dash_on_aws.py
   ```

- 特記事項
  - 各サンプルが扱う DRM システム・暗号化方式・パッケージング・Per-Title の有無は以下のとおりです。

    | サンプル | コーデック | コンテナ | DRM システム | 暗号化方式 | パッケージング | Per-Title |
    | --- | --- | --- | --- | --- | --- | --- |
    | 1 | H.264 + AAC | FMP4 | Widevine / PlayReady / FairPlay | CENC (CBC, IV 16 bytes) | DASH / HLS | なし (固定 ABR ラダー) |
    | 2 | H.264 + AAC | FMP4 (DASH) / TS (HLS) | Widevine / PlayReady (DASH)、FairPlay (HLS) | CENC (CTR, IV 8 bytes) / FairPlay AES-CBC | DASH / HLS | あり |
    | 3 | H.264 + AAC | Fragmented MP4 (ismv / isma) | PlayReady | CENC (CTR, IV 8 bytes) | Smooth Streaming | あり |
    | 4 | H.265 + AAC | FMP4 | Widevine / PlayReady (DASH)、FairPlay (HLS) | CENC (CTR, IV 8 bytes) / FairPlay AES-CBC | DASH / HLS | あり |
    | 5 | VP9 (映像) + AAC (音声) | WebM (映像) / FMP4 (音声) | Widevine | CENC (CTR, IV 8 bytes) | DASH | あり |

    ※ サンプル 2〜5 はコード上で `encryption_mode` を明示指定しておらず、CTR は Bitmovin API のデフォルト値です（サンプル 1 のみ `EncryptionMode.CBC` を明示指定しています）。

  - サンプル 1 は `CencDrm` の `encryption_mode=EncryptionMode.CBC` を指定し、1 つの CENC 設定の中に Widevine (`pssh`)・PlayReady (`la_url`)・FairPlay (`iv` / `uri`) をまとめて含めています。映像・音声の同じ FMP4 Muxing に同一の CENC 設定を適用し、DASH と HLS の両方のマニフェストから参照します。
  - サンプル 2 は、DASH 系統 (FMP4 Muxing) に CENC (Widevine + PlayReady、CTR モード)、HLS 系統 (TS Muxing) に単独の FairPlay (AES-CBC) を付与する構成です。映像・音声それぞれについて FMP4 と TS の 2 種類の Muxing を作成します。
  - サンプル 3 は Smooth Streaming 向けに、`Mp4Muxing` を `fragmented_mp4_muxing_manifest_type=FragmentedMp4MuxingManifestType.SMOOTH` で生成し (映像 `video.ismv` / 音声 `audio.isma`)、CENC PlayReady を付与して `stream.ism` / `stream.ismc` を生成します。
  - サンプル 4 は、エンコードは 1 回だけ行い、生成された単一の FMP4 Muxing に対して DASH 用に CENC、HLS 用に FairPlay の 2 種類の DRM をそれぞれ別の出力パスに書き出す構成です。DASH マニフェストは CENC、HLS マニフェストは FairPlay を参照します。
  - サンプル 5 は、映像を VP9 (WebM)、音声を AAC (FMP4) として別コンテナで出力し、いずれも CENC Widevine で暗号化して DASH マニフェストに content protection を付与します。
  - **DRM 鍵について (重要)**: 各サンプルではコード冒頭の定数に DRM 鍵のテスト値が直書きされています。これらはサンプルを動作させるためのプレースホルダー値であり、**本番環境では必ずご自身の値に差し替えてください**。対象となる定数は以下のとおりです (サンプルにより使用するものは異なります)。
    - `CENC_KEY` / `CENC_KID`: CENC 暗号化に用いるコンテンツ鍵と Key ID
    - `CENC_WIDEVINE_PSSH`: Widevine の PSSH (Base64)
    - `CENC_PLAYREADY_LA_URL`: PlayReady のライセンス取得 URL
    - `CENC_FAIRPLAY_IV` / `CENC_FAIRPLAY_URI` (サンプル 1)、`FAIRPLAY_KEY` / `FAIRPLAY_IV` / `FAIRPLAY_URI` (サンプル 2・4): FairPlay の鍵 / IV / キー URI (`skd://...`)
  - Per-Title を使用するサンプル (2〜5) では、映像ストリームを Per-Title テンプレート (`PER_TITLE_TEMPLATE` / `PER_TITLE_TEMPLATE_FIXED_RESOLUTION_AND_BITRATE`) として定義しており、実際の ABR ラダー (レンディション) はエンコード時に Bitmovin Per-Title が自動展開します。展開後の各レンディションで出力パスが衝突しないよう、出力パスには `{height}p_{bitrate}_{uuid}` のプレースホルダーを用いています。これらのサンプルではレンディション数がエンコード後に確定するため、マニフェストはエンコード完了後に生成しています。
  - Per-Title を使用するサンプルの映像コーデック設定には、Hulu 推奨に準拠したチューニングを適用しています (VP9 では出力解像度に応じて `cpu_used` / `tile_columns` を切り替えています)。

## 前提条件

- Bitmovin Encoder アカウントと API Key
- DRM 暗号化機能を利用可能な Bitmovin Encoder
- 入出力に使用する AWS S3 バケット

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

3. DRM 鍵の定数をご自身の値に差し替えます。サンプルにはテスト値が直書きされているため、本番では必ず差し替えてください (使用する定数はサンプルにより異なります)。
   ```python
   CENC_KEY = '<INSERT YOUR CENC KEY>'
   CENC_KID = '<INSERT YOUR CENC KID>'
   CENC_WIDEVINE_PSSH = '<INSERT YOUR WIDEVINE PSSH>'
   CENC_PLAYREADY_LA_URL = '<INSERT YOUR PLAYREADY LA URL>'
   # サンプル 1: CENC に内包する FairPlay
   CENC_FAIRPLAY_IV = '<INSERT YOUR FAIRPLAY IV>'
   CENC_FAIRPLAY_URI = '<INSERT YOUR FAIRPLAY URI>'
   # サンプル 2・4: 単独 FairPlay
   FAIRPLAY_KEY = '<INSERT YOUR FAIRPLAY KEY>'
   FAIRPLAY_IV = '<INSERT YOUR FAIRPLAY IV>'
   FAIRPLAY_URI = '<INSERT YOUR FAIRPLAY URI>'
   ```

4. 必要に応じて、出力エンコードの Profile (ABR ラダー / Per-Title テンプレート) を変更します。Per-Title を使用するサンプルでは、`encoding_profiles_*` で定義したテンプレートをもとに実際のレンディションがエンコード時に自動展開されます。
   ```python
   encoding_profiles_h264_pertitle = [
       {"height": 180, "profile": ProfileH264.BASELINE, "level": None, "mode": StreamMode.PER_TITLE_TEMPLATE, "aqs": 1.2},
       # ...
       {"height": 1080, "profile": ProfileH264.HIGH, "level": None, "mode": StreamMode.PER_TITLE_TEMPLATE, "aqs": 0.5},
   ]
   ```

5. サンプルコードを実行し、エンコードを開始します。

## 処理結果例

エンコードが終了すると、各サンプルのコーデック・コンテナに従って DRM で暗号化された Muxing が出力先 S3 に生成され、それを参照するマニフェスト (サンプル 1・2・4 は DASH と HLS、サンプル 3 は Smooth Streaming、サンプル 5 は DASH) が出力されます。マニフェストには各 DRM システムの content protection 情報が埋め込まれます。

再生テストには、対象の DRM システム (Widevine / PlayReady / FairPlay) に対応したプレイヤーと、有効なライセンスサーバーが必要です。サンプルに直書きされた DRM 鍵はテスト値のため、実際にライセンス取得を伴う再生を行う場合はご自身の鍵・ライセンスサーバー情報に差し替えてください。
