"""The model and threshold frozen at the end of Phase 2.

These values are written in code, not read from settings, so neither an environment variable nor
an edited metadata file can change which model is served or who gets flagged. Start-up compares
them with the metadata and the file on disk, and refuses to serve if anything differs.
"""

FROZEN_MODEL_VERSION = "fraud_detector_v1"
FROZEN_MODEL_SHA256 = "69813c176b02d035f550e80f0f694f44bb9fec8a31222a25de189525a91ad40c"
FROZEN_THRESHOLD = 0.02841914258897305
VERIFIED_LIBRARIES = ("scikit-learn", "xgboost")
# Built by scripts/export_model_report.py from saved Phase 2 outputs only. Rebuilding it from the
# same sources gives the same bytes, so a different hash means the report or a source changed.
# Phase 5 M1 rebuilt it with line-ending-independent source hashes; every reported value is
# unchanged, so only this pin and the report's source_files section changed.
MODEL_REPORT_SHA256 = "9d1794bbeeb5f6cc4f518a1175ef3adddaf29e2ad1e47a4b9c88ff4cf02e3109"

SCORE_TYPE = "uncalibrated_model_score"
SCORE_IS_CALIBRATED = False
SCORE_NOTE = (
    "model_score ranks transactions for review. It is not a calibrated probability of fraud, and "
    "a flag is a request for human review, not a finding of fraud."
)
