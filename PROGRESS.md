# Project Progress

- Phase 0 started: created the project structure and Python virtual environment.
- Phase 0 complete: Python 3.11.9, Git 2.47.1, Docker 29.9.3; virtual environment created and dependencies installed.
- Phase 1 complete: exact project source files created and compiled successfully.
- Phase 2 complete: data generated with 5,000 rows and 23.8% default rate; DVC pointer and `data-v1` tag created.
- Phase 3 complete: first XGBoost model promoted with ROC-AUC 0.6965 and registered as MLflow version 1.
- Phase 4 complete: depth3 and weak candidates were rejected; metrics hash for the promoted model remained unchanged.
- Phase 5 complete: FastAPI dashboard, three applicant scores, 422 validation, metrics, recent predictions, health, and prediction log verified.
- Phase 6 complete: `pytest -q` passed 2 tests.
- Phase 7 complete: shifted data generated at 40.2%; 4 of 10 features drifted and drift report created.
- Phase 8 complete: Docker image `loan-default-api` built successfully; the container answered `/health` and a `/predict` request, then was stopped and removed.
- Phase 9 prepared: CI workflow exists; final model and metrics will be committed and prepared for manual GitHub push.
- Phase 10 manual: Render deployment remains for the user to complete in the browser.
- Phase 11 complete: README and RUNBOOK created.
