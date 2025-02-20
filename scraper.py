# scraper.py

import asyncio  # 非同期処理を行うためのライブラリ
import json     # JSON形式のデータを扱うためのライブラリ
import os
import re  # 正規表現を扱うライブラリをインポートします
import datetime

# Browser-Useを利用するためのエージェントをインポート
from browser_use import Agent
from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.browser.context import BrowserContextConfig
from llm_factory import get_llm

# LangChainのStructuredOutputParserを利用して、LLMの出力(result_str)をパース
from langchain.output_parsers import StructuredOutputParser, ResponseSchema


def construct_task(websites, keywords, result_items=None, return_products_num=5, search_condition=None, browser_settings=None):
    """
    ECサイト情報、検索キーワード、および抽出すべき製品情報に基づき、
    Browser-Use に渡すタスク命令文を生成します。

    引数:
      websites: 各ECサイト情報のリスト（辞書形式）
      keywords: 検索キーワードのリスト
      result_items: 抽出すべき製品情報のキー（辞書またはリスト）
      return_products_num: 各サイトで取得する上位商品の件数
      search_condition: 検索条件（価格範囲、並び順、フィルター等）
      browser_settings: ブラウザの動作設定（vision使用有無、公式サイト訪問有無等）

    戻り値:
      タスク命令文（文字列）
    """
    lines = []
    lines.append("以下の手順に従ってください。")
    
    # 1. サイトアクセス
    lines.append("1. 対象サイトに順にアクセスしてください。")
    lines.append("   対象サイト:")
    for site in websites:
        lines.append(f"- {site.get('name', '不明')} (URL: {site.get('url', '不明')})")

    lines.append("また、サイト訪問中にモーダルウィンドウで広告が出ることがあります。そのときは、閉じるボタンで閉じてから再開してください。")
    # 2. 検索実行
    lines.append(f"2. 各サイトごとに、空白区切りキーワード ({' '.join(keywords)}) を使用して検索してください。")
    
    # 3. 検索条件の適用
    if search_condition:
        lines.append("3. 以下の条件で検索結果を絞り込んでください：")
        
        # 価格範囲
        if 'price_range' in search_condition:
            price_range = search_condition['price_range']
            if price_range.get('min') is not None:
                lines.append(f"   - 最低価格: {price_range['min']}円以上")
            if price_range.get('max') is not None:
                lines.append(f"   - 最高価格: {price_range['max']}円以下")
        
        # 並び順
        if 'sort_by' in search_condition:
            lines.append(f"   - 並び順: {search_condition['sort_by']}")
        
        # フィルター条件
        if 'filters' in search_condition and search_condition['filters']:
            lines.append("   - 追加の絞り込み条件（可能な場合のみ適用してください）:")
            for filter_condition in search_condition['filters']:
                lines.append(f"     ・{filter_condition}")
            lines.append("   ※ フィルタリングができない場合は、この条件を無視して商品情報を取得してください。")
    
    # 4. 商品ページを開く
    lines.append(f"4. 検索結果ページで上位 {return_products_num} 件の商品をホイールクリックして新しいタブで開いてください。")
    lines.append("   ※ フィルタリングができなかった場合は、価格帯に合う商品を優先的に選んでください。")
    
    # 5. 情報抽出
    if result_items:
        # 基本情報の抽出
        extract_info = "5. 各商品のタブで、以下の情報を抽出してください："
        lines.append(extract_info)
        lines.append("   - 商品名")
        lines.append("   - 価格")
        lines.append("   - URL")
        
        # 口コミ情報の取得設定
        reviews_per_product = browser_settings.get('reviews_per_product', 3)
        if reviews_per_product == 0:
            lines.append("   - 口コミ情報は取得不要です")
        elif reviews_per_product == -1:
            lines.append("   - 全ての口コミ情報を取得してください")
        else:
            lines.append(f"   - 評価の高い順で{reviews_per_product}件の口コミ情報を取得してください")
        
        lines.append("   - 商品の詳細情報（特徴、仕様、説明など）")
        
        # 公式サイト訪問が有効な場合
        if browser_settings and browser_settings.get('visit_official_site'):
            lines.append("   その後、以下の手順で公式情報を取得してください：")
            lines.append("   1. 商品ページからメーカーの公式サイトへのリンクを見つけてください")
            lines.append("   2. リンクが無ければ、商品名で検索して公式サイトのページを開いてください")
            lines.append("   2. 公式サイトで該当製品のページを開いてください")
            lines.append("   3. 公式サイトから詳細な製品仕様と特徴を抽出してください")
            lines.append("   4. メーカーの公式サイトURLを記録してください")
        
        # JSON形式の指定
        lines.append("6. 抽出した情報を以下のキーを使用してJSONオブジェクトとして記録してください：")
        for key, desc in result_items.items():
            lines.append(f"   - {key}: {desc}")
    else:
        lines.append("5. 各商品のタブで、製品名、価格、URL の情報のみを抽出し、JSON形式で記録してください。")
    
    # JSON形式の詳細指定
    if result_items and isinstance(result_items, dict):
        keys_description = ", ".join([f"'{k}': {v}" for k, v in result_items.items()])
        schema = (
            "最終的な出力は以下の形式の純粋なJSONのみとしてください：\n"
            "{\n"
            '  "results": [\n'
            "    {\n"
            "      " + ",\n      ".join([f'"{k}": "値"' for k in result_items.keys()]) + "\n"
            "    },\n"
            "    ...\n"
            "  ]\n"
            "}\n\n"
            "注意事項：\n"
            "- 追加のテキストや説明は一切含めないでください\n"
            "- 必ず全ての商品情報を results 配列に含めてください\n"
            "- 各商品オブジェクトには以下のキーを必ず含めてください：" + keys_description
        )
        lines.append("JSONの形式は以下のようにしてください：")
        lines.append(schema)
    
    # 最後の手順
    lines.append("7. 次のサイトへ進んでください。")
    lines.append("8. 全サイトの情報抽出が終了したら、必ず以下のJSON形式で全商品の情報をまとめて出力してください。")
    lines.append("   フィルタリングができなかった場合でも、取得できた商品情報は必ずJSON形式で出力してください。")
    lines.append("   出力の際は、JSONデータのみを出力し、説明文や追加のテキストは一切含めないでください。")
    lines.append("   エラーメッセージや説明は出力せず、純粋なJSONデータのみを出力してください。")
    
    return "\n".join(lines)


