"""Configuration.

One settings object, assembled from environment variables and an optional YAML
file. Each module owns one nested section; nobody reads `os.environ` directly,
so every knob is discoverable in one place and typed.

Environment variables are prefixed and nested with `__`, e.g.
`VERIFACT_VERIFICATION__TAU_SUP=0.25`.

Secrets come from the environment only (SR-08). There is no default API key: if
auth is enabled and no key is set, startup fails loudly rather than serving an
open endpoint.
"""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class InputSettings(BaseModel):
    max_chars: int = Field(default=20_000, ge=1)
    max_sentences: int = Field(default=400, ge=1)
    max_claims: int = Field(default=600, ge=1)
    normalize_unicode: bool = True


class ExtractionSettings(BaseModel):
    #: "spacy" uses the installed model; "regex" is the dependency-free fallback.
    backend: Literal["spacy", "regex", "auto"] = "auto"
    spacy_model: str = "en_core_web_sm"
    llm_decomposer_enabled: bool = False
    llm_decomposer_model: str | None = None


class RetrievalSettings(BaseModel):
    registry_path: Path = Path("config/sources.yaml")
    top_k: int = Field(default=3, ge=1)
    top_k_escalated: int = Field(default=10, ge=1)
    bm25_k1: float = 1.5
    bm25_b: float = 0.75
    #: RRF constant. 60 is the value from cormack2009rrf; recorded, not copied silently.
    rrf_k: int = 60
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    #: "dense" needs the ml extra; "lexical" is BM25 only.
    backend: Literal["dense", "lexical", "auto"] = "auto"
    http_timeout_s: float = 10.0
    max_response_bytes: int = 2_000_000
    requests_per_second: float = 1.0
    cache_dir: Path = Path(".cache/http")
    offline: bool = False
    user_agent: str = "VeriFact/0.1 (academic project; contact via repository)"


class KGSettings(BaseModel):
    enabled: bool = True
    max_hops: int = Field(default=2, ge=1, le=3)
    max_nodes: int = Field(default=400, ge=1)
    sparql_endpoint: str = "https://query.wikidata.org/sparql"
    supported_predicates_path: Path = Path("config/kg_predicates.yaml")


class VerificationSettings(BaseModel):
    nli_model: str = "cross-encoder/nli-deberta-v3-small"
    nli_model_escalated: str = "cross-encoder/nli-deberta-v3-base"
    backend: Literal["transformer", "lexical", "auto"] = "auto"
    # Decision thresholds. Fitted on dev and frozen (ADR-005). These defaults are
    # placeholders until the freeze; the frozen values live in config/thresholds.yaml
    # and the freeze commit is recorded in docs/testing/test-report.md.
    tau_cov: float = Field(default=0.15, ge=0.0, le=1.0)
    #: Minimum absolute claim-passage similarity for evidence to count as
    #: on topic at all. Guards against min-max relevance inflation (EA-07).
    tau_sim: float = Field(default=0.35, ge=0.0, le=1.0)
    tau_weak: float = Field(default=0.35, ge=0.0, le=1.0)
    tau_sup: float = Field(default=0.20, ge=0.0, le=1.0)
    tau_con: float = Field(default=0.20, ge=0.0, le=1.0)
    #: Near-duplicate passages above this cosine are collapsed before weighting (FR-34).
    dedup_threshold: float = Field(default=0.95, ge=0.0, le=1.0)
    calibration_method: Literal["temperature", "isotonic", "none"] = "temperature"
    calibrator_path: Path = Path("config/calibrator.json")
    adaptive_budget: bool = True
    #: Escalate when |E - C| falls inside this band around a decision threshold.
    escalate_margin: float = Field(default=0.10, ge=0.0, le=1.0)


class ApiSettings(BaseModel):
    auth_enabled: bool = True
    #: Set via VERIFACT_API__API_KEYS='["key1","key2"]'. Never defaulted.
    api_keys: list[str] = Field(default_factory=list)
    rate_limit_per_minute: int = Field(default=60, ge=1)
    cors_origins: list[str] = Field(default_factory=list)


class LogSettings(BaseModel):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    json_format: bool = True
    #: Raw input text is redacted at this level and above (NFR-15, SR-07).
    redact_text: bool = True


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VERIFACT_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["dev", "test", "prod"] = "dev"
    #: SQLite by default so a clone runs with no services; Postgres in compose.
    database_url: str = "sqlite+pysqlite:///./verifact.db"
    seed: int = 20261102

    input: InputSettings = Field(default_factory=InputSettings)
    extraction: ExtractionSettings = Field(default_factory=ExtractionSettings)
    retrieval: RetrievalSettings = Field(default_factory=RetrievalSettings)
    kg: KGSettings = Field(default_factory=KGSettings)
    verification: VerificationSettings = Field(default_factory=VerificationSettings)
    api: ApiSettings = Field(default_factory=ApiSettings)
    log: LogSettings = Field(default_factory=LogSettings)

    @model_validator(mode="after")
    def _auth_is_configured(self) -> Settings:
        """Refuse to start an authenticated API with no keys.

        Checked here rather than on ApiSettings so it runs once the environment
        has been applied, not at import time.
        """
        if self.api.auth_enabled and not self.api.api_keys:
            raise ValueError(
                "API auth is enabled but no keys are configured. Set "
                "VERIFACT_API__API_KEYS, or VERIFACT_API__AUTH_ENABLED=false for "
                "local development. Refusing to serve an unauthenticated API."
            )
        return self

    def config_hash(self) -> str:
        """Stable hash of everything that can change a result (FR-62).

        Excludes operational fields that cannot affect a verdict, so a run is not
        marked irreproducible merely because the log level changed.
        """
        payload = self.model_dump(mode="json", exclude={"log", "api", "environment"})
        blob = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(blob.encode()).hexdigest()[:16]

    @classmethod
    def from_yaml(cls, path: Path, **overrides: Any) -> Settings:
        """Load a YAML file as a base, with environment still taking precedence."""
        data: dict[str, Any] = {}
        if path.exists():
            data = yaml.safe_load(path.read_text()) or {}
        return cls(**{**data, **overrides})


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings, suitable as a FastAPI dependency.

    Tests call `get_settings.cache_clear()` after changing the environment.
    """
    return Settings()
