# scratch/verify_benchmark.py
# Verification script for the Multi-Model Benchmarking pipeline.

import os
import sys
import gzip
from datetime import datetime

# Adjust sys.path to resolve module imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import Session, Influencer, AuditRun, NormalizedMetrics, BenchmarkReport
from services.report_generator import ReportGeneratorService
from services.storage_manager import StorageManager

test_metrics = {
  "creator_username": "life_with_janvi",
  "source_platform": "NotJustAnalytics",
  "profile_metrics": {
    "followers": 829,
    "following": 118,
    "posts": 118,
    "bio": "Lifestyle, but make it real"
  },
  "engagement_metrics": {
    "avg_likes": 1680,
    "avg_comments": 13,
    "engagement_rate": 20.79,
    "avg_views": 5000,
    "avg_shares": 100,
    "avg_saves": 250
  },
  "growth_metrics": {
    "followers_growth": 50,
    "monthly_growth_rate": 2.5,
    "daily_avg_growth": 1.6
  },
  "hashtag_metrics": {
    "top_hashtags": ["#rajkotcafes", "#explorepage"]
  },
  "content_metrics": {
    "avg_reels_views": 6700,
    "posting_frequency": 0.5,
    "total_reels": 50,
    "total_carousels": 40,
    "total_images": 28
  },
  "audience_metrics": {
    "top_countries": ["India"],
    "top_cities": ["Rajkot"],
    "gender_split": "70% Female / 30% Male",
    "age_range": "18-24"
  },
  "additional_metrics": {}
}

def verify_pipeline():
    print("=== STARTING MULTI-MODEL BENCHMARK PIPELINE VERIFICATION ===")
    
    # 1. Verify Database Registration of AuditRun and NormalizedMetrics
    print("\n1. Testing Database Registration...")
    try:
        with Session() as session:
            # Get or create influencer
            influencer = session.query(Influencer).filter_by(username="life_with_janvi").first()
            if not influencer:
                influencer = Influencer(username="life_with_janvi")
                session.add(influencer)
                session.commit()
                
            # Create AuditRun
            audit_run = AuditRun(influencer_id=influencer.id, status="benchmark_verify")
            session.add(audit_run)
            session.commit()
            audit_run_id = audit_run.id
            
            # Save NormalizedMetrics
            db_metrics = NormalizedMetrics(
                audit_run_id=audit_run_id,
                followers=829.0,
                following=118.0,
                posts_count=118.0,
                avg_likes=1680.0,
                avg_comments=13.0,
                engagement_rate=20.79,
                growth_rate=2.5,
                authenticity_score=None
            )
            session.add(db_metrics)
            session.commit()
            
            print(f"   [SUCCESS] Registered AuditRun ID: {audit_run_id} and saved NormalizedMetrics successfully.")
    except Exception as e:
        print(f"   [FAILURE] Database registration failed: {str(e)}")
        return False
        
    # 2. Test OpenRouter Call (Try each model until one succeeds to verify connectivity and save flows)
    print("\n2. Testing OpenRouter API Calls...")
    generator = ReportGeneratorService()
    
    successful_res = None
    successful_model = None
    
    for model_key in ["Llama 3.3 70B", "Hermes 3 Llama 3.1 405B", "Qwen 3 Next 80B", "GPT-OSS 120B"]:
        print(f"   Trying model: {model_key}...")
        res = generator.generate_report(model_key, test_metrics, "life_with_janvi")
        if res.get("error"):
            print(f"      [INFO] {model_key} failed: {res['error']}")
        else:
            print(f"      [SUCCESS] Received response from {model_key}!")
            successful_res = res
            successful_model = model_key
            break
            
    if not successful_res:
        print("   [FAILURE] All 4 free models failed or were rate-limited/timed out right now. (Upstream OpenRouter transient issue)")
        return False
        
    print(f"   - Latency: {successful_res['latency']}s")
    print(f"   - Input Tokens: {successful_res['prompt_tokens']}")
    print(f"   - Output Tokens: {successful_res['completion_tokens']}")
    print(f"   - Preview of generated report (first 150 chars):\n")
    safe_preview = successful_res["report_text"][:150].encode("ascii", errors="replace").decode("ascii")
    print("     " + safe_preview.replace("\n", "\n     ") + "...")
        
    # 3. Test Storage Manager Double Persistence
    print("\n3. Testing Storage Manager Persistence...")
    try:
        storage = StorageManager()
        
        # Save locally
        local_path = storage.save_report_locally("life_with_janvi", successful_model, successful_res["report_text"])
        print(f"   [SUCCESS] Local report stored at: {local_path}")
        if not os.path.exists(local_path):
            print("   [FAILURE] Local report file does not exist!")
            return False
            
        # Save to DB
        db_success = storage.save_report_to_db(
            audit_run_id=audit_run_id,
            employee_username="verifier_bot",
            model_used=successful_model,
            report_text=successful_res["report_text"],
            raw_model_response=successful_res["raw_response"],
            latency=successful_res["latency"],
            prompt_tokens=successful_res["prompt_tokens"],
            completion_tokens=successful_res["completion_tokens"]
        )
        
        if db_success:
            print("   [SUCCESS] Compressed report saved to PostgreSQL.")
        else:
            print("   [FAILURE] Saving compressed report to DB returned failure status.")
            return False
    except Exception as e:
        print(f"   [FAILURE] Double persistence failed: {str(e)}")
        return False
        
    # 4. Verify Gzip Database Compression & Decompression
    print("\n4. Verifying Gzip Database Archival and Decompression Integrity...")
    try:
        with Session() as session:
            db_report = session.query(BenchmarkReport).filter_by(audit_run_id=audit_run_id, model_used=successful_model).first()
            if not db_report:
                print("   [FAILURE] Could not retrieve the inserted BenchmarkReport from DB.")
                return False
                
            compressed_bytes = db_report.compressed_report
            decompressed_text = gzip.decompress(compressed_bytes).decode("utf-8")
            
            if decompressed_text == successful_res["report_text"]:
                print("   [SUCCESS] Gzip compression/decompression verified. Integrity matches 100%.")
                print(f"   - Raw size: {len(successful_res['report_text'].encode('utf-8'))} bytes")
                print(f"   - Compressed size: {len(compressed_bytes)} bytes")
                print(f"   - Compression ratio: {len(compressed_bytes)/len(successful_res['report_text'].encode('utf-8')):.1%}")
            else:
                print("   [FAILURE] Decompressed report text does not match the original report text!")
                return False
    except Exception as e:
        print(f"   [FAILURE] Compression integrity verification failed: {str(e)}")
        return False

    print("\n=== PIPELINE VERIFICATION COMPLETED WITH 100% SUCCESS ===")
    return True

if __name__ == "__main__":
    success = verify_pipeline()
    sys.exit(0 if success else 1)