def run_browser_search(task, search_model="gpt-4o", ai_platform="openai", use_vision=True):
    """
    Browser-Use エージェントを使い、指定されたタスク命令文を実行して結果を取得します。

    引数:
      task: タスク命令文（文字列）
      search_model: 使用するLLMのモデル名
      ai_platform: 使用するAIプラットフォームの名前
      use_vision: ブラウザの視覚情報を使用するかどうか（True/False）

    戻り値:
      エージェントの実行結果（文字列）
    """
    async def async_run():
        llm = get_llm(ai_platform, search_model)
        combined_task = "以下の指示に従ってください。\n" + task
        agent = Agent(task=combined_task, llm=llm, use_vision=use_vision, generate_gif=False)
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
      websites: 複数のECサイト情報を含むリスト
      search_parameters: 検索条件を含む辞書

    戻り値:
      製品情報を含むリスト。各製品情報は辞書形式です。
    """
    # 各種パラメータの取得
    keywords = search_parameters.get("keywords", [])
    result_items = search_parameters.get("result_items", [])
    return_products_num = search_parameters.get("return_products_num", None)
    search_condition = search_parameters.get("search_condition", {})
    browser_settings = search_parameters.get("browser_settings", {})
    
    # タスク命令文の作成
    task_instruction = construct_task(
        websites,
        keywords,
        result_items,
        return_products_num,
        search_condition,
        browser_settings
    )
    
    product_data = []

    try:
        # AIモデルの設定を取得
        search_model = search_parameters.get("search_model", "gpt-4o")
        ai_platform = search_parameters.get("ai_platform", "openai")
        use_vision = browser_settings.get("use_vision", True)

        # Browser-Useの実行
        result_str = run_browser_search(task_instruction, search_model, ai_platform, use_vision)
        
        # スキーマの設定
        if ai_platform.lower() == "google":
            schema_description = (
                "A JSON object with key 'results', where results is an array of objects. "
                "Each object must have the following properties: site_name (string), product_name (string), "
                "price (number), url (string), reviews (string), details (string), "
                "manufacturer_url (string). "
                "Ensure that the output is pure valid JSON without extra text."
            )
        elif result_items and isinstance(result_items, dict) and len(result_items) > 0:
            keys_description = ", ".join([f"'{key}': {desc}" for key, desc in result_items.items()])
            schema_description = (
                "A JSON object should be returned with a key 'results' mapping to a list of product objects. "
                "Each product object must have the following keys: " + keys_description + " "
                "Ensure that the output is pure valid JSON without additional text or explanations."
            )
        else:
            schema_description = (
                "A JSON object should be returned with a key 'results' mapping to a list of product objects. "
                "Each product object must contain the keys: 'product_name' (string), 'url' (string), and "
                "'price' (number). Ensure that the output is pure valid JSON without additional text or explanations."
            )
        
        print("Using schema description: ", schema_description)
        schemas = [
            ResponseSchema(name="results", description=schema_description)
        ]
        print(f"result_str: \n{result_str}")
        
        # 結果のパース
        try:
            output_parser = StructuredOutputParser.from_response_schemas(schemas)
            product_data = output_parser.parse(result_str)

            # パース済みのデータを保存
            with open('scraped_data.json', 'w', encoding='utf-8') as f:
                json.dump(product_data, f, ensure_ascii=False, indent=2)
            print("スクレイピング結果を scraped_data.json に保存しました。")

        except Exception as e:
            print("JSONのパースに失敗しました。生の結果を使用します。エラー:", e)
            # パースに失敗した場合は、生の結果文字列をそのまま返す
            product_data = result_str
            # 生の結果も保存しておく
            with open('scraped_data.txt', 'w', encoding='utf-8') as f:
                f.write(result_str)
            print("生のスクレイピング結果を scraped_data.txt に保存しました。")

    except Exception as e:
        print("Browser-Useの実行に失敗しました。エラー:", e)
        product_data = "Browser-Useの実行に失敗しました。"
    
    return product_data