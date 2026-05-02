"""File-based cache manager with TTL using Apache Feather format."""
import hashlib
import json
import time
from pathlib import Path
import pandas as pd


class CacheManager:
    def __init__(self, cache_dir: Path, ttl_config: dict):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl_config

    def _key_path(self, namespace: str, key: str) -> Path:
        safe_key = hashlib.md5(key.encode()).hexdigest()[:16]
        return self.cache_dir / namespace / f"{safe_key}"

    def get(self, namespace: str, key: str) -> pd.DataFrame | None:
        path = self._key_path(namespace, key)
        feather_path = path.with_suffix(".feather")
        meta_path = path.with_suffix(".meta")
        if not feather_path.exists():
            return None
        try:
            with open(meta_path, "r") as f:
                meta = json.load(f)
            if time.time() - meta["timestamp"] > self.ttl.get(namespace, 3600):
                return None
            return pd.read_feather(feather_path)
        except Exception:
            return None

    def _sanitize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert mixed-type object columns to strings so Feather can handle them."""
        df = df.copy()
        for col in df.columns:
            if df[col].dtype == object:
                try:
                    df[col] = df[col].astype(str)
                except Exception:
                    df[col] = df[col].fillna("").astype(str)
        return df

    def set(self, namespace: str, key: str, df: pd.DataFrame):
        path = self._key_path(namespace, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._sanitize(df).to_feather(path.with_suffix(".feather"))
        with open(path.with_suffix(".meta"), "w") as f:
            json.dump({"timestamp": time.time(), "key": key}, f)

    def invalidate(self, namespace: str | None = None):
        target = self.cache_dir / namespace if namespace else self.cache_dir
        if not target.exists():
            return
        for f in target.rglob("*.feather"):
            f.unlink()
        for f in target.rglob("*.meta"):
            f.unlink()
