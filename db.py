"""Lớp truy cập dữ liệu.

- Chạy trên máy: mặc định dùng SQLite (file data/expenses.db).
- Chạy trên Streamlit Cloud: đặt DATABASE_URL (Supabase Postgres) trong Secrets.
"""

from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    create_engine,
    delete,
    func,
    insert,
    select,
    update,
)
from sqlalchemy.engine import Engine

EXPENSE = "expense"
INCOME = "income"
TYPE_LABELS = {EXPENSE: "Chi", INCOME: "Thu"}

metadata = MetaData()

categories = Table(
    "categories",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(100), nullable=False),
    Column("type", String(10), nullable=False),  # expense | income
    UniqueConstraint("name", "type", name="uq_category_name_type"),
)

transactions = Table(
    "transactions",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("date", Date, nullable=False, index=True),
    Column("amount", BigInteger, nullable=False),  # VND, luôn dương
    Column("type", String(10), nullable=False),
    Column("category_id", Integer, ForeignKey("categories.id"), nullable=False),
    Column("note", String(500), nullable=False, default=""),
    Column("created_at", DateTime, nullable=False, default=datetime.now),
)

# category_id = NULL nghĩa là ngân sách tổng cho toàn bộ khoản chi trong tháng.
budgets = Table(
    "budgets",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("category_id", Integer, ForeignKey("categories.id"), nullable=True),
    Column("amount", BigInteger, nullable=False),
)

DEFAULT_CATEGORIES = {
    EXPENSE: [
        "Ăn uống",
        "Đi lại",
        "Nhà ở & hóa đơn",
        "Mua sắm",
        "Giải trí",
        "Sức khỏe",
        "Giáo dục",
        "Gia đình & quà tặng",
        "Khác",
    ],
    INCOME: ["Lương", "Thưởng", "Kinh doanh", "Đầu tư", "Khác"],
}


def _database_url() -> str:
    url = None
    try:
        url = st.secrets.get("DATABASE_URL")
    except Exception:  # không có file secrets.toml
        pass
    url = url or os.environ.get("DATABASE_URL")
    if url:
        # Chỉ định rõ driver psycopg (v3); chấp nhận cả dạng postgres:// của Supabase/Heroku
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                url = "postgresql+psycopg://" + url[len(prefix) :]
                break
        return url
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(exist_ok=True)
    return f"sqlite:///{data_dir / 'expenses.db'}"


@st.cache_resource
def get_engine() -> Engine:
    engine = create_engine(_database_url(), pool_pre_ping=True)
    metadata.create_all(engine)
    _seed_categories(engine)
    return engine


def is_sqlite() -> bool:
    return get_engine().dialect.name == "sqlite"


def _seed_categories(engine: Engine) -> None:
    with engine.begin() as conn:
        count = conn.execute(select(func.count()).select_from(categories)).scalar_one()
        if count == 0:
            conn.execute(
                insert(categories),
                [
                    {"name": name, "type": ctype}
                    for ctype, names in DEFAULT_CATEGORIES.items()
                    for name in names
                ],
            )


# ---------- Danh mục ----------

def list_categories(ctype: str | None = None) -> pd.DataFrame:
    stmt = select(categories).order_by(categories.c.type, categories.c.name)
    if ctype:
        stmt = stmt.where(categories.c.type == ctype)
    with get_engine().connect() as conn:
        return pd.DataFrame(conn.execute(stmt).mappings().all(), columns=["id", "name", "type"])


def add_category(name: str, ctype: str) -> None:
    with get_engine().begin() as conn:
        conn.execute(insert(categories).values(name=name.strip(), type=ctype))


def rename_category(category_id: int, name: str) -> None:
    with get_engine().begin() as conn:
        conn.execute(
            update(categories).where(categories.c.id == category_id).values(name=name.strip())
        )


def category_usage(category_id: int) -> int:
    with get_engine().connect() as conn:
        return conn.execute(
            select(func.count())
            .select_from(transactions)
            .where(transactions.c.category_id == category_id)
        ).scalar_one()


def delete_category(category_id: int) -> None:
    """Chỉ xóa được danh mục chưa có giao dịch nào."""
    if category_usage(category_id):
        raise ValueError("Danh mục đang có giao dịch, không thể xóa.")
    with get_engine().begin() as conn:
        conn.execute(delete(budgets).where(budgets.c.category_id == category_id))
        conn.execute(delete(categories).where(categories.c.id == category_id))


# ---------- Giao dịch ----------

def add_transaction(d: date, amount: int, ctype: str, category_id: int, note: str) -> None:
    with get_engine().begin() as conn:
        conn.execute(
            insert(transactions).values(
                date=d,
                amount=int(amount),
                type=ctype,
                category_id=int(category_id),
                note=note.strip(),
                created_at=datetime.now(),
            )
        )


def update_transaction(
    tx_id: int, d: date, amount: int, ctype: str, category_id: int, note: str
) -> None:
    with get_engine().begin() as conn:
        conn.execute(
            update(transactions)
            .where(transactions.c.id == tx_id)
            .values(
                date=d,
                amount=int(amount),
                type=ctype,
                category_id=int(category_id),
                note=note.strip(),
            )
        )


def delete_transaction(tx_id: int) -> None:
    with get_engine().begin() as conn:
        conn.execute(delete(transactions).where(transactions.c.id == tx_id))


def list_transactions(
    start: date | None = None,
    end: date | None = None,
    ctype: str | None = None,
    category_ids: list[int] | None = None,
) -> pd.DataFrame:
    """Trả về DataFrame: id, date, amount, type, category_id, category, note."""
    stmt = (
        select(
            transactions.c.id,
            transactions.c.date,
            transactions.c.amount,
            transactions.c.type,
            transactions.c.category_id,
            categories.c.name.label("category"),
            transactions.c.note,
        )
        .join(categories, categories.c.id == transactions.c.category_id)
        .order_by(transactions.c.date.desc(), transactions.c.id.desc())
    )
    if start:
        stmt = stmt.where(transactions.c.date >= start)
    if end:
        stmt = stmt.where(transactions.c.date <= end)
    if ctype:
        stmt = stmt.where(transactions.c.type == ctype)
    if category_ids:
        stmt = stmt.where(transactions.c.category_id.in_(category_ids))
    cols = ["id", "date", "amount", "type", "category_id", "category", "note"]
    with get_engine().connect() as conn:
        df = pd.DataFrame(conn.execute(stmt).mappings().all(), columns=cols)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["amount"] = df["amount"].astype("int64")
    return df


# ---------- Ngân sách ----------

def get_budgets() -> dict[int | None, int]:
    """{category_id hoặc None (tổng): hạn mức/tháng}"""
    with get_engine().connect() as conn:
        rows = conn.execute(select(budgets.c.category_id, budgets.c.amount)).all()
    return {r.category_id: int(r.amount) for r in rows}


def set_budget(category_id: int | None, amount: int) -> None:
    """amount <= 0 nghĩa là bỏ ngân sách."""
    cond = (
        budgets.c.category_id.is_(None)
        if category_id is None
        else budgets.c.category_id == category_id
    )
    with get_engine().begin() as conn:
        conn.execute(delete(budgets).where(cond))
        if amount and amount > 0:
            conn.execute(insert(budgets).values(category_id=category_id, amount=int(amount)))
