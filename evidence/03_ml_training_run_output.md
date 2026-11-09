# ML training + batch scoring run

Job run `780747672492204` (task run `987298765650366`) · result **SUCCESS** · notebook `/Workspace/Users/narasimha.kamathardi@databricks.com/pinecrest-readmission-journey/03_ml/train_readmission_model`

### cell
```python
# 30-day readmission risk model: train on pc_gold_discharge_features, track + register in
# MLflow / Unity Catalog, then score each patient's latest discharge into pc_gold_readmission_risk.
# Runs on serverless compute.
```
**output:**
```

```

### cell
```python
%pip install -q mlflow==3.4.0 scikit-learn==1.5.2
```
**output:**
```
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed. This behaviour is the source of the following dependency conflicts.
jupyter-server 1.23.4 requires anyio=3.1.0, but you have anyio 4.16.0 which is incompatible.
googleapis-common-protos 1.62.0 requires protobuf!=3.20.0,!=3.20.1,!=4.21.1,!=4.21.2,!=4.21.3,!=4.21.4,!=4.21.5,=3.19.5, but you have protobuf 6.33.6 which is incompatible.
virtualenv 20.16.7 requires platformdirs=2.4, but you have platformdirs 4.12.4 which is incompatible.
Note: you may need to restart the kernel using %restart_python or dbutils.library.restartPython() to use updated packages.
```

### cell
```python
dbutils.library.restartPython()
```
**output:**
```

```

### cell
```python
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
```
**output:**
```
2026/11/09 22:18:55 INFO mlflow.tracking.fluent: Experiment with name '/Users/narasimha.kamathardi@databricks.com/pinecrest-readmission-risk' does not exist. Creating a new experiment.

training rows=4509 test rows=1504 positive rate=0.147

/local_disk0/.ephemeral_nfs/envs/pythonEnv-1e14cd0c-02b4-4dd9-94ec-c75a789c11ad/lib/python3.10/site-packages/mlflow/types/utils.py:452: UserWarning: Hint: Inferred schema contains integer column(s). Integer columns in Python cannot represent missing values. If your input data contains missing values at inference time, it will be encoded as floats and will cause a schema enforcement error. The best way to avoid this problem is to infer the model schema based on a realistic data sample (training dataset) that includes missing values. Alternatively, you can declare integer columns as doubles (float64) whenever these columns may have missing values. See `Handling Integers With Missing Values `_ for more details.
  warnings.warn(
2026/11/09 22:19:24 WARNING mlflow.models.model: `artifact_path` is deprecated. Please use `name` instead.
🔗 View Logged Model at: https://adb-984752964297111.11.azuredatabricks.net/ml/experiments/1596196291870492/models/m-94d7d22752de4f4db228818b2848cee2?o=984752964297111
Successfully registered model 'users.narasimha_kamathardi.pc_readmission_risk_model'.
🔗 Created version '1' of model 'users.narasimha_kamathardi.pc_readmission_risk_model': https://adb-984752964297111.11.azuredatabricks.net/explore/data/models/users/narasimha_kamathardi/pc_readmission_risk_model/version/1?o=984752964297111

mlflow run_id=e2b9043da7b54204b0cfbb17d7667ed5
test AUC=0.779  avg precision=0.434  top-decile lift=3.34x
registered users.narasimha_kamathardi.pc_readmission_risk_model version 1 alias=champion

/home/spark-1e14cd0c-02b4-4dd9-94ec-c7/.ipykernel/27928/command-5164970941860275-2220454848:69: SettingWithCopyWarning: 
A value is trying to be set on a copy of a slice from a DataFrame.
Try using .loc[row_indexer,col_indexer] = value instead

See the caveats in the documentation: https://pandas.pydata.org/pandas-docs/stable/user_guide/indexing.html#returning-a-view-versus-a-copy
  out["followup_scheduled"] = out["followup_scheduled"].astype(bool)

scored 2000 patients -> users.narasimha_kamathardi.pc_gold_readmission_risk
Low       1372
Medium     375
High       253
patient_id encounter_id         facility primary_condition discharge_date discharge_disposition  followup_scheduled  age      payer  chronic_conditions  risk_score risk_tier                     recommended_action model_version
  PC-01684    EN-005050   Pinecrest Main               CHF     2026-09-07       Skilled nursing               False   80 Commercial                   0      0.9119      High Schedule follow-up visit within 7 days             1
  PC-00609    EN-001830  Pinecrest North            Sepsis     2026-07-14       Skilled nursing               False   92   Medicare                   8      0.8885      High Schedule follow-up visit within 7 days             1
  PC-00662    EN-001981   Pinecrest Main               AMI     2026-08-07       Skilled nursing               False   76   Self-pay                   6      0.8773      High Schedule follow-up visit within 7 days             1
  PC-00549    EN-001653 Pinecrest Valley              COPD     2026-03-20       Skilled nursing               False   61   Medicare                   5      0.8764      High Schedule follow-up visit within 7 days             1
  PC-01287    EN-003841 Pinecrest Valley          Diabetes     2026-09-11              Left AMA               False   88   Medicare                   6      0.8728      High Schedule follow-up visit within 7 days             1
```
