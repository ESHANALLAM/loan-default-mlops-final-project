import uuid

from fastapi.testclient import TestClient
from src.api import app

c = TestClient(app)
SAMPLE = dict(age=35, annual_income=55000, loan_amount=15000, interest_rate=14.5,
              loan_term_months=36, credit_score=640, employment_years=4,
              dti=22, open_accounts=6, home_ownership="RENT")

def test_health():
    assert c.get("/health").json()["status"] == "ok"

def test_predict():
    r = c.post("/predict", json=SAMPLE)
    assert r.status_code == 401
    assert c.get("/recent").status_code == 401


def test_login_first_page():
    response = c.get("/")
    assert response.status_code == 200
    assert response.text.index('id="authPage"') < response.text.index('id="appShell"')
    assert 'id="registerTab"' in response.text


def test_account_prediction_history_is_private_and_remembered():
    email_a = f"user-{uuid.uuid4().hex}@example.com"
    email_b = f"user-{uuid.uuid4().hex}@example.com"
    user_a = TestClient(app)
    user_b = TestClient(app)

    registered = user_a.post("/auth/register", json={
        "name": "Demo User", "email": email_a, "password": "secret123"
    })
    assert registered.status_code == 200
    predicted = user_a.post("/predict", json=SAMPLE)
    assert predicted.status_code == 200
    history = user_a.get("/auth/me")
    assert history.status_code == 200
    assert len(history.json()["predictions"]) == 1

    assert user_b.get("/auth/me").status_code == 401
    assert user_b.get("/recent").status_code == 401
    registered_b = user_b.post("/auth/register", json={
        "name": "Other User", "email": email_b, "password": "secret123"
    })
    assert registered_b.status_code == 200
    assert user_b.get("/auth/me").json()["predictions"] == []

    returning_user = TestClient(app)
    logged_in = returning_user.post("/auth/login", json={
        "email": email_a, "password": "secret123"
    })
    assert logged_in.status_code == 200
    assert len(returning_user.get("/auth/me").json()["predictions"]) == 1
    assert returning_user.post("/auth/logout").status_code == 200
    assert returning_user.get("/auth/me").status_code == 401
