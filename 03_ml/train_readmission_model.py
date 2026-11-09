# Databricks notebook source
# 30-day readmission risk model: train on pc_gold_discharge_features, track + register in
# MLflow / Unity Catalog, then score each patient's latest discharge into pc_gold_readmission_risk.
# Runs on serverless compute.

# COMMAND ----------

# MAGIC %pip install -q mlflow==3.4.0 scikit-learn==1.5.2

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import mlflow
import pandas as pd
from mlflow.models import infer_signature
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

FQ = "users.narasimha_kamathardi"
MODEL_NAME = f"{FQ}.pc_readmission_risk_model"
NUM = ["age", "chronic_conditions", "length_of_stay", "prior_admissions_12m"]
CAT = ["discharge_disposition", "primary_condition", "payer", "sex"]
BOOL = ["followup_scheduled"]

mlflow.set_registry_uri("databricks-uc")
mlflow.set_experiment("/Users/narasimha.kamathardi@databricks.com/pinecrest-readmission-risk")

df = spark.table(f"{FQ}.pc_gold_discharge_features").toPandas()
df["followup_scheduled"] = df["followup_scheduled"].astype(int)
X, y = df[NUM + CAT + BOOL], df["readmitted_30d"].astype(int)
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
print(f"training rows={len(X_tr)} test rows={len(X_te)} positive rate={y.mean():.3f}")

model = Pipeline([
    ("prep", ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"), CAT)],
                               remainder="passthrough")),
    ("clf", GradientBoostingClassifier(n_estimators=200, max_depth=3, learning_rate=0.05, random_state=42)),
])

with mlflow.start_run(run_name="gbm-readmission-30d") as run:
    model.fit(X_tr, y_tr)
    p = model.predict_proba(X_te)[:, 1]
    auc, ap = roc_auc_score(y_te, p), average_precision_score(y_te, p)
    # lift: readmission rate among the top-decile of predicted risk vs overall
    top = pd.Series(p).rank(pct=True).values >= 0.9
    lift = y_te.values[top].mean() / y_te.mean()
    mlflow.log_params({"n_estimators": 200, "max_depth": 3, "learning_rate": 0.05})
    mlflow.log_metrics({"test_auc": auc, "test_avg_precision": ap, "top_decile_lift": lift})
    mlflow.sklearn.log_model(model, "model", signature=infer_signature(X_te, p),
                             registered_model_name=MODEL_NAME)
    print(f"mlflow run_id={run.info.run_id}")
    print(f"test AUC={auc:.3f}  avg precision={ap:.3f}  top-decile lift={lift:.2f}x")

version = max(int(v.version) for v in mlflow.MlflowClient().search_model_versions(f"name='{MODEL_NAME}'"))
mlflow.MlflowClient().set_registered_model_alias(MODEL_NAME, "champion", version)
print(f"registered {MODEL_NAME} version {version} alias=champion")

# ---- batch score: latest discharge per patient -> risk worklist -------------------------
champion = mlflow.sklearn.load_model(f"models:/{MODEL_NAME}@champion")
latest = spark.sql(f"""
    SELECT * FROM {FQ}.pc_gold_discharge_features
    QUALIFY row_number() OVER (PARTITION BY patient_id ORDER BY discharge_date DESC) = 1""").toPandas()
latest["followup_scheduled"] = latest["followup_scheduled"].astype(int)
latest["risk_score"] = champion.predict_proba(latest[NUM + CAT + BOOL])[:, 1].round(4)
latest["risk_tier"] = pd.cut(latest["risk_score"], [0, 0.15, 0.30, 1.0], labels=["Low", "Medium", "High"],
                             include_lowest=True).astype(str)
latest["recommended_action"] = latest.apply(
    lambda r: "Schedule follow-up visit within 7 days" if not r.followup_scheduled and r.risk_tier == "High"
    else "Pharmacist medication reconciliation call" if r.risk_tier == "High"
    else "Nurse check-in call within 72 hours" if r.risk_tier == "Medium" else "Standard discharge packet",
    axis=1)
latest["model_version"] = str(version)

out = latest[["patient_id", "encounter_id", "facility", "primary_condition", "discharge_date",
              "discharge_disposition", "followup_scheduled", "age", "payer", "chronic_conditions",
              "risk_score", "risk_tier", "recommended_action", "model_version"]]
out["followup_scheduled"] = out["followup_scheduled"].astype(bool)
(spark.createDataFrame(out).write.mode("overwrite").option("overwriteSchema", "true")
 .saveAsTable(f"{FQ}.pc_gold_readmission_risk"))
spark.sql(f"ALTER TABLE {FQ}.pc_gold_readmission_risk SET TBLPROPERTIES (delta.enableChangeDataFeed = true)")

print(f"scored {len(out)} patients -> {FQ}.pc_gold_readmission_risk")
print(out["risk_tier"].value_counts().to_string())
print(out.sort_values("risk_score", ascending=False).head(5).to_string(index=False))
