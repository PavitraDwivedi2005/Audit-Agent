# services/storage_manager.py
# Double-persist manager for benchmark reports.
# Saves reports as markdown files locally and compresses reports for database archival.

import os
import gzip
from datetime import datetime
from database.models import Session, BenchmarkReport

class StorageManager:
    """
    Manages archival and persistence of benchmarking reports.
    Provides double-persist mechanisms: Local Markdown files and Gzipped database rows.
    """

    def __init__(self):
        # Resolve the base directory dynamically to work reliably
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.reports_dir = os.path.join(self.base_dir, "benchmark_reports")

    def sanitize_filename(self, text: str) -> str:
        """Replace spaces and invalid filesystem characters with underscores."""
        invalid_chars = '<>:"/\\|?* '
        sanitized = text
        for char in invalid_chars:
            sanitized = sanitized.replace(char, "_")
        return sanitized.strip("_")

    def save_report_locally(self, creator_username: str, model_used: str, report_text: str, timestamp: datetime = None) -> str:
        """
        Saves the markdown report text locally to a creator-specific directory.
        Returns the absolute path of the created file.
        """
        if not timestamp:
            timestamp = datetime.utcnow()
            
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        sanitized_creator = self.sanitize_filename(creator_username or "unknown_creator")
        sanitized_model = self.sanitize_filename(model_used)
        
        # Creator-specific directory
        creator_dir = os.path.join(self.reports_dir, sanitized_creator)
        os.makedirs(creator_dir, exist_ok=True)
        
        filename = f"{timestamp_str}_{sanitized_model}.md"
        filepath = os.path.join(creator_dir, filename)
        
        # Write report to disk
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report_text)
            
        return filepath

    def save_report_to_db(
        self,
        audit_run_id: int,
        employee_username: str | None,
        model_used: str,
        report_text: str,
        raw_model_response: str | None,
        latency: float,
        prompt_tokens: int,
        completion_tokens: int,
        timestamp: datetime = None
    ) -> bool:
        """
        Compresses the report text using gzip and inserts a BenchmarkReport row
        linked to the provided audit_run_id.
        """
        if not timestamp:
            timestamp = datetime.utcnow()
            
        try:
            # Compress report text using gzip
            compressed_bytes = gzip.compress(report_text.encode("utf-8"))
            
            with Session() as session:
                db_report = BenchmarkReport(
                    audit_run_id=audit_run_id,
                    employee_username=employee_username,
                    model_used=model_used,
                    timestamp=timestamp,
                    raw_report=report_text,
                    raw_model_response=raw_model_response,
                    compressed_report=compressed_bytes,
                    latency=latency,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens
                )
                session.add(db_report)
                session.commit()
            return True
        except Exception as e:
            # Log error internally or re-raise; we print to stderr for Streamlit/server logs
            print(f"[ERROR] Failed to save benchmark report to DB: {str(e)}")
            return False
