"""
Convenience script: creates the DB tables, ensures the sample CSV exists,
and prints next steps. Actual upload happens through the API (so it also
exercises the validation pipeline exactly as a real user would).

Usage:
    python scripts/seed_sample_data.py
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.init_db import init_db  # noqa: E402

SAMPLE_CSV = Path(__file__).resolve().parent.parent / "data" / "sample" / "sample_sales.csv"

if __name__ == "__main__":
    init_db()
    if not SAMPLE_CSV.exists():
        print("Sample CSV not found, generating it now...")
        subprocess.run([sys.executable, str(Path(__file__).parent / "generate_sample_csv.py")], check=True)

    print(
        "\nDatabase is ready. Next steps:\n"
        "  1. Start the API:      uvicorn app.main:app --reload\n"
        "  2. Log in as admin:    POST /api/v1/auth/login "
        "(email: admin@salesbi.local, password: Admin@123)\n"
        f"  3. Upload the sample CSV via POST /api/v1/datasets/upload -> {SAMPLE_CSV}\n"
        "  4. Train models:       POST /api/v1/forecast/train\n"
        "  5. Get predictions:    POST /api/v1/forecast/predict\n"
        "  6. Open the dashboard: streamlit run dashboard/app.py\n"
    )
