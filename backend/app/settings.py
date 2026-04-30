from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ZJGSU-IEE-Portal"
    database_url: str = "sqlite+aiosqlite:///./data.db"

    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None

    # Aliyun DashScope (Qwen) OpenAI-compatible mode
    # If LLM_* not provided, DASHSCOPE_API_KEY will be used automatically.
    dashscope_api_key: str | None = None
    dashscope_model: str | None = None

    admin_token: str | None = None

    def effective_llm_base_url(self) -> str | None:
        if self.llm_base_url:
            return self.llm_base_url
        if self.dashscope_api_key:
            return "https://dashscope.aliyuncs.com/compatible-mode/v1"
        return None

    def effective_llm_api_key(self) -> str | None:
        if self.llm_api_key:
            return self.llm_api_key
        if self.dashscope_api_key:
            return self.dashscope_api_key
        return None

    def effective_llm_model(self) -> str | None:
        if self.llm_model:
            return self.llm_model
        if self.dashscope_api_key:
            return self.dashscope_model or "qwen-plus"
        return None


settings = Settings()

