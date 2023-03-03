# はじめに

このサンプルでは、Bitmovin Encoder API を使用して、Nagra NexGuard Forensic Watermarking を利用する方法を説明します。この機能は A/B watermarking 
と言われる方法を用います。Bitmovin Encoder は各入力に対して2つの出力（stream A / stream B) を生成し、Nagra NexGuard Forensic Watermarking に対応した CDN 
を用いることで、CDN は各ユーザーに対してユニークな A/B のシーケンスを生成して配信します。このユニークなシーケンスによって、万が一コンテンツが漏洩した際に漏洩元を特定することが可能になります。本サンプルでは Python 
を用いたサンプルを説明します。

## 前提条件

- Bitmovin Encoder バージョン 2.62 以降
- 有効な Nagra NexGuard Forensic Watermarking のアカウント

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
   
   INPUT_PATH = "<INSERT YOUR INPUT PATH>"
   
   S3_OUTPUT_ACCESS_KEY = '<INSERT YOUR ACCESS KEY>'
   S3_OUTPUT_SECRET_KEY = '<INSERT YOUR SECRET KEY>'
   S3_OUTPUT_BUCKET_NAME = '<INSERT YOUR BUCKET NAME>'
   ```

3. 有効な Nagra NexGuard Forensic Watermarking のライセンス情報と Nagra から提供される Preset の値を下記に設定します。
   ```python
   # NexGuard License: Base64 strings obtained from Nagra
   NEX_GUARD_LICENSE = "<INSERT YOUR NAGRA LICENSE>"
   
   # NexGuard Preset obtained from Nagra
   NEX_GUARD_PRESET = "<INSERT YOUR NAGRA PRESET>"
   ```

4. init.mp4 セグメントへの prefix として用いる文字列を下記に記載します。
   ```python
   # This filename is used as a init segment prefix (e.g. bigbuckbunny_init.mp4)
   # Please refer the tutorial for more details about the naming conventions.
   # https://bitmovin.com/docs/encoding/tutorials/how-to-use-nagra-nexguard-filemarker-a-b-watermarking
   FILENAME = "bigbuckbunny"
   ```

5. 必要に応じて、出力エンコードの Profile を変更します。デフォルトでは 1080p video と AAC のみ出力するよう設定されています。

   ```python
   encoding_profiles_h264 = [
       dict(height=1080, bitrate=2_000_000, level=None, mode=StreamMode.STANDARD)
   ]
   
   encoding_profiles_aac = [
       dict(bitrate=128000, rate=48_000)
   ]
   ```
   
6. サンプルコードを実行し、エンコードを開始します。

## 処理結果例

エンコードが終了すると、出力場所に下記のように、1つの init.mp4 セグメントと A/B watermarking で用いるために対になった stream A/stream B のセグメントが生成されます。
   ```text
   bigbuckbunny_init.mp4
   segment_0.m4s
   segment_1.m4s
   b.segment_0.m4s
   b.segment_1.m4s
   ```

ここで注意点としては、stream A/stream B をどのようなパターンで配信するかは Nagra と各 CDN 
の設定によって決められ、エンコーダーやプレイヤー側が決めるものではありません。各ストリームセッションの開始時にユニークなパターンが生成されます。

