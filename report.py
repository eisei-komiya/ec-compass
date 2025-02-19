import os
import json
import re
from llm_factory import get_llm


def generate_report(product_results, evaluation_criteria, top_n, report_model="gpt-4o-mini", ai_platform="openai"):
    """
    製品情報と評価基準に基づき、Markdown形式のレポートを生成します。

    引数:
      product_results: 各ECサイトから収集した製品情報（リストまたは辞書）
      evaluation_criteria: 評価基準の辞書（ユーザーの自然言語による preferences を含む）
      top_n: 上位抽出件数
      report_model: レポート生成に使用するモデル名
      ai_platform: 使用するAIプラットフォームの名前

    戻り値:
      生成されたMarkdown形式のレポート（文字列）
    """
    # ユーザーの preferences を取得
    user_preferences = evaluation_criteria.get('preferences', 'できるだけ安価な商品を探してください')

    prompt = (
        "以下の情報に基づいて調査レポートを生成してください。\n\n"
        "【ユーザーの希望】\n"
        f"{user_preferences}\n\n"
        "【製品情報】\n"
        "各製品について以下の情報が含まれています：\n"
        "・商品名\n"
        "・価格\n"
        "・URL\n"
        "・口コミ情報\n"
        "・商品の詳細情報（特徴、仕様など）\n\n"
        "特に以下の点に注意してレポートを作成してください：\n"
        "1. ユーザーの希望に沿った製品を優先的に取り上げる\n"
        "2. 口コミ情報を活用して、実際のユーザー評価を反映する\n"
        "3. 商品の特徴や仕様を分かりやすく説明する\n"
        "4. 価格についても言及し、コストパフォーマンスの観点からコメントを付ける\n\n"
        "以下が製品情報の詳細です：\n"
        f"{str(product_results)}\n\n"
        "レポートはMarkdown形式で作成し、見出しや箇条書きを適切に使用して読みやすく構造化してください。"
    )

    combined_prompt = "あなたはプロフェッショナルな製品レビューアーとして、以下の製品情報を分析し、ユーザーの希望に沿ったレポートを作成してください。\n" + prompt

    variant = "genai" if ai_platform.lower() == "google" else None
    try:
        llm = get_llm(ai_platform, report_model, variant=variant)
        report = llm.invoke(combined_prompt).content
    except Exception as e:
        print(f"レポート生成中にエラーが発生しました: {e}")
        return "レポート生成に失敗しました。"

    # 不要なコードブロックのマーカー (```) を削除
    report = re.sub(r'^```.*?\n', '', report, flags=re.DOTALL)
    report = re.sub(r'\n```$', '', report, flags=re.DOTALL)
    return report 