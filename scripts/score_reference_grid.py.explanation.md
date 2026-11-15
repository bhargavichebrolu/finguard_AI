# score_reference_grid.py

Source: [scripts/score_reference_grid.py](score_reference_grid.py)

## A. File Purpose
Scores a fixed grid of 550 synthetic inputs with the frozen model, computes their SHAP explanations, and prints one SHA-256 fingerprint of every output, with the library versions and the number flagged.

## B. Why This File Exists
Phase 6 rebuilt the API image to halve its size (no NVIDIA NCCL, no uv at run time). A smaller image is only acceptable if inference is unchanged. Running this inside the old and the new image gave the same fingerprint, which shows every score and explanation is identical to the last bit. It stays in the repository so any later image change can be checked the same way.

## C. Dependencies
- **Libraries:** pandas, the API's own packages.
- **Internal modules:** `app.services.model_service.load_verified_model` (all start-up checks, then the model), `app.ml.schema` for the valid types and destinations.
- **External services / database:** none; the database is never contacted, though a syntactically valid `DATABASE_URL` is required by the settings.
- **Depended on by:** `DEPLOYMENT.md` (image size), `test_deployment.py`.

## D. Every Function Explained

### `reference_grid`
Returns a DataFrame of every valid transaction type and destination pair (merchant only with PAYMENT, as the API requires), crossed with 11 amounts (`AMOUNTS`, from 0.01 to 50,000,000) and 10 steps (`STEPS`, from 1 to 1,000,000): 550 rows.

### `fingerprint`
Serialises the scores (as `repr` strings, so every bit counts) and explanations with sorted keys, and returns the text and its SHA-256.

### `main`
Loads the verified model, scores and explains the grid, prints a JSON summary, and with `--out` writes every output.

## E. Classes Explained
None.

## F. Execution Flow
Settings → `load_verified_model` (metadata, library versions, hashes, then the file) → score → explain → fingerprint → print.

## G. Input and Output
Input: the mounted frozen model files. Output: for example `{"rows": 550, "flagged": 123, "threshold": "0.02841914258897305", "xgboost": "3.2.0", "scikit-learn": "1.9.1", "sha256_of_all_outputs": "c188cdf2…"}`.

## H. Important Technical Concepts
- **Synthetic only:** no PaySim row, partition or test-set value is read; this measures nothing about model quality, only that the same inputs give the same outputs.
- **Bit-exact:** `repr` of each float keeps all 17 significant digits; any change in a library's arithmetic changes the hash.

## I. Example
The command in the module docstring, once per image; compare the two `sha256_of_all_outputs` values.

## J. Maintenance Notes
Do not change the grid: the recorded fingerprint `c188cdf28eb86ae06916776bd078cdb975b978af4ab9b0b80bb33ea55dc9b94f` is only comparable with the same inputs.

## K. Related Files
- [model_service.py](../backend/app/services/model_service.py.explanation.md): loading and explaining.
- [backend/Dockerfile](../backend/Dockerfile.explanation.md): the image it checks.
