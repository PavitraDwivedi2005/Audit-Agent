# services/validator.py
from typing import Dict, Any, List

class AuditValidator:
    """
    Validates structured influencer metrics for anomalies.
    Returns a list of warning messages.
    """
    def validate(self, nested_metrics: Dict[str, Any]) -> List[str]:
        warnings = []
        
        prof = nested_metrics.get("profile_metrics", {})
        eng = nested_metrics.get("engagement_metrics", {})
        
        followers_obj = prof.get("followers", {})
        followers = followers_obj.get("value")
        
        engagement_rate_obj = eng.get("engagement_rate", {})
        er = engagement_rate_obj.get("value")
        
        if followers and followers > 100000:
            if er is None or er == 0:
                warnings.append(f"Suspiciously missing engagement rate for account with {followers:,.0f} followers.")
                
        # Future validation rules can be added here
        
        return warnings
