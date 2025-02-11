import os
import json
import re
from llm_factory import get_llm


def generate_report(product_results, evaluation_criteria, top_n, report_model="gpt-4o-mini", ai_platform="openai"):
    """
    製品情報と評価基準に基づき、Markdown形式のレポートを生成します。

    引数:
      product_results: 各ECサイトから収集した製品情報（リストまたは辞書）
      evaluation_criteria: 評価基準の辞書
      top_n: 上位抽出件数（利用目的によっては使用しない場合もあります）
      report_model: レポート生成に使用するモデル名
      ai_platform: 使用するAIプラットフォームの名前

    戻り値:
      生成されたMarkdown形式のレポート（文字列）
    """
    prompt = (
        "以下は各ECサイトの製品情報と評価基準です。詳細なレポートをMarkdown形式で作成してください。\n\n"
        "【各ECサイトの製品情報】\n" + json.dumps(product_results, ensure_ascii=False, indent=2) + "\n\n"
        "【評価基準】\n" + json.dumps(evaluation_criteria, ensure_ascii=False, indent=2) + "\n\n"
        "・各評価項目について、メリットと改善点を解説してください。\n"
        "・出力はMarkdown形式のみで、余計なコードブロック等は含めないでください。\n"
    )
    combined_prompt = "あなたはプロフェッショナルなレポート作成アシスタントです。\n" + prompt

    variant = "genai" if ai_platform.lower() == "google" else None
    try:
        llm = get_llm(ai_platform, report_model, variant=variant)
        report = llm.invoke(combined_prompt).content
    except Exception as e:
        print(f"レポート生成中にエラーが発生しました: {e}.")
        return "レポート生成に失敗しました。"

    # 不要なコードブロックのマーカー (```) を削除
    report = re.sub(r'^```.*?\n', '', report, flags=re.DOTALL)
    report = re.sub(r'\n```$', '', report, flags=re.DOTALL)
    return report 