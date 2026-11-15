# ADR 0003: Phase 3 decisions

Status: accepted for Phase 3, subject to review at the phase gate.

Each entry records a choice where the PRD left room, or where the phase authorisation changed the PRD. The PRD text itself is not edited.

## 1. Explanation documents sit beside new files
ADR 0001 mirrored documents under `docs/file-explanations/`. The Phase 3 authorisation asks for a sibling `.explanation.md`, so every file created from Phase 3 onward has one beside it. Phase 1 and 2 documents stay where they are, because moving 61 files adds no information and makes history harder to follow. `scripts/check_explanations.py` accepts either location, and reports a source documented in both.

Declarative configuration is now covered too, because the authorisation includes configuration files.

## 2. `model_score` replaces `fraud_probability`
PRD 6.2 and 9.1 use "probability" and `fraud_probability`. Phase 2 found that the scores are not calibrated: on validation, rows scoring 0.1 to 0.2 were fraud 31% of the time. The authorisation therefore requires `model_score`. The column, API field and documents all use that name, and every prediction response carries `score_is_calibrated: false`.

## 3. `FLAG_FOR_REVIEW` replaces a fraud verdict
The `prediction` column holds `FLAG_FOR_REVIEW` or `NOT_FLAGGED`. A flag is a request for a person to look. On test, 40.7% of flags were labelled fraud and 45.9% of labelled fraud was flagged.

## 4. Risk levels cannot change who is flagged
PRD 6.3 requires configurable boundaries. The authorisation forbids changing the threshold. The two fit together as follows:

| Level | Rule | Configurable |
|---|---|---|
| Low | `model_score` below the frozen threshold | No |
| Medium | At or above the frozen threshold, below the high boundary | Only the upper edge |
| High | At or above the high boundary | Yes |

So Low is exactly `NOT_FLAGGED`, and Medium and High are exactly `FLAG_FOR_REVIEW`.

The high boundary defaults to 0.30, the lowest PRD 5.5 candidate. On validation, 0.30 gives 88.5% precision and 24.2% recall (156 alerts). That figure comes from `threshold_analysis.json`, and no test data was used. Each prediction stores the boundary in force, so changing the setting never rewrites history.

## 5. `risk_score` is `model_score` on a 0 to 100 scale
PRD 6.2 and 9.1 require a risk score. It is `model_score * 100`, with no other transformation, because any more elaborate scale would suggest a meaning that has not been measured. It is not a percentage chance. A flagged transaction can show a risk score as low as 2.84, which is accurate: the frozen threshold is 0.02842.

## 6. Input validation is stricter than the feature code
- `amount` must be above 0 with at most 2 decimal places, so the stored value equals the scored value.
- `merchant` is valid only with `PAYMENT`, and `PAYMENT` only with `merchant`. PaySim has no other combination, so the model has no basis for a score on one (ADR 0001).
- Post-transaction balances are refused rather than ignored, so nobody can believe they influenced a score.

## 7. Uploaded labels are kept apart from predictions
PRD 6.4 allows `isFraud` to be retained for later evaluation and PRD 6.1 requires labels, predictions and investigation outcomes to stay separate. Labels go to their own table, `ground_truth_labels`. The scoring path builds its inputs from the four allowed columns only, and a test proves scores do not change when a label column is present. `isFlaggedFraud` is ignored and reported.

The application reports counts of supplied labels, but computes no performance metric from them. Performance figures come only from the frozen Phase 2 outputs.

## 8. One prediction per transaction
`predictions.transaction_id` is unique, and so is `investigations.prediction_id`. Explorer filters therefore have one unambiguous prediction per row. Scoring an existing transaction with a future model would need a migration and a rule for which prediction is current. That is left until a second model exists.

## 9. Two database roles
`POSTGRES_USER` is a superuser for administration only. The API and migrations use `APP_DB_USER`, which owns the application databases but is not a superuser. Tests use a separate database, and the test fixtures refuse any database whose name does not end in `_test`, because they delete rows.

## 10. Batch processing runs inside the API process
PRD 11.7 says not to assume background workers. Uploads are stored in a temporary file and processed in chunks by FastAPI background tasks. Each chunk commits on its own, which gives progress reporting and limits lost work. A restart interrupts a running job, and start-up marks such jobs as failed rather than leaving them looking active. They must be uploaded again. The limits default to 10 MB and 50,000 rows.

*Superseded in Phase 5 (M4) by a PostgreSQL job queue that resumes interrupted jobs: [ADR 0005](0005-phase-5-decisions.md), D1.*

## 11. Rate limits are per process
PRD section 10 says "where supported". Login, prediction and upload limits are held in memory, so they reset on restart and are not shared between workers. That is enough for one process and is documented as a limitation for anything larger.

*Superseded in Phase 5 (M3) by counters in PostgreSQL shared by every process: [ADR 0005](0005-phase-5-decisions.md), D2.*

## 12. Tokens are stateless, but checked against the database
Tokens are signed JWTs valid for 30 minutes. Every request also loads the user, so deactivating an account or changing a role takes effect at once. A changed password invalidates earlier tokens through a counter stored on the user.

## 13. The frozen model is pinned in code
`app/core/frozen_model.py` records the version, file hash and threshold. Start-up refuses to serve if the metadata disagrees, so editing both the model file and its metadata is not enough to change the served model. Installing a new model is a deliberate code change. The installed `scikit-learn` and `xgboost` versions must also match those recorded when the model was saved, because saved models are not guaranteed to behave the same across versions.
