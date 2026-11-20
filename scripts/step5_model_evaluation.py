
from pathlib import Path
import json
import joblib
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix,
    ConfusionMatrixDisplay
)

# --------------------------------------------------
# 1. PROJECT PATHS
# --------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_DIR / "data" / "processed"
MODEL_DIR = PROJECT_DIR / "models"
REPORT_DIR = DATA_DIR / "reports"

REPORT_DIR.mkdir(parents=True, exist_ok=True)

X_TEST_PATH = DATA_DIR / "X_test_scaled.csv"
Y_TEST_PATH = DATA_DIR / "y_test.csv"

LABEL_ENCODER_PATH = MODEL_DIR / "label_encoder.joblib"

MODEL_PATHS = {
    "Extra Trees": MODEL_DIR / "extra_trees_model.joblib",
    "Random Forest": MODEL_DIR / "random_forest_model.joblib",
    "XGBoost": MODEL_DIR / "xgboost_model.joblib",
    "SVM": MODEL_DIR / "svm_model.joblib"
}


# --------------------------------------------------
# 2. LOAD TEST DATA
# --------------------------------------------------

print("\nSTEP 5: MODEL EVALUATION")
print("=" * 60)

X_test = pd.read_csv(X_TEST_PATH)
y_test_df = pd.read_csv(Y_TEST_PATH)

if y_test_df.empty:
    raise ValueError("The test label file is empty.")

# Use the first column as the target labels.
y_test = y_test_df.iloc[:, 0]

print("Test features shape:", X_test.shape)
print("Test labels shape:", y_test.shape)

if len(X_test) != len(y_test):
    raise ValueError("Test features and labels have different row counts.")

if X_test.isnull().values.any():
    raise ValueError("Test features contain missing values.")

if not all(pd.api.types.is_numeric_dtype(dtype) for dtype in X_test.dtypes):
    raise ValueError("Test features must all be numeric.")


# --------------------------------------------------
# 3. LOAD LABEL ENCODER
# --------------------------------------------------

label_encoder = joblib.load(LABEL_ENCODER_PATH)

class_names = list(label_encoder.classes_)

print("\nClasses:", class_names)


# --------------------------------------------------
# 4. PREPARE PREDICTION LABELS
# --------------------------------------------------

def convert_predictions(predictions, model):
    """
    Convert encoded predictions back to original class names
    when the model was trained using LabelEncoder.
    """

    predictions = list(predictions)

    model_classes = getattr(model, "classes_", None)

    # XGBoost was trained using encoded integer labels.
    if model_classes is not None:
        try:
            numeric_classes = [int(value) for value in model_classes]

            if set(numeric_classes).issubset(
                set(range(len(class_names)))
            ):
                return label_encoder.inverse_transform(
                    [int(value) for value in predictions]
                )
        except (ValueError, TypeError):
            pass

    return predictions


# --------------------------------------------------
# 5. EVALUATE EACH MODEL
# --------------------------------------------------

results = []

for model_name, model_path in MODEL_PATHS.items():

    print("\n" + "=" * 60)
    print("Evaluating:", model_name)
    print("=" * 60)

    if not model_path.exists():
        print("Model file not found:", model_path)
        continue

    model = joblib.load(model_path)

    predictions = model.predict(X_test)
    predictions = convert_predictions(predictions, model)

    accuracy = accuracy_score(y_test, predictions)

    precision = precision_score(
        y_test,
        predictions,
        average="macro",
        zero_division=0
    )

    recall = recall_score(
        y_test,
        predictions,
        average="macro",
        zero_division=0
    )

    f1 = f1_score(
        y_test,
        predictions,
        average="macro",
        zero_division=0
    )

    print(f"Accuracy:  {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1-score:  {f1:.4f}")

    # Classification report
    report = classification_report(
        y_test,
        predictions,
        labels=class_names,
        target_names=class_names,
        output_dict=True,
        zero_division=0
    )

    report_path = REPORT_DIR / (
        model_name.lower().replace(" ", "_")
        + "_evaluation_report.json"
    )

    with open(report_path, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)

    # Confusion matrix
    cm = confusion_matrix(
        y_test,
        predictions,
        labels=class_names
    )

    cm_df = pd.DataFrame(
        cm,
        index=class_names,
        columns=class_names
    )

    cm_csv_path = REPORT_DIR / (
        model_name.lower().replace(" ", "_")
        + "_evaluation_confusion_matrix.csv"
    )

    cm_df.to_csv(cm_csv_path)

    # Confusion matrix image
    display = ConfusionMatrixDisplay(
        confusion_matrix=cm,
        display_labels=class_names
    )

    fig, ax = plt.subplots(figsize=(7, 6))

    display.plot(
        ax=ax,
        cmap="Blues",
        values_format="d",
        colorbar=False
    )

    ax.set_title(f"{model_name} - Confusion Matrix")
    plt.xticks(rotation=20)
    plt.tight_layout()

    image_path = REPORT_DIR / (
        model_name.lower().replace(" ", "_")
        + "_confusion_matrix.png"
    )

    plt.savefig(image_path, dpi=300)
    plt.close(fig)

    results.append({
        "Model": model_name,
        "Accuracy": accuracy,
        "Precision": precision,
        "Recall": recall,
        "Macro F1-score": f1
    })

    print("Classification report saved:", report_path.name)
    print("Confusion matrix saved:", image_path.name)


# --------------------------------------------------
# 6. COMPARE MODELS
# --------------------------------------------------

if not results:
    raise RuntimeError("No models were evaluated.")

results_df = pd.DataFrame(results)

results_df = results_df.sort_values(
    by="Macro F1-score",
    ascending=False
)

comparison_path = REPORT_DIR / "step5_model_evaluation_comparison.csv"

results_df.to_csv(comparison_path, index=False)

print("\nMODEL COMPARISON")
print("=" * 60)
print(results_df.to_string(index=False))


# --------------------------------------------------
# 7. IDENTIFY BEST MODEL
# --------------------------------------------------

best_model = results_df.iloc[0]

print("\nBEST MODEL")
print("=" * 60)
print("Model:", best_model["Model"])
print(f"Accuracy: {best_model['Accuracy']:.4f}")
print(f"Macro F1-score: {best_model['Macro F1-score']:.4f}")


# --------------------------------------------------
# 8. SAVE MODEL COMPARISON CHART
# --------------------------------------------------

fig, ax = plt.subplots(figsize=(9, 5))

results_df.set_index("Model")[
    ["Accuracy", "Precision", "Recall", "Macro F1-score"]
].plot(kind="bar", ax=ax)

ax.set_title("PhysioFlex 3.0 - Model Performance Comparison")
ax.set_ylabel("Score")
ax.set_ylim(0, 1)
ax.set_xlabel("Machine Learning Models")
ax.legend(loc="lower right")
plt.xticks(rotation=0)
plt.tight_layout()

chart_path = REPORT_DIR / "step5_model_comparison.png"

plt.savefig(chart_path, dpi=300)
plt.close(fig)


# --------------------------------------------------
# 9. FINAL OUTPUT
# --------------------------------------------------

print("\n" + "=" * 60)
print("STEP 5 COMPLETED SUCCESSFULLY")
print("=" * 60)

print("\nGenerated files:")
print("- step5_model_evaluation_comparison.csv")
print("- step5_model_comparison.png")
print("- Individual model evaluation reports")
print("- Individual confusion matrix CSV files")
print("- Individual confusion matrix PNG images")

print("\nReport folder:")
print(REPORT_DIR)

print("\nREADY FOR STEP 6")
