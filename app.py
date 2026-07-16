# -*- coding: utf-8 -*-
"""
종로구 공공시설 태양광 설치 현황 대시보드
Streamlit + Plotly
실행: streamlit run app.py
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ------------------------------------------------------------------
# 페이지 설정
# ------------------------------------------------------------------
st.set_page_config(
    page_title="종로구 공공시설 태양광 설치 대시보드",
    page_icon="☀️",
    layout="wide",
)

CSV_PATH = "서울특별시_종로구_공공시설_태양광_설치현황_20210423.csv"

# ------------------------------------------------------------------
# 데이터 로드 & 전처리
# ------------------------------------------------------------------
@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8")
    df = df.rename(columns={"설치용량(킬로와트)": "설치용량_kW"})

    def classify(name: str) -> str:
        if any(k in name for k in ["주민센터", "자치회관", "구민회관"]):
            return "주민센터/자치회관"
        if any(k in name for k in ["복지관", "경로당", "노인"]):
            return "복지시설"
        if any(k in name for k in ["어린이집", "육아"]):
            return "보육시설"
        if "주차" in name:
            return "주차시설"
        if "화장실" in name:
            return "공원/화장실"
        if any(k in name for k in ["문화체육", "청사"]):
            return "문화체육/청사"
        return "기타"

    df["시설유형"] = df["시설명"].apply(classify)
    return df

df = load_data(CSV_PATH)

# ------------------------------------------------------------------
# 사이드바 필터
# ------------------------------------------------------------------
st.sidebar.header("필터")
year_min, year_max = int(df["설치년도"].min()), int(df["설치년도"].max())
year_range = st.sidebar.slider("설치년도", year_min, year_max, (year_min, year_max))

types = sorted(df["시설유형"].unique().tolist())
selected_types = st.sidebar.multiselect("시설 유형", types, default=types)

f = df[
    (df["설치년도"].between(*year_range))
    & (df["시설유형"].isin(selected_types))
].copy()

# ------------------------------------------------------------------
# 헤더 & KPI
# ------------------------------------------------------------------
st.title("종로구 공공시설 태양광 설치 현황 대시보드")
st.caption(f"기준일자: {df['기준일자'].iloc[0]}  ·  원본: 서울특별시 종로구")

total_kw = f["설치용량_kW"].sum()
annual_kwh = total_kw * 1300              # kW당 연간 1,300kWh 가정
co2_ton = annual_kwh * 0.4249 / 1000      # 전력 배출계수 0.4249 kgCO2/kWh

c1, c2, c3, c4 = st.columns(4)
c1.metric("설치 시설 수", f"{len(f):,} 개소")
c2.metric("총 설치용량", f"{total_kw:,.1f} kW")
c3.metric("연간 예상 발전량", f"{annual_kwh:,.0f} kWh")
c4.metric("연간 CO₂ 절감량", f"{co2_ton:,.1f} 톤")

st.divider()

# ------------------------------------------------------------------
# 차트 1: 연도별 설치 추이 (막대 + 누적선)
# ------------------------------------------------------------------
st.subheader("연도별 설치 추이")

by_year = (
    f.groupby("설치년도")
     .agg(연간건수=("시설명", "count"), 연간용량=("설치용량_kW", "sum"))
     .reset_index()
     .sort_values("설치년도")
)
by_year["누적용량"] = by_year["연간용량"].cumsum()

fig1 = go.Figure()
fig1.add_bar(
    x=by_year["설치년도"], y=by_year["연간용량"],
    name="연간 설치용량(kW)", marker_color="#2563eb",
    text=by_year["연간용량"].round(1), textposition="outside",
)
fig1.add_trace(go.Scatter(
    x=by_year["설치년도"], y=by_year["누적용량"],
    name="누적 설치용량(kW)", mode="lines+markers",
    yaxis="y2", line=dict(color="#f59e0b", width=3),
))
fig1.update_layout(
    height=380,
    xaxis=dict(title="설치년도", dtick=1),
    yaxis=dict(title="연간 설치용량 (kW)"),
    yaxis2=dict(title="누적 설치용량 (kW)", overlaying="y", side="right"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=10, r=10, t=20, b=10),
)
st.plotly_chart(fig1, use_container_width=True)

# ------------------------------------------------------------------
# 차트 2 & 3: 시설유형 분석
# ------------------------------------------------------------------
colA, colB = st.columns(2)

by_type = (
    f.groupby("시설유형")
     .agg(건수=("시설명", "count"), 총용량=("설치용량_kW", "sum"), 평균용량=("설치용량_kW", "mean"))
     .reset_index()
     .sort_values("총용량", ascending=True)
)

with colA:
    st.subheader("시설유형별 설치용량")
    fig2 = px.bar(
        by_type, x="총용량", y="시설유형", orientation="h",
        text=by_type["총용량"].round(1),
        color="총용량", color_continuous_scale="Blues",
    )
    fig2.update_traces(textposition="outside")
    fig2.update_layout(
        height=360, margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title="총 설치용량 (kW)", yaxis_title="",
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig2, use_container_width=True)

with colB:
    st.subheader("시설유형별 시설 수 비중")
    fig3 = px.pie(
        by_type, names="시설유형", values="건수", hole=0.45,
        color_discrete_sequence=px.colors.sequential.Blues_r,
    )
    fig3.update_traces(textinfo="label+percent")
    fig3.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
    st.plotly_chart(fig3, use_container_width=True)

# ------------------------------------------------------------------
# 차트 4: 시설별 설치용량 랭킹
# ------------------------------------------------------------------
st.subheader("시설별 설치용량 랭킹")
ranking = f.sort_values("설치용량_kW", ascending=True)
fig4 = px.bar(
    ranking, x="설치용량_kW", y="시설명", orientation="h",
    color="시설유형",
    text=ranking["설치용량_kW"].round(1),
    color_discrete_sequence=px.colors.qualitative.Set2,
    hover_data=["설치년도", "도로명 주소"],
)
fig4.update_traces(textposition="outside")
fig4.update_layout(
    height=max(400, 22 * len(ranking)),
    margin=dict(l=10, r=10, t=10, b=10),
    xaxis_title="설치용량 (kW)", yaxis_title="",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)
st.plotly_chart(fig4, use_container_width=True)

# ------------------------------------------------------------------
# 인사이트
# ------------------------------------------------------------------
st.divider()
st.subheader("주요 인사이트")
st.markdown(
    f"""
