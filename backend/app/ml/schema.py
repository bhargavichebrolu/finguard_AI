"""Single source of truth for raw PaySim columns, model inputs and the feature schema.

Bump FEATURE_SCHEMA_VERSION whenever FEATURE_DICTIONARY changes: saved models record the
version they were trained with, and the API refuses to pair a model with a different schema.
"""

from dataclasses import asdict, dataclass

FEATURE_SCHEMA_VERSION = "1.0.0"

RAW_COLUMNS: tuple[str, ...] = (
    "step",
    "type",
    "amount",
    "nameOrig",
    "oldbalanceOrg",
    "newbalanceOrig",
    "nameDest",
    "oldbalanceDest",
    "newbalanceDest",
    "isFraud",
    "isFlaggedFraud",
)

TARGET_COLUMN = "isFraud"
RULE_FLAG_COLUMN = "isFlaggedFraud"
LEAKY_BALANCE_COLUMNS: tuple[str, ...] = (
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest",
)
ACCOUNT_IDENTIFIER_COLUMNS: tuple[str, ...] = ("nameOrig", "nameDest")

# Raw columns the data pipeline is allowed to read. Balances are absent on purpose, so they
# cannot reach a processed file through a coding mistake.
PIPELINE_RAW_COLUMNS: tuple[str, ...] = (
    "step",
    "type",
    "amount",
    "nameDest",
    TARGET_COLUMN,
    RULE_FLAG_COLUMN,
)

TRANSACTION_TYPES: tuple[str, ...] = ("CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER")
DESTINATION_PREFIX_TO_CATEGORY: dict[str, str] = {"C": "customer", "M": "merchant"}
DESTINATION_CATEGORIES: tuple[str, ...] = ("customer", "merchant")

# The four values a caller supplies for one prediction (PRD section 6.2).
PREDICTION_INPUT_COLUMNS: tuple[str, ...] = (
    "amount",
    "transaction_type",
    "step",
    "destination_category",
)

# Non-feature columns stored next to the features in processed partitions.
PROCESSED_LABEL_COLUMN = "is_fraud"
PROCESSED_RULE_FLAG_COLUMN = "is_flagged_fraud"
PROCESSED_STEP_COLUMN = "step"
PROCESSED_ROW_COLUMN = "source_row"

# The simulator caps fraud amounts here. Never a feature; used only to report how much a result
# depends on this artefact of the simulation.
SIMULATOR_AMOUNT_CAP = 10_000_000.0


@dataclass(frozen=True)
class FeatureSpec:
    """One row of the feature dictionary required by PRD section 4.4."""

    name: str
    source_columns: tuple[str, ...]
    transformation: str
    data_type: str
    kind: str  # "numeric" or "categorical"
    business_meaning: str
    rationale: str
    available_before_completion: bool


@dataclass(frozen=True)
class RejectedFeature:
    """A candidate feature that was considered and deliberately left out."""

    name: str
    reason: str


