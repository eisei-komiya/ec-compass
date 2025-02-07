# ai_report_generator.py
import os  # 環境変数を扱うためのライブラリ
try:
    from dotenv import load_dotenv  # python-dotenv を使って.envファイルを読み込みます
    load_dotenv()  # .env ファイルから環境変数をロード
except ImportError:
    print("python-dotenvがインストールされていません。必要に応じてインストールしてください。")

from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  # OpenAI APIを利用するためのライブラリ

# 環境変数 'OPENAI_API_KEY' からAPIキーを取得して設定します

import json    # 辞書を文字列に変換するために利用


def generate_report_with_ai(product_results, evaluation_criteria, top_n, report_model="gpt-4o-mini", ai_platform="openai"):
    """
    製品情報と評価基準に基づいて、OpenAI APIを利用して詳細なMarkdown形式のレポートを生成する関数です。

    引数:
      product_results: 各ECサイトから収集した製品情報のリスト
      evaluation_criteria: YAML設定ファイルからの評価基準の辞書
      top_n: 各ECサイトごとに抽出する上位製品数（ユーザーが設定可能）
      report_model: 使用するGPTモデルの名前
      ai_platform: 使用するAIプラットフォームの名前

    戻り値:
      生成されたMarkdown形式のレポート（文字列）
    """
    # プロンプトの作成
    prompt = (
        "以下は各ECサイトごとの製品情報（各サイトで複数の商品が含まれています）と評価基準です。これに基づいて、詳細かつ分かりやすいMarkdown形式のレポートを作成してください。\n\n"
        "【各ECサイトの製品情報】\n" + json.dumps(product_results, ensure_ascii=False, indent=2) + "\n\n"
        "【評価基準】\n" + json.dumps(evaluation_criteria, ensure_ascii=False, indent=2) + "\n\n"
        "・各評価項目ごとに、メリットや改善点を詳しく解説してください。\n"
        "・カスタム評価基準も必ず反映してください。\n"
        "・ECサイトごとにトップ商品の特徴や比較点を記載し、視認性の高いレポートにしてください。"
    )

    combined_prompt = "あなたは、提供された製品情報と評価基準に基づき、詳細かつ分かりやすいMarkdown形式のレポートを作成するプロフェッショナルなアシスタントです。\n" + prompt

    # ai_platform に応じて、使用するLLMモジュールとAPIキー、必要なパラメータを設定します
    if ai_platform.lower() == "deepseek":
        from langchain_openai import ChatOpenAI
        base_url = "https://api.deepseek.com/v1"
        api_key = os.getenv("DEEPSEEK_API_KEY")
        llm = ChatOpenAI(model=report_model, api_key=api_key, temperature=0.7, **({"base_url": base_url} if base_url else {}))
    elif ai_platform.lower() == "google":
        from langchain_google_vertexai import ChatVertexAI
        api_key = os.getenv("GOOGLE_API_KEY")
        llm = ChatVertexAI(model=report_model, api_key=api_key, temperature=0.7)
    elif ai_platform.lower() == "openai":
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        llm = ChatOpenAI(model=report_model, api_key=api_key, temperature=0.7)
    else:
        # デフォルトはOpenAIを使用
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        llm = ChatOpenAI(model=report_model, api_key=api_key, temperature=0.7)

    # LangChainを使ってレポート生成
    report = llm.predict(combined_prompt)
    return report 