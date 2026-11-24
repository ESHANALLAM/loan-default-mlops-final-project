"""Data drift report: training data (reference) vs new/production data (current)."""
import os, sys
import pandas as pd
from src.features import RAW

cur_path = sys.argv[1] if len(sys.argv) > 1 else "data/loan_new.csv"
ref = pd.read_csv("data/loan.csv")[RAW]
cur = pd.read_csv(cur_path)[RAW]
os.makedirs("reports", exist_ok=True)
out = "reports/drift_report.html"

try:
    from evidently.report import Report
    from evidently.metric_preset import DataDriftPreset
    rep = Report(metrics=[DataDriftPreset()])
    rep.run(reference_data=ref, current_data=cur)
    rep.save_html(out)
    res = rep.as_dict()["metrics"][0]["result"]
    share, n = res["share_of_drifted_columns"], res["number_of_drifted_columns"]
    print(f"Drifted columns: {n} of {len(RAW)} ({share:.0%})")
    print("DRIFT DETECTED -> retrain model" if share >= 0.3 else "No significant drift")
except ImportError:
    try:
        from evidently import Report
        from evidently.presets import DataDriftPreset
        Report([DataDriftPreset()]).run(cur, ref).save_html(out)
    except ImportError:
        scores = {}
        for column in RAW:
            if not pd.api.types.is_numeric_dtype(ref[column]):
                continue
            reference_std = float(ref[column].std())
            score = abs(float(cur[column].mean()) - float(ref[column].mean()))
            scores[column] = score / reference_std if reference_std else 0.0
        drifted = [column for column, score in scores.items() if score >= 0.30]
        share = len(drifted) / len(RAW)
        rows = "".join(
            f"<tr><td>{column}</td><td>{score:.3f}</td><td>{'DRIFT' if column in drifted else 'OK'}</td></tr>"
            for column, score in sorted(scores.items(), key=lambda item: item[1], reverse=True)
        )
        html = f"""<!doctype html><html><head><meta charset="utf-8"><title>Drift Report</title>
<style>body{{font-family:Arial,sans-serif;margin:40px}}table{{border-collapse:collapse}}th,td{{border:1px solid #ddd;padding:8px}}th{{background:#101b34;color:white}}</style>
</head><body><h1>Data Drift Report</h1><p>Fallback report: Evidently native imports are blocked by Windows Application Control.</p>
<p><b>Drifted columns: {len(drifted)} of {len(RAW)} ({share:.0%})</b></p>
<table><tr><th>Feature</th><th>Mean shift (std units)</th><th>Status</th></tr>{rows}</table>
<p><b>{'DRIFT DETECTED -> retrain model' if share >= 0.3 else 'No significant drift'}</b></p></body></html>"""
        open(out, "w", encoding="utf-8").write(html)
        print(f"Drifted columns: {len(drifted)} of {len(RAW)} ({share:.0%})")
        print("DRIFT DETECTED -> retrain model" if share >= 0.3 else "No significant drift")
print("Report saved:", out)
