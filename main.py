# main.py
import argparse  # コマンドライン引数を扱うためのライブラリ
from config_loader import load_config  # 設定ファイルを読み込むモジュール
from scraper import scrape_data  # 製品情報を収集するモジュール
from ai_report_generator import generate_report_with_ai  # OpenAI APIを利用してレポート生成を行うモジュール
from dotenv import load_dotenv  # .env ファイルから環境変数を読み込むためのライブラリ


def main():
    """
    EC Compassのエントリーポイント。
    設定ファイルからデータを読み込み、各ECサイトからBrowser-Useを使って製品情報を取得し、
    その全情報をOpenAI APIに渡して、ユーザーの評価基準に基づいた上位製品（例：上位5件）のレポートを生成します。
    """
    # .env ファイルから環境変数をロード（APIキーなど）
    load_dotenv()
    # コマンドライン引数の設定
    parser = argparse.ArgumentParser(description='EC Compass - 製品比較CLIツール')
    parser.add_argument('--config', type=str, default='settings.yaml', help='設定ファイルのパス (YAML形式)')
    args = parser.parse_args()

    # 設定ファイルの内容を読み込む
    config = load_config(args.config)

    # search_parametersからwebsitesを取得する
    search_params = config.get('search_parameters', {})
    websites = search_params.get('websites', [])
    all_products = scrape_data(websites, search_params)

    # 取得した全製品情報をログ出力（初期検証用）
    print('取得した製品情報一覧:')
    for product in all_products:
        print(product)

    # settings.yamlから上位何件を選択するかの設定を取得（デフォルトは5件）
    top_n = config.get('top_n', 5)

    # settings.yaml の 'report_model' 設定でレポート生成に使用するモデルを指定
    report_model = config.get('report_model', 'gpt-4o-mini')

    # OpenAI API（LangChain経由）を利用して、ユーザーの評価基準に基づいた上位製品のレポートを生成
    report = generate_report_with_ai(all_products, config.get('criteria', {}), top_n, report_model=report_model)

    # 生成されたレポートを'report.md'ファイルに保存
    with open('report.md', 'w', encoding='utf-8') as f:
        f.write(report)

    print('OpenAIが生成したレポートが report.md に保存されました。')


if __name__ == '__main__':
    main()