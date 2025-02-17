# scraper.py

import asyncio  # 非同期処理を行うためのライブラリ
import json     # JSON形式のデータを扱うためのライブラリ
import os
import re  # 正規表現を扱うライブラリをインポートします

# Browser-Useを利用するためのエージェントをインポート
from browser_use import Agent
from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.browser.context import BrowserContextConfig
from llm_factory import get_llm

# LangChainのStructuredOutputParserを利用して、LLMの出力(result_str)をパース
from langchain.output_parsers import StructuredOutputParser, ResponseSchema


def construct_task(websites, keywords, result_items=None, return_products_num=5):
    """
    ECサイト情報、検索キーワード、および抽出すべき製品情報に基づき、
    Browser-Use に渡すタスク命令文を生成します。

    引数:
      websites: 各ECサイト情報のリスト（辞書形式）
      keywords: 検索キーワードのリスト
      result_items: 抽出すべき製品情報のキー（辞書またはリスト）
      return_products_num: 各サイトで取得する上位商品の件数

    戻り値:
      タスク命令文（文字列）
    """
    lines = []
    lines.append("以下の手順に従ってください。")
    lines.append("1. search_parameters に記載された各サイトに順にアクセスしてください。")
    lines.append("   対象サイト:")
    for site in websites:
        lines.append(f"- {site.get('name', '不明')} (URL: {site.get('url', '不明')})")
    lines.append(f"2. 各サイトごとに、空白区切りキーワード ({' '.join(keywords)}) を使用して検索してください。")
    lines.append(f"3. 検索結果ページで上位 {return_products_num} 件の商品をホイールクリックして新しいタブで開いてください。")
    if result_items:
        if isinstance(result_items, dict):
            keys = ", ".join(result_items.keys())
        else:
            keys = "、".join(result_items)
        lines.append(f"4. 各商品のタブで、{keys} に該当する情報のみを抽出し、JSON形式で記録してください。")
    else:
        lines.append("4. 各商品のタブで、製品名、価格、URL の情報のみを抽出し、JSON形式で記録してください。")
    if result_items and isinstance(result_items, dict):
        keys_description = ", ".join([f"'{k}': {v}" for k, v in result_items.items()])
        schema = ("A JSON object should be returned with key 'results' mapping to a list of product objects. "
                  "Each product object must have the following keys: " + keys_description + " Ensure that the output is pure valid JSON without extra text.")
        lines.append("JSONの形式は以下のようにしてください：")
        lines.append(schema)
    lines.append("5. 次のサイトへ進んでください。")
    lines.append("6. 全サイトの情報抽出が終了したら、記憶した全商品の情報をまとめた1つのJSONを出力してください。")
    return "\n".join(lines)


def run_browser_search(task, search_model="gpt-4o", ai_platform="openai"):
    """
    Browser-Use エージェントを使い、指定されたタスク命令文を実行して結果を取得します。

    引数:
      task: タスク命令文（文字列）
      search_model: 使用するLLMのモデル名
      ai_platform: 使用するAIプラットフォームの名前

    戻り値:
      エージェントの実行結果（文字列）
    """
    async def async_run():
        llm = get_llm(ai_platform, search_model)
        combined_task = "以下の指示に従ってください。\n" + task
        agent = Agent(task=combined_task, llm=llm, use_vision=False, generate_gif=False)
        result = await agent.run()
        if hasattr(result, "final_result"):
            result_str = result.final_result()
        elif isinstance(result, list) and result:
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