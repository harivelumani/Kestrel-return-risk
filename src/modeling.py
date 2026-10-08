"""Shared preprocessing and the two candidate estimators."""

from __future__ import annotations

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.config import RANDOM_SEED
from src.features import CATEGORICAL_FEATURES, feature_columns


def make_pipeline(include_history: bool, model_name: str) -> Pipeline:
    columns = feature_columns(include_history)
    numeric = [column for column in columns if column not in CATEGORICAL_FEATURES]
    categorical = [column for column in columns if column in CATEGORICAL_FEATURES]
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "num",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric,
            ),
            (
                "cat",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        (
                            "onehot",
                            OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                        ),
                    ]
                ),
                categorical,
            ),
        ]
    )
    if model_name == "logistic":
        estimator = LogisticRegression(
            C=1.0,
            solver="lbfgs",
            max_iter=2000,
            random_state=RANDOM_SEED,
        )
    elif model_name == "hist_gradient_boosting":
        estimator = HistGradientBoostingClassifier(
            max_iter=200,
            learning_rate=0.08,
            max_depth=4,
            min_samples_leaf=30,
            l2_regularization=0.1,
            early_stopping=False,
            random_state=RANDOM_SEED,
        )
    else:
        raise ValueError(f"Unknown model {model_name}")
    return Pipeline([("preprocess", preprocessor), ("model", estimator)])


def positive_scores(pipeline: Pipeline, matrix) -> np.ndarray:
    probabilities = pipeline.predict_proba(matrix)
    classes = list(pipeline.named_steps["model"].classes_)
    return np.asarray(probabilities[:, classes.index(1)], dtype=float)
