"""The model and threshold frozen at the end of Phase 2.

These values are written in code, not read from settings, so neither an environment variable nor
an edited metadata file can change which model is served or who gets flagged. Start-up compares
them with the metadata and the file on disk, and refuses to serve if anything differs.
"""

FROZEN_MODEL_VERSION = "fraud_detector_v1"
FROZEN_MODEL_SHA256 = "69813c176b02d035f550e80f0f694f44bb9fec8a31222a25de189525a91ad40c"
FROZEN_THRESHOLD = 0.02841914258897305
VERIFIED_LIBRARIES = ("scikit-learn", "xgboost")

SCORE_TYPE = "uncalibrated_model_score"
SCORE_IS_CALIBRATED = False
SCORE_NOTE = (
    "model_score ranks transactions for review. It is not a calibrated probability of fraud, and "
    "a flag is a request for human review, not a finding of fraud."
)
