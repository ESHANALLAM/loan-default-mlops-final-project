# Live Demo Runbook

1. **Show the data and DVC pointer.** Run `Get-Content data\loan.csv.dvc`; run `Get-Content data\loan.csv -Head 3`; explain that DVC tracks the data while Git tracks the pointer.
2. **Train the model.** Run `python -m src.train`; point out the `PROMOTED` decision, ROC-AUC, and the `Created version '1'` MLflow message.
3. **Open MLflow.** Run `python -m mlflow ui --backend-store-uri sqlite:///mlflow.db --port 5000`; open `http://127.0.0.1:5000` and show three runs and three registered model versions.
4. **Demonstrate the promotion gate.** Run the depth 3 and 5-tree commands; explain that both are rejected because their ROC-AUC is lower, even though a metric tradeoff exists.
5. **Start and show the dashboard.** Run `python -m uvicorn src.api:app --port 8000`; open `http://127.0.0.1:8000` and score LOW, MEDIUM, and HIGH applicants.
6. **Validate API tests.** Run `python -m pytest -q`; say that both FastAPI health and prediction tests pass.
7. **Show drift monitoring.** Run `python data\make_data.py --drift --seed 9 --out data\loan_new.csv`, then `python -m src.monitor`; open `reports\drift_report.html` and explain the 30% project threshold versus Evidently's 50% banner.
8. **Build and run Docker.** Run `docker build -t loan-default-api .` and `docker run -d --name loan-api -p 8000:8000 loan-default-api`; call `/health`, then stop and remove the container.
9. **Show CI and deployment.** Open GitHub Actions and show the green `build-test` workflow, then show `render.yaml` and explain the manual Render deployment step.