FEATURE_DICTIONARY: tuple[FeatureSpec, ...] = (
    FeatureSpec(
        name="amount",
        source_columns=("amount",),
        transformation="Unchanged",
        data_type="float64",
        kind="numeric",
        business_meaning="Value of the transaction in the simulation's currency units.",
        rationale="Known when the transaction is requested; tree models split on it directly.",
        available_before_completion=True,
    ),
    FeatureSpec(
        name="amount_log1p",
        source_columns=("amount",),
        transformation="natural log of (1 + amount)",
        data_type="float64",
        kind="numeric",
        business_meaning="Order of magnitude of the transaction value.",
        rationale="Amounts are heavily right-skewed; linear models need a compressed scale.",
        available_before_completion=True,
    ),
    FeatureSpec(
        name="transaction_type",
        source_columns=("type",),
        transformation="Categorical restricted to the five PaySim types",
        data_type="category",
        kind="categorical",
        business_meaning="Kind of movement: cash in, cash out, debit, payment or transfer.",
        rationale="Known at request time. Labelled fraud occurs only in TRANSFER and CASH_OUT.",
        available_before_completion=True,
    ),
    FeatureSpec(
        name="destination_category",
        source_columns=("nameDest",),
        transformation="First letter of nameDest: C maps to customer, M maps to merchant",
        data_type="category",
        kind="categorical",
        business_meaning="Whether money goes to a customer account or a merchant.",
        rationale=(
            "Required by PRD 4.4. The category is used instead of the identifier. In PaySim it is "
            "fully determined by type (merchant if and only if PAYMENT), so it adds no signal here."
        ),
        available_before_completion=True,
    ),
    FeatureSpec(
        name="hour_of_day",
        source_columns=("step",),
        transformation="step modulo 24",
        data_type="int64",
        kind="numeric",
        business_meaning="Simulated hour of the day, assuming one step is one hour.",
        rationale="Legitimate activity follows a daily cycle, so the hour carries signal.",
        available_before_completion=True,
    ),
    FeatureSpec(
        name="hour_sin",
        source_columns=("step",),
        transformation="sin(2 * pi * hour_of_day / 24)",
        data_type="float64",
        kind="numeric",
        business_meaning="Position on the 24-hour clock, sine component.",
        rationale="Keeps 23:00 next to 00:00 for linear and distance-based methods such as SMOTE.",
        available_before_completion=True,
    ),
    FeatureSpec(
        name="hour_cos",
        source_columns=("step",),
        transformation="cos(2 * pi * hour_of_day / 24)",
        data_type="float64",
        kind="numeric",
        business_meaning="Position on the 24-hour clock, cosine component.",
        rationale="Pairs with hour_sin; both are needed to locate a point on the circle.",
        available_before_completion=True,
    ),
)

REJECTED_FEATURES: tuple[RejectedFeature, ...] = (
    RejectedFeature(
        "oldbalanceOrg, newbalanceOrig, oldbalanceDest, newbalanceDest",
        "Affected by the simulator's fraud cancellation behaviour, and the post-transaction "
        "values do not exist at assessment time (PRD 4.3).",
    ),
    RejectedFeature(
        "isFlaggedFraud",
        "Output of an existing rule, kept only as a separate baseline (PRD 4.3).",
    ),
    RejectedFeature(
        "step, day_index",
        "Grow without bound, so later partitions fall outside the range seen in training, and a "
        "tree could memorise when fraud occurred instead of learning a pattern.",
    ),
    RejectedFeature(
        "nameOrig, nameDest as numbers",
        "Identifiers have no numeric meaning (PRD 4.3).",
    ),
    RejectedFeature(
        "destination or origin transaction counts",
        "Would need account identifiers and an online history store, which the prediction input "
        "in PRD 6.2 does not provide. Training on them would create training/serving skew.",
    ),
    RejectedFeature(
        "is_amount_exactly_10m, is_round_amount",
        "Available at request time, but they encode the simulator's fraud amount cap rather than "
        "behaviour that would carry over to other data.",
    ),
)

FEATURE_COLUMNS: tuple[str, ...] = tuple(spec.name for spec in FEATURE_DICTIONARY)
NUMERIC_FEATURES: tuple[str, ...] = tuple(
    spec.name for spec in FEATURE_DICTIONARY if spec.kind == "numeric"
)
CATEGORICAL_FEATURES: tuple[str, ...] = tuple(
    spec.name for spec in FEATURE_DICTIONARY if spec.kind == "categorical"
)

# Nothing in this set may ever appear in FEATURE_COLUMNS.
FORBIDDEN_FEATURE_COLUMNS: frozenset[str] = frozenset(
    {
        TARGET_COLUMN,
        RULE_FLAG_COLUMN,
        *LEAKY_BALANCE_COLUMNS,
        *ACCOUNT_IDENTIFIER_COLUMNS,
        PROCESSED_LABEL_COLUMN,
        PROCESSED_RULE_FLAG_COLUMN,
        PROCESSED_STEP_COLUMN,
        PROCESSED_ROW_COLUMN,
    }
)


def feature_dictionary_records() -> dict:
    """Return the feature dictionary and rejected candidates as JSON-ready data."""
    return {
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "features": [asdict(spec) for spec in FEATURE_DICTIONARY],
        "rejected_features": [asdict(rejected) for rejected in REJECTED_FEATURES],
    }
