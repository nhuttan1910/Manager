"""Thành phần giao diện dùng chung: CSS, thẻ số liệu, thẻ ngân sách, danh sách giao dịch."""

from __future__ import annotations

import html
from datetime import date

import pandas as pd
import streamlit as st

import db
from utils import fmt_vnd

GREEN = "#12b886"
RED = "#f0525a"
ORANGE = "#f59f00"
BLUE = "#4c6ef5"
CHART_COLORS = ["#12b886", "#4c6ef5", "#f59f00", "#f0525a", "#7950f2",
                "#15aabf", "#e64980", "#82c91e", "#fd7e14", "#868e96"]

CATEGORY_ICONS = {
    "Ăn uống": "🍜", "Đi lại": "🛵", "Nhà ở & hóa đơn": "🏠", "Mua sắm": "🛍️",
    "Giải trí": "🎬", "Sức khỏe": "💊", "Giáo dục": "📚", "Gia đình & quà tặng": "🎁",
    "Lương": "💼", "Thưởng": "🏆", "Kinh doanh": "🏪", "Đầu tư": "📈", "Khác": "📌",
}

_CSS = """
<style>
.block-container {max-width: 1200px;}
h1 {letter-spacing: -0.02em;}

.page-head {margin: 0 0 0.25rem 0;}
.page-head .title {font-size: 1.9rem; font-weight: 700; letter-spacing: -0.02em; line-height: 1.2;}
.page-head .sub {opacity: .65; font-size: .95rem; margin-top: .15rem;}

.kpi {border-radius: 16px; padding: 18px 20px; border: 1px solid rgba(128,128,128,.18);
      background: linear-gradient(135deg, var(--kpi-bg) 0%, rgba(128,128,128,.03) 100%);
      height: 100%;}
.kpi .label {font-size: .85rem; opacity: .75; display: flex; align-items: center; gap: .4rem;}
.kpi .value {font-size: 1.65rem; font-weight: 700; margin-top: .35rem; color: var(--kpi-fg);
             letter-spacing: -0.01em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;}
.kpi .foot {margin-top: .4rem; font-size: .8rem; opacity: .8;}
.chip {display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: .75rem; font-weight: 600;}
.chip.good {background: rgba(18,184,134,.15); color: #0ca678;}
.chip.bad {background: rgba(240,82,90,.15); color: #e03131;}
.chip.neutral {background: rgba(128,128,128,.15);}

.budget {padding: 12px 0 14px 0; border-bottom: 1px solid rgba(128,128,128,.14);}
.budget:last-child {border-bottom: none;}
.budget .row {display: flex; justify-content: space-between; align-items: baseline; gap: .5rem;}
.budget .name {font-weight: 600;}
.budget .pct {font-weight: 700; font-size: .9rem;}
.budget .track {height: 8px; border-radius: 999px; background: rgba(128,128,128,.18); margin: .45rem 0 .35rem 0; overflow: hidden;}
.budget .fill {height: 100%; border-radius: 999px;}
.budget .meta {font-size: .8rem; opacity: .7; display: flex; justify-content: space-between; gap: .5rem;}
.budget .note {font-size: .8rem; margin-top: .3rem; font-weight: 500;}

.tx {display: flex; align-items: center; gap: .8rem; padding: 10px 2px; border-bottom: 1px solid rgba(128,128,128,.12);}
.tx:last-child {border-bottom: none;}
.tx .ico {width: 38px; height: 38px; border-radius: 12px; display: flex; align-items: center; justify-content: center;
          font-size: 1.15rem; background: rgba(128,128,128,.12); flex-shrink: 0;}
.tx .main {flex: 1; min-width: 0;}
.tx .cat {font-weight: 600; font-size: .92rem;}
.tx .note {font-size: .8rem; opacity: .65; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;}
.tx .amt {font-weight: 700; white-space: nowrap; text-align: right;}
.tx .amt small {display: block; font-weight: 400; font-size: .75rem; opacity: .6;}

.login-hero {text-align: center; margin: 4rem 0 1.5rem 0;}
.login-hero .logo {font-size: 3rem;}
.login-hero .title {font-size: 1.6rem; font-weight: 700; margin-top: .4rem;}
.login-hero .sub {opacity: .65;}
</style>
"""


