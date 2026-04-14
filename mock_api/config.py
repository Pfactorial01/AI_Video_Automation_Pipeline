from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    base_url: str = "http://localhost:8080"
    """Public base URL used in JSON responses (include scheme, no trailing slash)."""

    assets_dir: str = "mock_assets"
    """Directory containing vo.mp3, scene_*.png, scene_*.mp4, bgm_*.mp3, final.mp4."""

    scene_count: int = 5
    """Rotate scene_N assets modulo this value."""

    def assets_path(self) -> Path:
        p = Path(self.assets_dir)
        return p.resolve() if p.is_absolute() else (Path.cwd() / p).resolve()


settings = Settings()
