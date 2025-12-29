import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score


def load_data() -> pd.DataFrame:
    # Public Titanic dataset (Kaggle mirror)
    url = "https://raw.githubusercontent.com/datasciencedojo/datasets/master/titanic.csv"
    df = pd.read_csv(url)
    return df


def build_pipeline() -> Pipeline:
    numeric_features = ["Age", "Fare", "SibSp", "Parch"]
    categorical_features = ["Sex", "Pclass", "Embarked"]

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
        ],
        remainder="passthrough",
    )

    model = LogisticRegression(max_iter=1000)

    pipe = Pipeline(
        steps=[
            ("prep", preprocessor),
            ("model", model),
        ]
    )
    return pipe


def train_and_eval(df: pd.DataFrame) -> float:
    df = df.dropna(subset=["Survived"])  # just in case
    y = df["Survived"].astype(int)

    X = df[["Age", "Fare", "SibSp", "Parch", "Sex", "Pclass", "Embarked"]].copy()
    # minimal cleanup
    X["Age"] = X["Age"].fillna(X["Age"].median())
    X["Embarked"] = X["Embarked"].fillna("Unknown")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipe = build_pipeline()
    pipe.fit(X_train, y_train)

    preds = pipe.predict(X_test)
    acc = accuracy_score(y_test, preds)
    return acc


def main():
    df = load_data()
    acc = train_and_eval(df)
    print(f"Accuracy: {acc:.3f}")


if __name__ == "__main__":
    main()
