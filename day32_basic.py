import os
import math

import psycopg
import pandas as pd
import streamlit as st

from pathlib import Path
from dotenv import load_dotenv
from psycopg.rows import dict_row

# 환경변수 불러오기
load_dotenv(Path(__file__).resolve().parent / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
RULE_VERSION = "shipping-v1"


# 배송비 계산 함수 (UI, DB와 독립적)
def calculate_shipping_fee(weight):
    if weight <= 0:
        raise ValueError("무게는 1g 이상이어야 합니다.")

    if weight <= 1000:
        return 3000

    return 3000 + ((weight - 1) // 1000) * 1000


# DB 연결
def get_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL 환경변수를 설정하세요.")

    return psycopg.connect(DATABASE_URL)


# 테이블 생성
def create_table():
    sql = """
    CREATE TABLE IF NOT EXISTS shipping_quotes (
        id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        label VARCHAR(80) NOT NULL,
        weight INTEGER NOT NULL CHECK (weight > 0),
        fee INTEGER NOT NULL CHECK (fee >= 0),
        rule_version VARCHAR(20) NOT NULL
    );
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)


# 견적 저장
def save_quote(label, weight, fee):
    sql = """
    INSERT INTO shipping_quotes
        (label, weight, fee, rule_version)
    VALUES (%s, %s, %s, %s)
    RETURNING id;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (label, weight, fee, RULE_VERSION)
            )
            return cur.fetchone()[0]


# 최신 견적 100건 조회
def list_quotes():
    sql = """
    SELECT id, label, weight, fee, rule_version
    FROM shipping_quotes
    ORDER BY id DESC
    LIMIT 100;
    """

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql)
            return cur.fetchall()


# Streamlit 설정
st.set_page_config(
    page_title="배송비 견적 관리",
    page_icon="📦",
    layout="centered"
)

st.title("📦 배송비 견적 관리")
st.write("무게에 따른 배송비를 계산하고 PostgreSQL에 저장합니다.")

# 테이블 준비
try:
    create_table()
except (ValueError, psycopg.Error) as e:
    st.error(f"데이터베이스 연결 오류: {type(e).__name__}")
    st.stop()


# 견적 입력
st.subheader("배송비 계산")

with st.form("shipping_form"):
    label = st.text_input(
        "견적 제목",
        placeholder="예) 의류 배송",
        max_chars=80
    )

    weight = st.number_input(
        "무게(g)",
        min_value=1,
        max_value=20000,
        value=1000,
        step=1
    )

    submitted = st.form_submit_button("계산하고 저장")


# 계산 및 저장
if submitted:
    if not label.strip():
        st.warning("견적 제목을 입력해주세요.")

    else:
        fee = calculate_shipping_fee(weight)

        try:
            quote_id = save_quote(
                label.strip(),
                weight,
                fee
            )

            st.success("견적이 저장되었습니다.")
            st.metric("배송비", f"{fee:,}원")
            st.write(f"저장된 견적 ID: {quote_id}")

        except (ValueError, psycopg.Error) as e:
            st.error(f"견적 저장 실패: {type(e).__name__}")


# 최신 견적 목록
st.divider()
st.subheader("📋 최근 배송비 견적 100건")

try:
    quotes = list_quotes()

    if quotes:
        df = pd.DataFrame(quotes)

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("저장된 견적이 없습니다.")

except (ValueError, psycopg.Error) as e:
    st.error(f"견적 조회 실패: {type(e).__name__}")