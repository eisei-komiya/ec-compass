# main.py
import argparse  # コマンドライン引数を扱うためのライブラリ
from config_loader import load_config  # 設定ファイルを読み込むモジュール
from scraper import scrape_data  # 製品情報を収集するモジュール
from report import generate_report  # レポート生成モジュール（旧ai_report_generator）
from dotenv import load_dotenv  # .env ファイルから環境変数を読み込むためのライブラリ


def main():
    """
    EC Compassのエントリーポイント。
    設定ファイルからデータを読み込み、各ECサイトからBrowser-Useを使って製品情報を取得し、
    その全情報を基に評価基準に従ったレポートを生成します。
    """
    load_dotenv()  # .envファイルから環境変数をロード

    # コマンドライン引数の設定
    parser = argparse.ArgumentParser(description='EC Compass - 製品比較CLIツール')
    parser.add_argument('--config', type=str, default='settings.yaml', help='設定ファイルのパス (YAML形式)')
    args = parser.parse_args()

    # 設定ファイルの読み込み
    config = load_config(args.config)

    # 製品情報の取得
    search_params = config.get('search_parameters', {})
    websites = search_params.get('websites', [])
    all_products = scrape_data(websites, search_params)
    print('debug:')
    print(all_products)

    # レポート生成設定の取得
    top_n = config.get('top_n', 5)
    ai_platform = config.get('ai_platform', 'openai')
    report_model = config.get('report_model', 'gpt-4o-mini')

    # レポート生成
    report = generate_report(all_products, config.get('criteria', {}), top_n, report_model=report_model, ai_platform=ai_platform)

    # 生成されたレポートの保存
    with open('report.md', 'w', encoding='utf-8') as f:
        f.write(report)

    print('OpenAIが生成したレポートが report.md に保存されました。')


if __name__ == '__main__':
    main()