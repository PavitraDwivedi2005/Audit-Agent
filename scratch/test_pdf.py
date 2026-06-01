# scratch/test_pdf.py
# Verification script for PDF compilation.

import os
import sys

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.pdf_generator import generate_pdf_report

mock_metrics = {
    "creator_username": "life_with_janvi",
    "source_platform": "NotJustAnalytics",
    "profile_metrics": {
        "followers": 829,
        "following": 312,
        "posts": 118,
        "bio": "Lifestyle + real thoughts"
    },
    "engagement_metrics": {
        "avg_likes": 1680,
        "avg_comments": 13,
        "engagement_rate": 20.79,
        "avg_views": 5200
    },
    "hashtag_metrics": {
        "top_hashtags": ["explorepage", "trending", "viralreels"]
    },
    "content_metrics": {
        "posting_frequency": 0.5
    }
}

mock_report = """1. INSTAGRAM PROFILE AUDIT SUMMARY
• Username: life_with_janvi
• Current positioning: General lifestyle & aesthetics. Insight: Potential is high but niche is unfocused.

2. CORE ACCOUNT METRICS
• Followers: 829. Insight: Solid base starting point.
• Engagement Rate: 20.79%. Insight: Extremely high but inflated due to recent cafe spikes.

6. KEY INSIGHTS
1. You already have viral potential with reels hitting 7k likes.
2. Inconsistency is your biggest growth blocker.

7. ACTIONABLE RECOMMENDATIONS
1. Target Cafe Discovery in Rajkot & Ahmedabad.
2. Set up content pillars: 40% Aesthetic Places, 30% POV feelings."""

print("Compiling PDF...")
try:
    pdf_bytes = generate_pdf_report("life_with_janvi", mock_report, mock_metrics)
    output_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_audit.pdf"))
    
    with open(output_path, "wb") as f:
        f.write(pdf_bytes)
        
    print(f"SUCCESS! PDF written to: {output_path}")
except Exception as e:
    print(f"FAILED: {e}")
