import streamlit as st

st.set_page_config(layout="centered", initial_sidebar_state="collapsed")

# 🚨 디버깅용 CSS: 모든 요소에 빨간 테두리를 치고, Flex 대신 Grid 방식 도입
st.markdown("""
<style>
/* 1. 눈으로 확인하기 위한 빨간 테두리 (어떤 녀석이 범인인지 색출) */
div[data-testid="stHorizontalBlock"] { border: 2px solid blue !important; }
div[data-testid="column"] { border: 1px dashed red !important; }
div[data-testid="stSelectbox"] { border: 1px dotted green !important; }

/* 2. Flex 대신 더 강력한 CSS Grid로 강제 분할 테스트 */
@media (max-width: 640px) {
    div[data-testid="stHorizontalBlock"] {
        display: grid !important;
        grid-auto-flow: column !important;
        grid-auto-columns: minmax(0, 1fr) !important; /* 무조건 화면 N등분 */
        gap: 2px !important;
        overflow-x: hidden !important;
    }
    div[data-testid="column"] {
        width: 100% !important;
        min-width: 0 !important;
        padding: 0 !important;
    }
}
</style>
""", unsafe_allow_html=True)

st.write("### 🛠️ 모바일 1줄 UI 디버깅 테스트")

# 테스트 1: 이전 / N번째 / 다음 (3등분)
col_prev, col_info, col_next = st.columns([1, 1.5, 1])
with col_prev: st.button("◀ 이전")
with col_info: st.markdown("<div style='font-size:0.75rem; text-align:center;'><b>2번째 진행</b><br>12번홀</div>", unsafe_allow_html=True)
with col_next: st.button("다음 ▶")

st.markdown("---")

# 테스트 2: 선수명 / 셀렉트박스 (2등분)
col_name, col_select = st.columns([1.5, 2.5])
with col_name: st.markdown("<div style='font-weight:bold; padding-top:5px;'>홍길동(매우긴이름)</div>", unsafe_allow_html=True)
with col_select: st.selectbox("점수", ["파(0)", "버디(-1)", "+1", "+2"], label_visibility="collapsed")
