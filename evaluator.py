# evaluator.py

def evaluate_product(product_info, criteria):
    """
    製品情報と評価基準に基づいて、製品の評価スコアを計算します。
    戻り値:
      float 型の評価スコア
    """
    score = 0.0

    # 価格評価
    if 'price' in product_info and 'price' in criteria:
        price_settings = criteria['price']
        weight = price_settings.get('weight', 0)
        threshold = price_settings.get('threshold', 0)
        if product_info['price'] <= threshold:
            score += weight * 10
        else:
            score += weight * (10 * threshold / product_info['price'])


    # レビュー評価
    if 'reviews' in product_info:
        score += 0.1 * product_info['reviews']

    return score 