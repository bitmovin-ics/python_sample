# はじめに

本リポジトリは Bitmovin Encoder を用いたサンプルスクリプトを管理するためのリポジトリです。 Bitmovin Encoder は各クラウド環境（AWS、GCP、Azure）を用いてエンコードを行うため、入出力ファイル、クラウドリージョン、各種エンコード設定やマニフェスト設定を Bitmovin が提供する API (https://bitmovin.com/docs/encoding/api-reference) を用いて記述します。

また、API は REST API として提供されている一方、クライアント側で実装しやすいよう各種プログラミング言語で
SDK（https://bitmovin.com/docs/encoding/sdks) も提供されています。本リポジトリでは主に Python 用の Bitmovin SDK を利用してエンコードを行う実装方法を示します。

## システム条件

- Python 2.7 もしくは Python 3.4 以降

## セットアップ方法

1. pip コマンドを利用し、Python 用の Bitmovin SDK を取得します。Bitmovin エンコーダーに新しい機能が追加され、API に新しいエンドポイントやパラメータが追加された場合、SDK を更新しないと機能が利用できない場合があります。詳細な API の追加機能についてはリリースノートを参照ください。
   （https://bitmovin.com/docs/encoding/changelogs/rest)

   ```sh
   $ pip install git+https://github.com/bitmovin/bitmovin-api-sdk-python.git
   ```
2. 有効な Bitmovin API key および Organization ID をスクリプトに設定します。API key は Bitmovin アカウントごとに発行され、スクリプトを実行すると Organization ID　に紐づくサブスクリプションプランを消費してエンコードを行います。

   ```python
   API_KEY = '<INSERT YOUR API KEY>'
   ORG_ID = '<INSERT YOUR ORG ID>'
   ```
3. 入出力ファイルが保存されている場所にアクセスするための情報、入力ファイルパス、出力先パスを指定します。例えば、S3
   input / S3 output を行うスクリプトの場合、下記のような定義がスクリプト内に用意されているため、各入出力にアクセスするために必要な情報を設定します。設定が必要なパラメータはスクリプトごとに異なる場合があるため、詳細はスクリプト内の記述をご確認ください。

   ```python
   S3_INPUT_ACCESS_KEY = '<INSERT_YOUR_ACCESS_KEY>'
   S3_INPUT_SECRET_KEY = '<INSERT_YOUR_SECRET_KEY>'
   S3_INPUT_BUCKET_NAME = '<INSERT_YOUR_BUCKET_NAME>'

   S3_OUTPUT_ACCESS_KEY = '<INSERT_YOUR_ACCESS_KEY>'
   S3_OUTPUT_SECRET_KEY = '<INSERT_YOUR_SECRET_KEY>'
   S3_OUTPUT_BUCKET_NAME = '<INSERT_YOUR_BUCKET_NAME>'

   INPUT_PATH = '<INSERT_YOUR_INPUT_FILE_PATH>'
   OUTPUT_BASE_PATH = '<INSERT_YOUR_OUTPUT_FOLDER_PATH>'
   ```

## サンプル

To be described.