- **총 {len(df)}개소, {df['설치용량_kW'].sum():.1f} kW**가 설치되었으며, 연간 약 **{df['설치용량_kW'].sum()*1300:,.0f} kWh** 발전으로 CO₂ **{df['설치용량_kW'].sum()*1300*0.4249/1000:.1f}톤** 저감 효과가 추정됩니다.
- **복지시설이 6개소·91.5 kW로 최대 축**을 이루며, 다음이 주민센터/자치회관(5개소·66.4 kW) 순입니다.
- **2009년 초기 대규모 보급(6개소·50.2 kW)** 이후 2013·2016년은 각 1건 이하로 정체, **2017~2018년(총 8개소·97.6 kW) 재확산**되는 패턴을 보입니다.
- 개별 최대는 **종로장애인복지관 33 kW**, 최소는 **부암경로당·착한주차안내소 3.46 kW** 로 시설 규모 편차가 큽니다.
- 평균 용량은 **문화체육/청사(28.2 kW) > 복지시설(15.2 kW) > 주민센터(13.3 kW)** 순으로, **대형 공공건물이 대용량 태양광의 앵커** 역할을 하고 있습니다.
"""
)

# ------------------------------------------------------------------
# 원본 데이터
# ------------------------------------------------------------------
with st.expander("원본 데이터 보기"):
    st.dataframe(f.reset_index(drop=True), use_container_width=True)
