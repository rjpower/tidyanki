import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def find_root():
    """Find the project root by looking for pyproject.toml"""
    path = Path(__file__).parent
    while not (path / "pyproject.toml").exists():
        path = path.parent
    return path


ROOT_DIR = find_root()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        secrets_dir=os.environ.get("SECRETS_DIR", ROOT_DIR / "secrets")
    )

    ROOT_DIR: Path = ROOT_DIR

    GOOGLE_SERVICE_ACCOUNT_INFO: dict | None = None
    GEMINI_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None

    def model_post_init(self, __context) -> None:
        super().model_post_init(__context)

        # expose API keys for litellm
        if self.OPENAI_API_KEY:
            os.environ["OPENAI_API_KEY"] = self.OPENAI_API_KEY
        if self.GEMINI_API_KEY:
            os.environ["GEMINI_API_KEY"] = self.GEMINI_API_KEY
        if self.GOOGLE_SERVICE_ACCOUNT_INFO:
            assert isinstance(self.GOOGLE_SERVICE_ACCOUNT_INFO, dict)


settings = Settings()  # type: ignore
