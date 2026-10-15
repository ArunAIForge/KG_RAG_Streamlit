# config/settings.py
import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "TN-KG-RAG"
    DEBUG: bool = False
    DATA_DIR: Path = Path(__file__).resolve().parent.parent / "data" / "raw"

    # LLM Settings (OpenAI or compatible provider)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL_NAME: str = "gpt-4o-mini"
    TEMPERATURE: float = 0.0

    # Neo4j AuraDB Settings
    NEO4J_URI: str = "neo4j+s://your-instance.databases.neo4j.io"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = ""

    # Scraper Settings
    TN_PORTAL_URL: str = "https://www.tn.gov.in/scheme_list.php?dep_id=Mg=="
    SCRAPE_HEADLESS: bool = True
    PAGE_TIMEOUT_MS: int = 45000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

# Ensure directories exist
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)