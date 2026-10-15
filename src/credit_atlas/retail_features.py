"""Train-only retail encoder and private development feature preparation."""
from __future__ import annotations

import copy
import math
import re
import uuid
from pathlib import Path

import duckdb
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from .public_suite import verify_acquisition
from .retail import CATEGORICAL_FEATURES, NUMERIC_FEATURES, PROTOCOL, assign_partitions
from .workspace import contained, read_json, sha256, timestamp, write_new

CASE_ID = re.compile(r"retail-case-[0-9a-f]{12}\Z")
DEVELOPMENT_ROLES = ("train", "calibration", "validation")


def verify_case(root, case_id):
    if not isinstance(case_id, str) or not CASE_ID.fullmatch(case_id):
        raise ValueError("Valid retail case ID required")
    folder = contained(root, "artifacts/private/" + case_id)
    receipt = read_json(folder / "case-complete.json")
    if (receipt.get("schema_version") != 1 or receipt.get("case_id") != case_id
            or receipt.get("status") != "RETAIL_CANONICAL_BENCHMARK_PREPARED"
            or receipt.get("method_source_sha256") != sha256(Path(__file__).with_name("retail.py"))
            or receipt.get("target") != PROTOCOL["target"] or receipt.get("visibility") != "private"
            or any(receipt.get(key) is not False for key in ("model_training_performed", "model_qualified_for_production",
                "temporal_out_of_time", "final_test_predictors_materialized", "final_test_scored", "public_release_approved"))):
        raise ValueError("Retail case method or private benchmark contract changed")
    source, acquisition = verify_acquisition(root, receipt["suite_id"])
    by_id = {item["source_id"]: item for item in acquisition["sources"]}
    if (sha256(source / "acquisition-complete.json") != receipt["source_receipt_sha256"]
            or by_id["uci-retail"]["sha256"] != receipt["source_sha256"]
            or by_id["uci-retail-metadata"]["sha256"] != receipt["metadata_sha256"]):
        raise ValueError("Retail source lineage changed")
    expected = {"run-start.json", "clients.parquet", "six_month_history.parquet", "partitions.parquet",
                "protocol.json", "quality.json", "reconciliation.json"}
    if set(receipt["outputs_sha256"]) != expected:
        raise ValueError("Complete retail evidence digests required")
    for name, digest in receipt["outputs_sha256"].items():
        if sha256(contained(root, str((folder / name).relative_to(root)))) != digest:
            raise ValueError("Retail canonical evidence changed")
    quality, reconciliation = read_json(folder / "quality.json"), read_json(folder / "reconciliation.json")
    if (read_json(folder / "protocol.json") != PROTOCOL or quality["support"] != receipt["support"]
            or quality["clients"] != receipt["clients"] or receipt["clients"] != by_id["uci-retail"]["profile"]["rows"]
            or receipt["history_rows"] != 6 * receipt["clients"]
            or reconciliation["status"] != "PASS" or reconciliation["differing_rows"] != {"clients":0,"history":0}):
        raise ValueError("Retail population/protocol evidence does not reconcile")
    return folder, receipt, sha256(folder / "case-complete.json")


