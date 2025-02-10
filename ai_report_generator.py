# ai_report_generator.py
import os  # 環境変数を扱うためのライブラリ
import json    # 辞書を文字列に変換するために利用
import re

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
        "・レポートは、Markdown形式で作成してください。"
        "・直接レポートのMarkdownを出力し、それ以外の出力はしないでください(コードベースで出力せず、プレーンテキストのMarkdownを出力してください。つまり、```などは不要です)"
    )

    combined_prompt = "あなたは、提供された製品情報と評価基準に基づき、詳細かつ分かりやすいMarkdown形式のレポートを作成するプロフェッショナルなアシスタントです。\n" + prompt

    # ai_platform に応じて、使用するLLMモジュールとAPIキー、必要なパラメータを設定します
    if ai_platform.lower() == "deepseek":
        from langchain_openai import ChatOpenAI
        base_url = "https://api.deepseek.com/v1"
        api_key = os.getenv("DEEPSEEK_API_KEY")
        llm = ChatOpenAI(model=report_model, api_key=api_key, temperature=0.7, **({"base_url": base_url} if base_url else {}))
    elif ai_platform.lower() == "google":
        # from langchain_google_vertexai import ChatVertexAI
        from langchain_google_genai import ChatGoogleGenerativeAI
        api_key = os.getenv("GOOGLE_API_KEY")
        # llm = ChatVertexAI(model=report_model, api_key=api_key, temperature=0.7)
        llm = ChatGoogleGenerativeAI(model=report_model, api_key=api_key, temperature=0.7)
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
    try:
        report = llm.invoke(combined_prompt).content
    except Exception as e:
        print(f"レポート生成中にエラーが発生しました: {e}. 使用しているAIプラットフォームやモデル設定を確認してください。")
        return "レポート生成に失敗しました。"
    # ```から、\nまでを削除し\n```も削除
    report = re.sub(r'^```.*?\n', '', report, flags=re.DOTALL)
    report = re.sub(r'\n```$', '', report, flags=re.DOTALL)
    return report