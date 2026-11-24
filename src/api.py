import datetime, hashlib, json, os, secrets, sqlite3
from pathlib import Path
import joblib, pandas as pd
from fastapi import Cookie, FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from src.features import RAW, prepare

app = FastAPI(title="Loan Default Prediction API", version="1.0")
model = joblib.load("models/model.joblib")
LOG = "logs/predictions.csv"
DB = os.getenv("APP_DB_PATH", "data/app.db")
DATABASE_URL = os.getenv("DATABASE_URL")


class DatabaseConnection:
    def __init__(self, connection, postgres=False):
        self.connection = connection
        self.postgres = postgres

    def execute(self, query, params=()):
        if self.postgres:
            query = query.replace("?", "%s")
        return self.connection.execute(query, params)

    def commit(self):
        self.connection.commit()

    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.commit()
        else:
            self.connection.rollback()
        self.close()


def db():
    if DATABASE_URL:
        import psycopg
        from psycopg.rows import dict_row

        url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        con = DatabaseConnection(psycopg.connect(url, row_factory=dict_row), postgres=True)
        id_type = "BIGSERIAL PRIMARY KEY"
        user_id_type = "BIGINT"
    else:
        db_dir = os.path.dirname(DB)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        con = DatabaseConnection(sqlite3.connect(DB))
        con.connection.row_factory = sqlite3.Row
        id_type = "INTEGER PRIMARY KEY AUTOINCREMENT"
        user_id_type = "INTEGER"

    con.execute(f"""CREATE TABLE IF NOT EXISTS users (
        id {id_type},
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""")
    con.execute(f"""CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id {user_id_type} NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")
    con.execute(f"""CREATE TABLE IF NOT EXISTS predictions (
        id {id_type},
        user_id {user_id_type},
        age INTEGER,
        annual_income REAL,
        loan_amount REAL,
        interest_rate REAL,
        loan_term_months INTEGER,
        credit_score INTEGER,
        employment_years REAL,
        dti REAL,
        open_accounts INTEGER,
        home_ownership TEXT,
        probability REAL NOT NULL,
        risk_level TEXT NOT NULL,
        decision TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")
    return con


def password_hash(password: str, salt: str = None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return f"{salt}${digest}"


def password_ok(password: str, stored: str):
    salt, digest = stored.split("$", 1)
    return secrets.compare_digest(password_hash(password, salt).split("$", 1)[1], digest)


def current_user(session: str = None):
    if not session:
        return None
    con = db()
    row = con.execute(
        """SELECT users.id, users.name, users.email FROM sessions
           JOIN users ON users.id = sessions.user_id WHERE sessions.token=?""",
        (session,),
    ).fetchone()
    con.close()
    return dict(row) if row else None


def authenticated_user(session: str = None):
    user = current_user(session)
    if not user:
        raise HTTPException(status_code=401, detail="Please log in to continue")
    return user


with db() as con:
    pass

@app.get("/", response_class=HTMLResponse)
def home():
    return Path("static/index.html").read_text(encoding="utf-8")

@app.get("/metrics")
def metrics():
    if not os.path.exists("models/metrics.json"):
        return {}
    return json.load(open("models/metrics.json"))

@app.get("/recent")
def recent(n: int = 8, session: str = Cookie(default=None)):
    user = authenticated_user(session)
    con = db()
    rows = con.execute(
        "SELECT * FROM predictions WHERE user_id=? ORDER BY id DESC LIMIT ?",
        (user["id"], max(1, min(n, 100))),
    ).fetchall()
    con.close()
    return [dict(row) for row in rows]

class Loan(BaseModel):
    age: int = Field(ge=18, le=100)
    annual_income: float = Field(gt=0)
    loan_amount: float = Field(gt=0)
    interest_rate: float
    loan_term_months: int
    credit_score: int = Field(ge=300, le=850)
    employment_years: float = Field(ge=0)
    dti: float = Field(ge=0)
    open_accounts: int = Field(ge=0)
    home_ownership: str = "RENT"


class AuthRequest(BaseModel):
    name: str = Field(default="", min_length=1)
    email: str = Field(min_length=3)
    password: str = Field(min_length=6)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=6)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/predict")
def predict(loan: Loan, session: str = Cookie(default=None)):
    user = authenticated_user(session)
    row = loan.model_dump()
    prob = float(model.predict_proba(prepare(pd.DataFrame([row])))[0, 1])
    level, action = (("LOW", "APPROVE") if prob < 0.2 else
                     ("MEDIUM", "MANUAL REVIEW") if prob < 0.5 else ("HIGH", "REJECT"))
    con = db()
    con.execute(
        """INSERT INTO predictions
        (user_id, age, annual_income, loan_amount, interest_rate, loan_term_months,
         credit_score, employment_years, dti, open_accounts, home_ownership,
         probability, risk_level, decision, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user["id"], row["age"], row["annual_income"], row["loan_amount"],
         row["interest_rate"], row["loan_term_months"], row["credit_score"],
         row["employment_years"], row["dti"], row["open_accounts"], row["home_ownership"],
         round(prob, 4), level, action, datetime.datetime.now().isoformat()),
    )
    con.commit()
    con.close()
    return {"default_probability": round(prob, 4), "risk_level": level, "decision": action}


@app.post("/auth/register")
def register(data: AuthRequest, response: Response):
    con = db()
    if con.execute("SELECT id FROM users WHERE email=?", (data.email.lower(),)).fetchone():
        con.close()
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    con.execute(
        "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (data.name.strip(), data.email.lower(), password_hash(data.password),
         datetime.datetime.now().isoformat()),
    )
    user_id = con.execute("SELECT id FROM users WHERE email=?", (data.email.lower(),)).fetchone()["id"]
    token = secrets.token_urlsafe(32)
    con.execute("INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
                (token, user_id, datetime.datetime.now().isoformat()))
    con.commit()
    con.close()
    response.set_cookie(
        "session", token, httponly=True, samesite="lax",
        secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
    )
    return {"name": data.name.strip(), "email": data.email.lower()}


@app.post("/auth/login")
def login(data: LoginRequest, response: Response):
    con = db()
    row = con.execute("SELECT * FROM users WHERE email=?", (data.email.lower(),)).fetchone()
    if not row or not password_ok(data.password, row["password_hash"]):
        con.close()
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = secrets.token_urlsafe(32)
    con.execute("INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
                (token, row["id"], datetime.datetime.now().isoformat()))
    con.commit()
    con.close()
    response.set_cookie(
        "session", token, httponly=True, samesite="lax",
        secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
    )
    return {"name": row["name"], "email": row["email"]}


@app.post("/auth/logout")
def logout(response: Response, session: str = Cookie(default=None)):
    if session:
        con = db()
        con.execute("DELETE FROM sessions WHERE token=?", (session,))
        con.commit()
        con.close()
    response.delete_cookie("session")
    return {"status": "logged out"}


@app.get("/auth/me")
def me(session: str = Cookie(default=None)):
    user = authenticated_user(session)
    con = db()
    rows = con.execute(
        "SELECT * FROM predictions WHERE user_id=? ORDER BY id DESC LIMIT 20",
        (user["id"],),
    ).fetchall()
    con.close()
    return {"user": user, "predictions": [dict(row) for row in rows]}
