# preprocessing.py

Source: [backend/app/ml/preprocessing.py](../../../../../backend/app/ml/preprocessing.py)

## A. File Purpose
Turns the feature table from `engineer_features` into the numeric matrix that all six model families receive.

## B. Why This File Exists
PRD 5.3 requires identical evaluation conditions for comparable models, so every family gets the same encoding. It sits apart from the training code because a saved model refers to `to_float32`, and the API must be able to load the model without installing training-only libraries.

## C. Dependencies
- **Libraries:** `numpy`, `pandas`, `scikit-learn`.
- **Internal modules:** `app.ml.schema`.
- **External services / database:** none.
- **Depended on by:** `candidates.py`, `imbalance.py`, `experiment_stages.py`, `final_evaluation.py`, and every saved model file.

## D. Every Function Explained

### `to_float32`
- **Purpose:** cast the matrix to single precision as the last preprocessing step.
- **Parameters / types:** `matrix: np.ndarray`.
- **Returns / type:** `np.ndarray` of `float32`, without a copy when it already is.
- **Internal processing:** `np.asarray` with a dtype.
- **Error handling:** none needed.
- **Calls:** numpy.
- **Used by:** the `FunctionTransformer` in `build_preprocessor`. It must stay importable under this name, or saved models will not load.

### `compact_features`
- **Purpose:** reduce training memory.
- **Parameters / types:** `features: pd.DataFrame`.
- **Returns / type:** `pd.DataFrame` with float32 numeric columns.
- **Internal processing:** a shallow copy, with numeric columns replaced.
- **Error handling:** `KeyError` if a numeric column is absent.
- **Calls:** pandas `astype`.
- **Used by:** `experiment_stages.load_development_data`, `imbalance.oversample_training_fold`.

### `build_preprocessor`
- **Purpose:** build the sklearn step that encodes categories and handles numeric columns.
- **Parameters / types:** `scale_numeric: bool`, used by Logistic Regression; `dropped_features: tuple[str, ...]`, used by feature-removal sensitivity runs.
- **Returns / type:** unfitted `sklearn.pipeline.Pipeline`.
- **Internal processing:** a `ColumnTransformer` with a fixed-category one-hot encoder, an optional scaler or passthrough, then the float32 cast.
- **Error handling:** `ValueError` for an unknown name in `dropped_features`. At use, an unseen category raises from the encoder.
- **Calls:** sklearn constructors.
- **Used by:** `candidates.build_pipeline`.

## E. Classes Explained
None.

## F. Execution Flow
Frame in, one-hot and numeric columns stacked, cast to float32, matrix out. Output column order is one-hot columns followed by numeric columns.

## G. Input and Output
Input: the seven-column frame from `engineer_features`. Output: a 12-column float32 matrix (5 type columns, 2 destination columns and 5 numeric columns), fewer if features are dropped.

## H. Important Technical Concepts
**Why float32:** 4.4 million rows by 12 columns take about 210 MB in float32 and 425 MB in float64, and the development machine has little free memory. Tree libraries work in single precision anyway. The cast is part of the pipeline, so a served value is rounded exactly as a training value was. This is not a material loss: an amount near 10,000,000 keeps a precision of about 1 unit.

**Why fixed categories:** learned categories would make a rare type's encoding depend on which rows were in a fold. A fixed list also makes an unseen value fail loudly.

**No fitting on later data:** the scaler is fitted inside the pipeline's `fit`, which only ever sees training rows.

## I. Example
```python
matrix = build_preprocessor(scale_numeric=True).fit_transform(features)
```

## J. Maintenance Notes
Renaming `to_float32` or moving this file breaks loading of existing model files. Treat either as a model-version change.

## K. Related Files
- [candidates.py](candidates.py.explanation.md): attaches this to each estimator.
- [features.py](features.py.explanation.md): produces the input.
- [schema.py](schema.py.explanation.md): column lists.