class RetailEncoder:
    """Explicit 13 numerical/6 categorical fields; no identifiers or demographic predictors."""
    def __init__(self):
        self.state = None

    def fit(self, rows):
        if self.state is not None or not rows or any(row.get("partition") != "train" for row in rows):
            raise ValueError("Fit a new encoder on nonempty training rows only")
        if any(type(row[name]) not in (int,float) or not math.isfinite(row[name])
               for row in rows for name in NUMERIC_FEATURES):
            raise ValueError("Finite numerical training values required")
        matrix = np.asarray([[row[name] for name in NUMERIC_FEATURES] for row in rows], dtype=np.float64)
        if not np.isfinite(matrix).all():
            raise ValueError("Nonfinite or missing retail numeric training value")
        means, scales = matrix.mean(axis=0), matrix.std(axis=0)
        scales[scales == 0] = 1
        categories = {name: ["__unseen__"] + sorted({self.category(row[name]) for row in rows})
                      for name in CATEGORICAL_FEATURES}
        self.state = {"schema_version":1,"fit_partition":"train","fit_rows":len(rows),
                      "numeric": {name: {"mean":float(mean),"scale":float(scale)}
                                  for name,mean,scale in zip(NUMERIC_FEATURES,means,scales,strict=True)},
                      "categorical": categories,
                      "feature_names": NUMERIC_FEATURES + [name + "=" + value for name in CATEGORICAL_FEATURES
                                                           for value in categories[name]]}
        return self

    @staticmethod
    def category(value):
        if type(value) is not int or not -2 <= value <= 9:
            raise ValueError("Reviewed source payment-status integer required")
        return str(value)

    def transform(self, rows):
        if self.state is None:
            raise ValueError("Encoder must be fitted first")
        if any(row.get("partition") not in DEVELOPMENT_ROLES for row in rows):
            raise ValueError("Development encoder excludes final-test rows")
        result = np.zeros((len(rows),len(self.state["feature_names"])),dtype=np.float64)
        for index,row in enumerate(rows):
            for column,name in enumerate(NUMERIC_FEATURES):
                value = row[name]
                if type(value) not in (int,float) or not math.isfinite(value):
                    raise ValueError("Nonfinite or missing retail numeric value")
                stats = self.state["numeric"][name]
                result[index,column]=(value-stats["mean"])/stats["scale"]
            offset = len(NUMERIC_FEATURES)
            for name in CATEGORICAL_FEATURES:
                values=self.state["categorical"][name]
                category=self.category(row[name])
                result[index,offset+values.index(category if category in values else "__unseen__")]=1
                offset+=len(values)
        if not np.isfinite(result).all():
            raise ValueError("Invalid encoded retail matrix")
        return result

    @classmethod
    def restore(cls,state):
        if (not isinstance(state,dict) or state.get("schema_version") != 1 or state.get("fit_partition") != "train"
                or type(state.get("fit_rows")) is not int or state["fit_rows"] <= 0
                or set(state["numeric"]) != set(NUMERIC_FEATURES)
                or set(state["categorical"]) != set(CATEGORICAL_FEATURES)):
            raise ValueError("Invalid retail encoder contract")
        for stats in state["numeric"].values():
            if (set(stats) != {"mean","scale"} or any(type(value) not in (int,float) or not math.isfinite(value)
                                                      for value in stats.values()) or stats["scale"] <= 0):
                raise ValueError("Invalid retail scaling state")
        for values in state["categorical"].values():
            if (not isinstance(values,list) or not 2 <= len(values) <= 13 or values[0] != "__unseen__"
                    or len(set(values)) != len(values) or any(value not in {str(i) for i in range(-2,10)} for value in values[1:])):
                raise ValueError("Invalid retail categorical vocabulary")
        names=NUMERIC_FEATURES+[name+"="+value for name in CATEGORICAL_FEATURES for value in state["categorical"][name]]
        if names != state["feature_names"]:
            raise ValueError("Retail encoded schema changed")
        encoder=cls()
        encoder.state=copy.deepcopy(state)
        return encoder


