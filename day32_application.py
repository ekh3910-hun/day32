import os
import uuid
from pathlib import Path

import pandas as pd
import psycopg
import streamlit as st
from dotenv import load_dotenv
from psycopg.rows import dict_row



# 환경변수
load_dotenv(Path(__file__).resolve().parent / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")


# 계산 함수
def calculate_balance(income, expense):
    return income - expense


# DB 연결
def get_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL이 설정되지 않았습니다.")

    return psycopg.connect(DATABASE_URL)


# 테이블 생성
def create_table():
    sql = """
    CREATE TABLE IF NOT EXISTS budget_plans (
        id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        title VARCHAR(80) NOT NULL,
        income INTEGER NOT NULL CHECK (income >= 0),
        expense INTEGER NOT NULL CHECK (expense >= 0),
        balance INTEGER NOT NULL,
        request_key UUID UNIQUE NOT NULL
    );
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)


# 예산 계획 저장
def save_plan(plan):
    sql = """
    INSERT INTO budget_plans
        (title, income, expense, balance, request_key)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (request_key) DO NOTHING
    RETURNING id;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    plan["title"],
                    plan["income"],
                    plan["expense"],
                    plan["balance"],
                    plan["request_key"],
                ),
            )

            result = cur.fetchone()

            if result:
                return result[0], True

            # 이미 저장된 요청 키라면 기존 ID 반환
            cur.execute(
                """
                SELECT id
                FROM budget_plans
                WHERE request_key = %s;
                """,
                (plan["request_key"],),
            )

            existing = cur.fetchone()
            if existing is None:
                raise RuntimeError("요청 키에 해당하는 저장 기록을 찾지 못했습니다.")

            return existing[0], False


# 제목 검색
def search_plans(keyword):
    sql = """
    SELECT id, title, income, expense, balance
    FROM budget_plans
    WHERE title ILIKE %s
    ORDER BY id DESC
    LIMIT 100;
    """

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (f"%{keyword}%",))
            return cur.fetchall()


# ID별 상세 조회
def get_plan_by_id(plan_id):
    sql = """
    SELECT id, title, income, expense, balance, request_key
    FROM budget_plans
    WHERE id = %s;
    """

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (plan_id,))
            return cur.fetchone()


# 전체 통계 (검색 조건과 무관)
def get_statistics():
    sql = """
    SELECT
        COUNT(*) AS total_count,
        COALESCE(SUM(balance), 0) AS total_balance
    FROM budget_plans;
    """

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql)
            return cur.fetchone()


# Streamlit 화면
st.set_page_config(
    page_title="월간 예산 계획",
    page_icon="💰",
    layout="centered",
)

st.title("💰 월간 예산 계획")
st.write("수입과 지출을 입력하고 예상 잔액을 계산하여 저장합니다.")


# 세션 상태 초기화
if "budget_preview" not in st.session_state:
    st.session_state.budget_preview = None

if "budget_request_key" not in st.session_state:
    st.session_state.budget_request_key = None


# DB 준비
try:
    create_table()
except (ValueError, psycopg.Error) as e:
    st.error(f"DB 연결 오류: {e}")
    st.info("DB 연결이 복구되면 저장과 조회를 다시 시도할 수 있습니다.")


# 입력
st.subheader("예산 계획 입력")

title = st.text_input(
    "계획 제목",
    max_chars=80,
    placeholder="예) 10월 생활비",
)

income = st.number_input(
    "예상 수입(원)",
    min_value=0,
    max_value=100000000,
    value=100000,
    step=1000,
)

expense = st.number_input(
    "예상 지출(원)",
    min_value=0,
    max_value=100000000,
    value=70000,
    step=1000,
)


# 계산 미리보기
if st.button("계산 미리보기"):
    if not title.strip():
        st.warning("계획 제목을 입력하세요.")
    else:
        balance = calculate_balance(income, expense)

        st.session_state.budget_preview = {
            "title": title.strip(),
            "income": income,
            "expense": expense,
            "balance": balance,
        }

        st.session_state.budget_request_key = uuid.uuid4()


# 미리보기 결과
if st.session_state.budget_preview is not None:
    plan = st.session_state.budget_preview

    st.divider()
    st.subheader("계산 미리보기")

    st.write(f"제목: {plan['title']}")
    st.write(f"수입: {plan['income']:,}원")
    st.write(f"지출: {plan['expense']:,}원")

    st.metric(
        "예상 잔액",
        f"{plan['balance']:,}원",
    )

    st.caption(
        f"요청 키: {st.session_state.budget_request_key}"
    )

    # DB 저장
    if st.button("DB 저장"):
        try:
            save_data = {
                **plan,
                "request_key": st.session_state.budget_request_key,
            }

            saved_id, is_new = save_plan(save_data)

            if is_new:
                st.success(f"새 계획 저장 완료! ID: {saved_id}")
            else:
                st.info(f"이미 저장된 요청입니다. 기존 ID: {saved_id}")

        except (ValueError, psycopg.Error, RuntimeError) as e:
            st.error(f"DB 저장 실패: {e}")
            st.info("미리보기와 요청 키는 유지됩니다. 다시 저장할 수 있습니다.")


# 전체 통계
st.divider()
st.subheader("전체 예산 통계")

try:
    stats = get_statistics()

    col1, col2 = st.columns(2)

    with col1:
        st.metric("전체 계획 건수", f"{stats['total_count']}건")

    with col2:
        st.metric(
            "전체 잔액 합계",
            f"{stats['total_balance']:,}원",
        )

except (ValueError, psycopg.Error) as e:
    st.error(f"통계 조회 실패: {e}")


# 제목 검색
st.divider()
st.subheader("예산 계획 검색")

keyword = st.text_input(
    "제목 검색",
    placeholder="검색어를 입력하세요",
)

try:
    plans = search_plans(keyword)

    if plans:
        df = pd.DataFrame(plans)
        st.dataframe(df, hide_index=True, use_container_width=True)
    else:
        st.info("검색 결과가 없습니다.")

except (ValueError, psycopg.Error) as e:
    st.error(f"목록 조회 실패: {e}")


# ID별 상세 조회
st.divider()
st.subheader("계획 상세 조회")

plan_id = st.number_input(
    "조회할 계획 ID",
    min_value=1,
    value=1,
    step=1,
)

if st.button("상세 조회"):
    try:
        detail = get_plan_by_id(plan_id)

        if detail:
            st.json({
                "id": detail["id"],
                "title": detail["title"],
                "income": detail["income"],
                "expense": detail["expense"],
                "balance": detail["balance"],
                "request_key": str(detail["request_key"]),
            })
        else:
            st.warning("해당 ID의 계획이 없습니다.")

    except (ValueError, psycopg.Error) as e:
        st.error(f"상세 조회 실패: {e}")

st.write("Streamlit 화면 테스트")