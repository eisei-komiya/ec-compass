#!/usr/bin/env python
"""
check_rate_limit.py

このプログラムは、OpenAI APIにシンプルなリクエストを送り、
レスポンスヘッダーに含まれるレート制限情報を取得して表示します。
取得する情報:
  - x-ratelimit-limit-requests: 許可される最大リクエスト数
  - x-ratelimit-limit-tokens: 許可される最大トークン数
  - x-ratelimit-remaining-requests: 残りリクエスト数
  - x-ratelimit-remaining-tokens: 残りトークン数
  - x-ratelimit-reset-requests: リセットまでの時間（リクエストベース）
  - x-ratelimit-reset-tokens: リセットまでの時間（トークンベース）
必ず環境変数 "OPENAI_API_KEY" を設定してから実行してください。
"""

import os     # 環境変数を読み込むためのライブラリ
import requests  # HTTPリクエストを送信するためのライブラリ
import json   # JSON形式のデータを扱うためのライブラリ
from dotenv import load_dotenv  # .env ファイルから環境変数を読み込むためのライブラリ



def get_rate_limit_info():
  """
  OpenAI APIのchat completionsエンドポイントにリクエストを送り、
  レスポンスヘッダーからレート制限情報を取得します。

  戻り値:
    レート制限情報を保持する辞書。該当ヘッダーが存在しない場合は "N/A" を設定。
  """
  load_dotenv()
  # 1. 環境変数からAPIキーを取得
  api_key = os.getenv("OPENAI_API_KEY")
  if not api_key:
    print("エラー: 環境変数 'OPENAI_API_KEY' が設定されていません。")
    return None

  # 2. HTTPリクエストヘッダーの設定
  headers = {
    "Content-Type": "application/json",  # リクエスト本文はJSON形式であることを指定
    "Authorization": f"Bearer {api_key}"   # APIキーを認証用ヘッダーに設定
  }

  # 3. APIに送信するデータの定義
  data = {
    "model": "gpt-4o",  # 使用するモデルの指定（バージョン付きに変更）
    "messages": [{"role": "user", "content": "Hello"}],  # シンプルなチャットメッセージ
    "max_tokens": 5  # 生成する最大トークン数
  }

  # 4. OpenAIのchat completionsエンドポイントのURL
  url = "https://api.openai.com/v1/chat/completions"

  try:
    # 5. POSTリクエストを送信し、APIレスポンスを取得
    response = requests.post(url, headers=headers, json=data)
    if response.status_code != 200:
      print(f"リクエストに失敗しました。ステータスコード: {response.status_code}")
      print("レスポンス内容:", response.text)
      return None
  except Exception as e:
    # ネットワークエラーなどの例外処理
    print("リクエスト送信中にエラーが発生しました:", str(e))
    return None

  # 6. レスポンスヘッダーからレート制限情報を抽出
  rate_limit_info = {
    "x-ratelimit-limit-requests": response.headers.get("x-ratelimit-limit-requests", "N/A"),
    "x-ratelimit-limit-tokens": response.headers.get("x-ratelimit-limit-tokens", "N/A"),
    "x-ratelimit-remaining-requests": response.headers.get("x-ratelimit-remaining-requests", "N/A"),
    "x-ratelimit-remaining-tokens": response.headers.get("x-ratelimit-remaining-tokens", "N/A"),
    "x-ratelimit-reset-requests": response.headers.get("x-ratelimit-reset-requests", "N/A"),
    "x-ratelimit-reset-tokens": response.headers.get("x-ratelimit-reset-tokens", "N/A")
  }

  return rate_limit_info


def main():
  """
  メイン関数。
  get_rate_limit_infoを呼び出し、取得したレート制限情報を表示します。
  """
  info = get_rate_limit_info()
  if info:
    print("取得したレート制限情報:")
    for key, value in info.items():
      print(f"{key}: {value}")


if __name__ == "__main__":
  main() 