def prepare_features(root: Path,case_id: str):
    root=root.resolve()
    if root.drive.upper() != "D:":
        raise ValueError("Private D: workspace required")
    folder,case,digest=verify_case(root,case_id)
    output=contained(root,"artifacts/private/retail-features-"+uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    write_new(output/"access-start.json",{"started_at":timestamp(),"purpose":"retail_development_feature_preparation",
              "all_label_ids_read_for_split_verification":True,"final_test_predictors_materialized":False,
              "final_test_scored":False,"case_id":case_id,"case_receipt_sha256":digest})
    try:
        with duckdb.connect() as db:
            db.read_parquet(str(folder/"clients.parquet")).create_view("clients")
            db.read_parquet(str(folder/"partitions.parquet")).create_view("partitions")
            labels=db.sql("SELECT source_client_id,target FROM clients ORDER BY source_client_id").arrow().read_all().to_pylist()
            saved=db.sql("SELECT * FROM partitions ORDER BY source_client_id").arrow().read_all().to_pylist()
            if saved != assign_partitions(labels):
                raise ValueError("Saved retail split does not reproduce from source labels")
            columns=",".join('c."'+name+'"' for name in NUMERIC_FEATURES+CATEGORICAL_FEATURES)
            rows=db.sql("SELECT c.source_client_id,c.target,p.partition,"+columns+
                        " FROM clients c JOIN partitions p USING(source_client_id) "
                        "WHERE p.partition IN ('train','calibration','validation') ORDER BY p.partition,c.source_client_id").arrow().read_all().to_pylist()
        counts={role:sum(row["partition"]==role for row in rows) for role in DEVELOPMENT_ROLES}
        if counts != {role:sum(case["support"][role].values()) for role in DEVELOPMENT_ROLES}:
            raise ValueError("Retail development join lost or duplicated clients")
        train=[row for row in rows if row["partition"]=="train"]
        encoder=RetailEncoder().fit(train)
        write_new(output/"encoder.json",encoder.state)
        restored=RetailEncoder.restore(read_json(output/"encoder.json"))
        matrix=encoder.transform(rows)
        if not np.array_equal(matrix,restored.transform(rows)):
            raise ValueError("Saved retail encoder parity failed")
        # IDs and labels remain private; the matrix contains allowlisted fields only.
        payload=[{"source_client_id":row["source_client_id"],"partition":row["partition"],"target":row["target"],
                  "features":vector.tolist()} for row,vector in zip(rows,matrix,strict=True)]
        schema=pa.schema([("source_client_id",pa.int32()),("partition",pa.string()),("target",pa.int8()),
                          ("features",pa.list_(pa.float64(),matrix.shape[1]))])
        pq.write_table(pa.Table.from_pylist(payload,schema=schema),output/"development.parquet",compression="zstd")
        if not np.array_equal(matrix,np.asarray([row["features"] for row in pq.read_table(output/"development.parquet").to_pylist()])):
            raise ValueError("Persisted retail matrix parity failed")
        coverage=[{"partition":role,"field":name,"rows":counts[role],
                   "unseen":sum(encoder.category(row[name]) not in encoder.state["categorical"][name]
                                for row in rows if row["partition"]==role)}
                  for role in DEVELOPMENT_ROLES for name in CATEGORICAL_FEATURES]
        write_new(output/"coverage.json",{"rows_by_partition":counts,"feature_dimension":matrix.shape[1],
                  "unseen_category_counts":coverage,"encoder_fit_rows":len(train),"encoder_parity":"PASS_ALL_DEVELOPMENT_ROWS",
                  "matrix_parity":"PASS_ALL_DEVELOPMENT_ROWS","final_test_predictors_materialized":False})
        _,_,current=verify_case(root,case_id)
        if current != digest:
            raise ValueError("Retail case changed during feature preparation")
        write_new(output/"features-complete.json",{"schema_version":1,"status":"RETAIL_DEVELOPMENT_FEATURES_PREPARED",
                  "feature_id":output.name,"completed_at":timestamp(),"case_id":case_id,"case_receipt_sha256":digest,
                  "method_source_sha256":sha256(Path(__file__)),"rows_by_partition":counts,
                  "feature_dimension":matrix.shape[1],"model_training_performed":False,"final_test_scored":False,
                  "final_test_predictors_materialized":False,"visibility":"private","public_release_approved":False,
                  "outputs_sha256":{path.name:sha256(path) for path in output.iterdir() if path.is_file()}})
        return {"directory":str(output),"status":"RETAIL_DEVELOPMENT_FEATURES_PREPARED",
                "rows_by_partition":counts,"feature_dimension":matrix.shape[1],"model_training_performed":False}
    except Exception as error:
        write_new(output/"features-failed.json",{"status":"FAIL","failed_at":timestamp(),
                  "exception_type":type(error).__name__,"model_training_performed":False})
        raise
