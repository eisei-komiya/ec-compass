# scraper.py

import asyncio  # 非同期処理を行うためのライブラリ
import json     # JSON形式のデータを扱うためのライブラリ
import os
import re  # 正規表現を扱うライブラリをインポートします

# Browser-Useを利用するためのエージェントをインポート
from browser_use import Agent
from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.browser.context import BrowserContextConfig

# LangChainのStructuredOutputParserを利用して、LLMの出力(result_str)をパース
from langchain.output_parsers import StructuredOutputParser, ResponseSchema


def construct_task(websites, keywords, result_items=None, return_products_num=5):
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
    
    task += f"3. 検索結果ページにて上位 {return_products_num} 件の商品の必ず実際にクリックして新しいタブで開いてください。(抽出したリンクから遷移しないでください)\n"
    
    # 4. 各商品の結果タブでは、まずその商品の詳細ページに遷移してください。
    # 抽出結果は純粋なJSON形式のみで返し、余計な説明文は含めないでください。
    if result_items:
        if isinstance(result_items, dict):
            list_keys = ", ".join(result_items.keys())
        else:
            list_keys = "、".join(result_items)
        task += "4. 各商品のタブで、" + list_keys + " に該当する情報のみを抽出して記憶してください。抽出結果はJSON形式のみで返してください。戻るボタンを押して、次の商品の抽出に進みます。\n"
    else:
        task += "4. 各商品のタブで、製品名、価格、URL の情報のみを抽出し、JSON形式で記憶してください。戻るボタンを押して、次の商品の抽出に進みます。\n"
    keys_description = ", ".join([f"'{key}': {desc}" for key, desc in result_items.items()])
    schema_description = (
        "A JSON object should be returned with a key 'results' mapping to a list of product objects. "
        "Each product object must have the following keys: " + keys_description + " "
        "Ensure that the output is pure valid JSON without additional text or explanations."
    )
    task += "JSONの形式は以下のようにしてください。\n" + schema_description + "\n"
    # 6. タブのクローズとサイト間の遷移
    task += "5. 次のサイトの情報取得に進んでください。\n"
    
    task += "6. すべてのサイトの各商品の詳細ページで情報抽出が完全に終了したら、記憶した全商品の情報をまとめた1つのJSONを出力してください。余計な説明文は含めないでください。\n"
    
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
            api_key = os.getenv("GOOGLE_API_KEY")
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
        # browser = Browser(
        #     config=BrowserConfig()
        # )
        # async with await browser.new_context() as context:
        #     agent = Agent(task=combined_task, llm=llm, browser_context=context, use_vision=False, generate_gif=False)
        #     result = await agent.run()
        agent = Agent(task=combined_task, llm=llm, use_vision=False, generate_gif=False)
        result = await agent.run()

        # 修正: Browser-Useのドキュメントに従い、resultがAgentHistoryListの場合はfinal_result()で最終結果のみを取得
        if hasattr(result, "final_result"):
            result_str = result.final_result()
        elif isinstance(result, list) and len(result) > 0:
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
    
    product_data = []

    try:
        # settingsで指定されたモデルを取得（指定がなければ'default'を使用）
        search_model = search_parameters.get("search_model", "gpt-4o")
        # settingsで指定されたai_platformを取得（指定がなければ'openai'を使用）
        ai_platform = search_parameters.get("ai_platform", "openai")

        # Browser-Useの非同期処理を実行して結果の文字列を取得
        result_str = run_browser_search(task_instruction, search_model, ai_platform)
        # Define an explicit JSON schema for the product information with detailed field explanations.
        if ai_platform.lower() == "google":
            # For Google Cloud, use a simplified fixed JSON schema to avoid unsupported keys.
            schema_description = (
                "A JSON object with key 'results', where results is an array of objects. "
                "Each object must have the following properties: site_name (string), product_name (string), price (number), url (string), atx_or_microatx (string), m2_slot_num (number). "
                "Ensure that the output is pure valid JSON without extra text."
            )
        elif result_items and isinstance(result_items, dict) and len(result_items) > 0:
            # Construct a description for each key from the result_items dictionary provided in settings.yaml.
            keys_description = ", ".join([f"'{key}': {desc}" for key, desc in result_items.items()])
            schema_description = (
                "A JSON object should be returned with a key 'results' mapping to a list of product objects. "
                "Each product object must have the following keys: " + keys_description + " "
                "Ensure that the output is pure valid JSON without additional text or explanations."
            )
        else:
            schema_description = (
                "A JSON object should be returned with a key 'results' mapping to a list of product objects. "
                "Each product object must contain the keys: 'product_name' (string), 'url' (string), and 'price' (number). "
                "Ensure that the output is pure valid JSON without additional text or explanations."
            )
        
        print("Using schema description: ", schema_description)
        schemas = [
            ResponseSchema(name="results", description=schema_description)
        ]
        print(f"result_str: \n{result_str}")
        # スキーマからOutputParserを作成し、LLM出力をパース
        output_parser = StructuredOutputParser.from_response_schemas(schemas)
        product_data = output_parser.parse(result_str)

        # Debug: Instead of JSON parsing, extract only the product page URL using regex.
        # print("result_str: ", result_str)
        # match = re.search(r'(https?://[^\s]+)', result_str)
        # if match:
        #     product_url = match.group(0)
        #     print("Extracted Product URL:", product_url)
        #     product_data = [{'url': product_url}]
        # else:
        #     print("No product URL found in the result.")
        #     product_data = []
    except Exception as e:
        print("Browser-Useの実行またはJSONのパースに失敗しました。エラー:", e)
    return product_data