def inject_css() -> None:
    st.html(_CSS)


def icon_for(category: str, ctype: str = db.EXPENSE) -> str:
    return CATEGORY_ICONS.get(category, "💸" if ctype == db.EXPENSE else "💰")


def page_header(title: str, subtitle: str = "") -> None:
    sub = f'<div class="sub">{html.escape(subtitle)}</div>' if subtitle else ""
    st.markdown(
        f'<div class="page-head"><div class="title">{html.escape(title)}</div>{sub}</div>',
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value: int, color: str, icon: str,
             delta: int | None = None, higher_is_good: bool = True) -> None:
    foot = ""
    if delta is not None:
        good = (delta >= 0) == higher_is_good
        cls = "neutral" if delta == 0 else ("good" if good else "bad")
        arrow = "▲" if delta > 0 else ("▼" if delta < 0 else "■")
        foot = f'<div class="foot"><span class="chip {cls}">{arrow} {fmt_vnd(abs(delta))}</span> so với tháng trước</div>'
    st.markdown(
        f'<div class="kpi" style="--kpi-fg:{color}; --kpi-bg:{color}1f">'
        f'<div class="label">{icon} {html.escape(label)}</div>'
        f'<div class="value">{fmt_vnd(value)}</div>{foot}</div>',
        unsafe_allow_html=True,
    )


def budget_cards(lines, days_left: int = 0) -> None:
    """lines: list[utils.BudgetLine]"""
    parts = []
    for ln in lines:
        color = {"ok": GREEN, "warn": ORANGE, "over": RED}[ln.level]
        if ln.level == "over":
            note = f'<div class="note" style="color:{RED}">🚨 Đã vượt {fmt_vnd(-ln.remaining)}</div>'
        elif ln.level == "warn":
            extra = f" · ~{fmt_vnd(ln.remaining / days_left)}/ngày" if days_left else ""
            note = f'<div class="note" style="color:{ORANGE}">⚠️ Sắp chạm hạn mức{extra}</div>'
        else:
            note = ""
        remain = f"Còn {fmt_vnd(ln.remaining)}" if ln.remaining >= 0 else "Hết hạn mức"
        parts.append(
            f'<div class="budget"><div class="row">'
            f'<span class="name">{icon_for(ln.name) if ln.name != "Tổng chi tiêu" else "🎯"} {html.escape(ln.name)}</span>'
            f'<span class="pct" style="color:{color}">{ln.ratio:.0%}</span></div>'
            f'<div class="track"><div class="fill" style="width:{min(ln.ratio, 1) * 100:.1f}%; background:{color}"></div></div>'
            f'<div class="meta"><span>{fmt_vnd(ln.spent)} / {fmt_vnd(ln.budget)}</span><span>{remain}</span></div>'
            f"{note}</div>"
        )
    st.markdown("".join(parts), unsafe_allow_html=True)


def tx_list(df: pd.DataFrame) -> None:
    """Danh sách giao dịch dạng thẻ (dùng cho vài dòng gần đây)."""
    rows = []
    for r in df.itertuples():
        is_inc = r.type == db.INCOME
        color = GREEN if is_inc else RED
        sign = "+" if is_inc else "−"
        d = r.date.strftime("%d/%m") if isinstance(r.date, date) else str(r.date)
        note = html.escape(r.note) if r.note else "&nbsp;"
        rows.append(
            f'<div class="tx"><div class="ico">{icon_for(r.category, r.type)}</div>'
            f'<div class="main"><div class="cat">{html.escape(r.category)}</div><div class="note">{note}</div></div>'
            f'<div class="amt" style="color:{color}">{sign}{fmt_vnd(r.amount)}<small>{d}</small></div></div>'
        )
    st.markdown("".join(rows), unsafe_allow_html=True)


def style_fig(fig, height: int | None = None):
    fig.update_layout(
        separators=",.",
        margin=dict(t=10, l=10, r=10, b=10),
        legend=dict(title_text="", orientation="h", yanchor="bottom", y=1.02, x=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Be Vietnam Pro, sans-serif"),
        hoverlabel=dict(font_family="Be Vietnam Pro, sans-serif"),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(128,128,128,.15)", zeroline=False)
    if height:
        fig.update_layout(height=height)
    return fig
