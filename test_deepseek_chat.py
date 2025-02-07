import os

# langchain_openaiからChatOpenAIをインポートします。
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv  # .env ファイルから環境変数を読み込むためのライブラリ


def main():
  load_dotenv()
  # 環境変数からDEEPSEEK_API_KEYを取得します。
  api_key = os.getenv("DEEPSEEK_API_KEY")
  if not api_key:
    print("Error: DEEPSEEK_API_KEYが環境変数に設定されていません。")
    return

  # DeepSeekのAPIのベースURLを指定します。
  base_url = "https://api.deepseek.com"

  # deepseek-reasonerモデルを利用するために、ChatOpenAIインスタンスを作成します。
  # temperatureは生成テキストの多様性を調整するパラメータです。
  llm = ChatOpenAI(model="deepseek-chat", api_key=api_key, temperature=0.7, base_url=base_url)

  # テスト用のプロンプトを定義します。
  # ここでは単純な算数の問題を出して、正しく応答が返るかを確認します。
  prompt = "Deepseek Chat Test: What is 2 + 2?"

  try:
    # モデルに予測を実行させ、応答を取得します。
    response = llm.invoke(prompt)
    print("deepseek-chatからの応答:")
    print(response)

  except Exception as e:
    # 何らかのエラーが発生した場合、その内容を表示します。
    print("エラーが発生しました:", e)


if __name__ == '__main__':
  main() 