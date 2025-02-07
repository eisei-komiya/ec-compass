# scraper.py

import asyncio  # 非同期処理を行うためのライブラリ
import json     # JSON形式のデータを扱うためのライブラリ
import os
import re  # 正規表現を扱うライブラリをインポートします

# Browser-Useを利用するためのエージェントをインポート
from browser_use import Agent


def construct_task(websites, keywords, result_items=None, return_products_num=None):
    """
    ECサイト情報、検索キーワード、取得する製品情報、及び取得件数に基づき、
    Browser-Useに渡すタスク命令文を生成します。

    引数:
      websites: 各ECサイトの情報リスト（辞書形式、例: {'name': 'Amazon', 'url': 'https://www.amazon.co.jp/'}）
      keywords: 検索キーワードのリスト
      result_items: 各サイトで取得する製品情報の項目リスト
      return_products_num: 各サイトで返す商品の上位件数

    戻り値:
      タスク命令文（文字列）
    """
    # 1. 初めに全体の手順を指示する文章を作成する
    task = "以下の手順に従ってください。\n"
    task += "1. search_parameters に記載された各サイト(以下のURL)に上から順番にアクセスしてください。\n"
    
    # 2. 各サイトの情報をリストアップ
    task += "   対象サイト:\n"
    for site in websites:
        task += "- {} (URL: {})\n".format(site.get("name", "不明"), site.get("url", "不明"))
    
    # 3. キーワードは空白区切りで検索するよう指示
    task += "2. 各サイトごとに、空白区切りされたキーワード ({} ) を用いて検索を実施してください。\n".format(" ".join(keywords))
    
    # 4. 検索結果の上位件数に応じた処理指示（return_products_num が指定されていれば）
    if return_products_num is not None:
        task += "3. 検索結果の上位 {} 件の商品について、新しいタブを開いてください。\n".format(return_products_num)
    else:
        task += "3. 検索結果の上位件数の商品について、新しいタブを開いてください。\n"
    
    # 5. 各商品のタブでは、結果として result_items の情報のみを抽出する指示
    if result_items and len(result_items) > 0:
        task += "4. 新しいタブで、" + "、".join(result_items) + " に該当する情報のみを抽出し、JSON形式で返してください。\n"
    else:
        task += "4. 新しいタブで、製品名、価格、URL の情報のみを抽出し、JSON形式で返してください。\n"
    
    # 6. タブのクローズとサイト間の遷移
    task += "5. 各商品のタブは取得後すぐに閉じ、次のサイトの情報取得に進んでください。\n"
    
    # 7. 全サイトの情報取得後、結果をまとめた JSON を返すように指示
    task += "6. すべてのサイトで情報取得が完了したら、全商品の情報をまとめた1つのJSONとして出力してください。余計な説明文は含めないでください。\n"
    
    return task


def run_browser_search(task, search_model="gpt-4o", ai_platform="openai"):
    """
    非同期でBrowser-Useのエージェントを使い、指定されたタスク命令文を実行して結果を取得します。

    引数:
      task: エージェントに渡すタスク命令文（文字列）
      search_model: 使用する言語モデルのモデル名
      ai_platform: 使用するAIプラットフォームの名前

    戻り値:
      エージェントの実行結果（文字列）
    """
    async def async_run():
        # ai_platformに応じて適切なLLMをインスタンス化
        if ai_platform.lower() == "deepseek":
            from langchain_openai import ChatOpenAI
            base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
            api_key = os.getenv("DEEPSEEK_API_KEY")
            llm = ChatOpenAI(model=search_model, api_key=api_key, temperature=0.7, **({"base_url": base_url} if base_url else {}))
        elif ai_platform.lower() == "google":
            from langchain_google_vertexai import ChatVertexAI
            api_key = os.getenv("GEMINI_API_KEY")
            llm = ChatVertexAI(model=search_model, api_key=api_key, temperature=0.7)
        elif ai_platform.lower() == "openai":
            from langchain_openai import ChatOpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            llm = ChatOpenAI(model=search_model, api_key=api_key, temperature=0.7)
        else:
            from langchain_openai import ChatOpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            llm = ChatOpenAI(model=search_model, api_key=api_key, temperature=0.7)

        # 統合されたタスク命令文に従い、エージェントを作成・実行
        combined_task = "以下の指示に従ってください。\n" + task
        agent = Agent(task=combined_task, llm=llm)
        result = await agent.run()

        # 結果が文字列として返される場合にそのまま出力
        if isinstance(result, list) and len(result) > 0:
            try:
                result_str = result[-1].message.content
            except AttributeError:
                result_str = str(result)
        elif isinstance(result, str):
            result_str = result
        else:
            result_str = str(result)

        return result_str

    return asyncio.run(async_run())


def scrape_data(websites, search_parameters):
    """
    指定されたECサイトリストと検索条件に基づき、Browser-Useを利用して製品情報を取得します。
    すべてのサイトの検索結果をまとめた製品情報リスト（辞書形式）を返します。

    引数:
      websites: 複数のECサイト情報を含むリスト（例: [{'name': 'Amazon', 'url': 'https://www.amazon.co.jp/'}, ...]）
      search_parameters: 検索条件を含む辞書（例: {'keywords': ["マザーボード", "ATX"], 'return_products_num': 5, ... }）

    戻り値:
      製品情報を含むリスト。各製品情報は辞書形式です。
    """
    # 'keywords'キーを検索条件から取得
    keywords = search_parameters.get("keywords", [])
    # 'result_items'キーを取得
    result_items = search_parameters.get("result_items", [])
    # 'return_products_num'キーを取得
    return_products_num = search_parameters.get("return_products_num", None)
    
    # ECサイト情報、キーワード、取得する製品情報、及び上位取得件数からタスク命令文を作成
    task_instruction = construct_task(websites, keywords, result_items, return_products_num)
    
    # 生成されたタスク命令文をログ出力
    print("生成されたタスク命令文:")
    print(task_instruction)
    
    try:
        # settingsで指定されたモデルを取得（指定がなければ'default'を使用）
        search_model = search_parameters.get("search_model", "gpt-4o")
        # settingsで指定されたai_platformを取得（指定がなければ'openai'を使用）
        ai_platform = search_parameters.get("ai_platform", "openai")

        # Browser-Useの非同期処理を実行して結果の文字列を取得
        result_str = run_browser_search(task_instruction, search_model, ai_platform)

        # LangChainのStructuredOutputParserを利用して、LLMの出力(result_str)をパース
        from langchain.output_parsers import StructuredOutputParser, ResponseSchema

        # 出力すべきJSONのスキーマを定義
        if result_items and len(result_items) > 0:
            schema_description = "製品情報のリスト。各製品は、" + "、".join(result_items) + " の情報を含む辞書です。"
        else:
            schema_description = "製品情報のリスト。各製品は、製品名、URL、価格 の情報を含む辞書です。"

        schemas = [
            ResponseSchema(name="results", description=schema_description)
        ]

        # スキーマからOutputParserを作成し、LLM出力をパース
        output_parser = StructuredOutputParser.from_response_schemas(schemas)
        product_data = output_parser.parse(result_str)
    except Exception as e:
        print("Browser-Useの実行またはJSONのパースに失敗しました。エラー:", e)
        exit()
    return product_data 