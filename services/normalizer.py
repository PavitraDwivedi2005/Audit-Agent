# services/normalizer.py
from typing import Dict, Any

class MetricsNormalizer:
    """
    Normalizes outputs from various scrapers into a single unified schema.
    """
    def normalize(self, source: str, raw_metrics: Dict[str, Any]) -> Dict[str, Any]:
        if source == "nja":
            return self._normalize_nja(raw_metrics)
        elif source == "toolzu":
            return self._normalize_toolzu(raw_metrics)
        elif source == "socialinsider":
            return self._normalize_socialinsider(raw_metrics)
        else:
            raise ValueError(f"Unknown scraper source: {source}")

    def _normalize_nja(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        def get_val(section: str, field: str):
            sec = metrics.get(section, {})
            obj = sec.get(field, {})
            # If status is not 'ok', return None
            if obj.get("status") != "ok":
                return None
            val = obj.get("value")
            return float(val) if val is not None else None

        return {
            "followers": get_val("profile_metrics", "followers"),
            "following": get_val("profile_metrics", "following"),
            "posts_count": get_val("profile_metrics", "posts_count"),
            "avg_likes": get_val("engagement_metrics", "avg_likes"),
            "avg_comments": get_val("engagement_metrics", "avg_comments"),
            "engagement_rate": get_val("engagement_metrics", "engagement_rate"),
            "growth_rate": get_val("growth_metrics", "growth_rate"),
            "authenticity_score": get_val("authenticity_metrics", "authenticity_score"),
        }
        
    def _normalize_toolzu(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        # TODO: Map toolzu specific fields to unified schema
        return {}

    def _normalize_socialinsider(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        # TODO: Map socialinsider specific fields to unified schema
        return {}
