# はじめに

本リポジトリには、Bitmovin 製品（Encoding、Player、Analytics
）を使用したサンプル実装が含まれています。各サンプルは、それぞれの製品のディレクトリ配下で管理されています。

## Encoding
/encoding ディレクトリ配下には、Bitmovin Encoding API 
を使用してビデオをエンコードするためのサンプル実装が含まれています。主なサンプルには以下のものがあります。
- **pertitle**: PerTitle エンコーディングを行うためのサンプルです。
- **forensic-watermark**: Forensic Watermarking を用いたエンコーディングを行うためのサンプルです。
- **dolby**: Dolby Vision、Dolby Atmos フォーマット出力のエンコードを行うためのサンプルです。
- **hdr10**: HDR10 フォーマット出力のエンコードを行うためのサンプルです。

これらのスクリプトには、Bitmovin Encoding API の各機能を使用する方法を示しています。詳細については、各スクリプト内のコメントを参照してください。

## Player
/player ディレクトリには、Bitmovin Player を使用してビデオを再生するためのサンプルが含まれています。サンプルには以下のものがあります。

- player-web-basic: Bitmovin Player を基本的な設定で初期化し、ビデオを再生するスクリプトです。

## Analytics
/analytics ディレクトリには、Bitmovin Analytics を使用してビデオ視聴の分析を行うためのサンプルが含まれています。主にクライアント側の Bitmovin Analytics と Player 
の統合方法についての実装例が含まれています。サンプルには以下のものがあります。

- player-web-integration: Bitmovin Analytics を有効にし、ビデオ視聴のトラッキング実装を示すためのサンプルです。


なお、本リポジトリは Bitmovin 公式のサンプル実装の日本語版を提供するものではございません。一実装例として参照ください。
