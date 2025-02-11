import os


def get_llm(ai_platform: str, model: str, variant: str = "genai"):
    """
    共通のLLMインスタンスを作成するファクトリ関数です。

    引数:
      ai_platform: 使用するAIプラットフォームの名前（例: 'deepseek', 'google', 'openai'）
      model: 使用するモデル名
      variant: googleプラットフォームの場合のバリアント（例: 'genai' を指定すると ChatGoogleGenerativeAI を利用し、指定しない場合は ChatVertexAI を利用）

    戻り値:
      作成されたLLMインスタンス
    """
    platform = ai_platform.lower()

    if platform == "deepseek":
        from langchain_openai import ChatOpenAI
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        api_key = os.getenv("DEEPSEEK_API_KEY")
        extra = {"base_url": base_url} if base_url else {}
        return ChatOpenAI(model=model, api_key=api_key, temperature=0.7, **extra)

    elif platform == "google":
        api_key = os.getenv("GOOGLE_API_KEY")
        if variant == "genai":
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(model=model, api_key=api_key, temperature=0.7)
        else:
            from langchain_google_vertexai import ChatVertexAI
            return ChatVertexAI(model=model, api_key=api_key, temperature=0.7)

    elif platform == "openai":
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        return ChatOpenAI(model=model, api_key=api_key, temperature=0.7)

    else:
        # デフォルトはOpenAIを使用
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        return ChatOpenAI(model=model, api_key=api_key, temperature=0.7) 