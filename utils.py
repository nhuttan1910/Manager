"""Hàm tiện ích dùng chung: định dạng tiền, chọn tháng, tính ngân sách."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date

import pandas as pd
import streamlit as st

import db

WARN_RATIO = 0.8  # cảnh báo khi đã dùng >= 80% ngân sách


def fmt_vnd(n: float | int) -> str:
    return f"{int(round(n)):,} ₫".replace(",", ".")


def month_bounds(year: int, month: int) -> tuple[date, date]:
    last = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last)


def prev_month(year: int, month: int) -> tuple[int, int]:
    return (year - 1, 12) if month == 1 else (year, month - 1)


def month_picker(key: str) -> tuple[int, int]:
    """Hai ô chọn tháng / năm, mặc định là tháng hiện tại."""
    today = date.today()
    c1, c2, _ = st.columns([1, 1, 3])
    month = c1.selectbox(
        "Tháng", list(range(1, 13)), index=today.month - 1, key=f"{key}_m",
        format_func=lambda m: f"Tháng {m}",
    )
    years = list(range(today.year - 5, today.year + 2))
    year = c2.selectbox("Năm", years, index=years.index(today.year), key=f"{key}_y")
    return year, month


@dataclass
class BudgetLine:
    name: str
    budget: int
    spent: int

    @property
    def ratio(self) -> float:
        return self.spent / self.budget if self.budget else 0.0

    @property
    def remaining(self) -> int:
        return self.budget - self.spent

    @property
    def level(self) -> str:
        if self.ratio >= 1:
            return "over"
        if self.ratio >= WARN_RATIO:
            return "warn"
        return "ok"


def budget_status(year: int, month: int, expenses: pd.DataFrame | None = None) -> list[BudgetLine]:
    """Tình hình ngân sách của một tháng. Dòng ngân sách tổng (nếu có) đứng đầu."""
    budgets = db.get_budgets()
    if not budgets:
        return []
    if expenses is None:
        start, end = month_bounds(year, month)
        expenses = db.list_transactions(start, end, ctype=db.EXPENSE)
    spent_by_cat = expenses.groupby("category_id")["amount"].sum() if not expenses.empty else pd.Series(dtype="int64")
    names = db.list_categories(db.EXPENSE).set_index("id")["name"].to_dict()

    lines: list[BudgetLine] = []
    if None in budgets:
        lines.append(BudgetLine("Tổng chi tiêu", budgets[None], int(spent_by_cat.sum())))
    for cat_id, amount in sorted(
        ((k, v) for k, v in budgets.items() if k is not None),
        key=lambda kv: names.get(kv[0], ""),
    ):
        if cat_id in names:
            lines.append(BudgetLine(names[cat_id], amount, int(spent_by_cat.get(cat_id, 0))))
    return lines


def render_budget_lines(lines: list[BudgetLine], year: int, month: int) -> None:
    """Thanh tiến độ + cảnh báo cho từng dòng ngân sách."""
    today = date.today()
    is_current = (year, month) == (today.year, today.month)
    days_left = calendar.monthrange(year, month)[1] - today.day + 1 if is_current else 0

    for line in lines:
        icon = {"ok": "🟢", "warn": "🟠", "over": "🔴"}[line.level]
        st.markdown(
            f"{icon} **{line.name}** — {fmt_vnd(line.spent)} / {fmt_vnd(line.budget)} "
            f"({line.ratio:.0%})"
        )
        st.progress(min(line.ratio, 1.0))
        if line.level == "over":
            st.error(f"Đã vượt ngân sách **{line.name}** {fmt_vnd(-line.remaining)}.", icon="🚨")
        elif line.level == "warn":
            msg = f"Sắp chạm ngân sách **{line.name}**: còn {fmt_vnd(line.remaining)}"
            if days_left:
                msg += f" cho {days_left} ngày (~{fmt_vnd(line.remaining / days_left)}/ngày)"
            st.warning(msg + ".", icon="⚠️")


def category_options(ctype: str) -> dict[int, str]:
    df = db.list_categories(ctype)
    return dict(zip(df["id"].astype(int), df["name"]))
