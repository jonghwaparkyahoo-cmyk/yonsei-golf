import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import gspread
import json
from google.oauth2.service_account import Credentials

# --- 디버깅 시작: Secrets 값이 어떻게 들어오는지 눈으로 확인하기 ---
st.write("### 🔍 디버깅 모드")
try:
    raw_key = st.secrets["gcp_json"]
    # 키 값이 너무 기니까 앞 50글자와 뒤 50글자만 화면에 출력 (보안 유지)
    st.write(f"Key 시작 부분: `{raw_key[:50]}`")
    st.write(f"Key 끝 부분: `{raw_key[-50:]}`")
    st.write(f"문자열 길이: {len(raw_key)}")
    st.write(f"줄바꿈(\\n) 개수: {raw_key.count(chr(10))} 개")
except Exception as e:
    st.error(f"Secrets 자체를 읽지 못함: {e}")
st.markdown("---")

st.set_page_config(page_title="연세대 골프 대회 모바일 스코어보드", layout="centered", page_icon="⛳")

# 15초마다 자동 새로고침 (모든 기기에서 실시간 동기화 유지)
st_autorefresh(interval=15000, key="datarefresh")

# 모바일 컴팩트 스타일링 CSS
st.markdown("""
<style>
.stSelectbox div[data-baseweb="select"] {
    min-height: 35px;
}
</style>
""", unsafe_allow_html=True)

# --- 1. 코스 파(Par) 정보 ---
PAR_LIST = [4, 4, 3, 4, 5, 4, 3, 5, 4, 4, 3, 5, 4, 3, 5, 4, 4, 4]

# --- 2. 구글 시트 연동 함수 (JSON 파싱 및 PEM 줄바꿈 보정) ---
if 'scores' not in st.session_state:
    st.session_state.scores = {}

# 🔑 통합 인증 함수 (이곳 한 곳에서만 인증을 처리하여 에러 확률 최소화)
def get_gspread_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    json_str = st.secrets["gcp_json"]
    creds_dict = json.loads(json_str)
    
    # 🚨 핵심 보정: PEM 개인키 내 잘못된 공백("= ")을 정상적인 줄바꿈("=\n")으로 강제 변환
    # 또한 이스케이프 문자열(\n)이 있다면 실제 줄바꿈으로 변환하여 PEM 파싱 에러(Invalid symbol 61) 완벽 차단
    if "private_key" in creds_dict:
        clean_key = creds_dict["private_key"].replace("= ", "=\n").replace("\\n", "\n")
        creds_dict["private_key"] = clean_key
        
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

def load_scores_from_gsheet():
    try:
        client = get_gspread_client()
        spreadsheet_url = st.secrets["spreadsheet_url"]
        sheet = client.open_by_url(spreadsheet_url)
        
        try:
            worksheet = sheet.worksheet("Scores")
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sheet.add_worksheet(title="Scores", rows=100, cols=3)
            worksheet.append_row(["선수명", "홀번호", "점수차"])
            return
            
        data = worksheet.get_all_records()
        if data:
            df = pd.DataFrame(data)
            if not df.empty and all(col in df.columns for col in ["선수명", "홀번호", "점수차"]):
                st.session_state.scores = {}
                for _, row in df.iterrows():
                    p_name = str(row["선수명"])
                    h_num = int(row["홀번호"])
                    diff_val = int(row["점수차"])
                    if p_name not in st.session_state.scores:
                        st.session_state.scores[p_name] = {}
                    st.session_state.scores[p_name][h_num] = diff_val
    except Exception as e:
        pass

# 앱 실행 시 시트 데이터 로드
load_scores_from_gsheet()

def save_scores_to_gsheet(scores_dict):
    try:
        client = get_gspread_client()
        spreadsheet_url = st.secrets["spreadsheet_url"]
        sheet = client.open_by_url(spreadsheet_url)
        
        try:
            worksheet = sheet.worksheet("Scores")
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sheet.add_worksheet(title="Scores", rows=100, cols=3)
            
        worksheet.clear()
        worksheet.append_row(["선수명", "홀번호", "점수차"])
        
        rows = []
        for p, holes in scores_dict.items():
            for h, d in holes.items():
                rows.append([p, h, d])
        if rows:
            worksheet.append_rows(rows)
        return True
    except Exception as e:
        st.error(f"🚨 구글 시트 저장 상세 에러: {e}")
        return False

# --- 3. 조편성 데이터 ---
if 'groups' not in st.session_state:
    st.session_state.groups = {
        "1A조": {
            "start_hole": 1,
            "players": {
                "노재호": {"hcap": 21.0, "dept": "세라믹"},
                "곽재영": {"hcap": 22.0, "dept": "전자"},
                "박주원": {"hcap": 15.0, "dept": "전자"}
            }
        },
        "1B조": {
            "start_hole": 1,
            "players": {
                "이용일": {"hcap": 25.0, "dept": "토목"},
                "신성원": {"hcap": 14.0, "dept": "전기"},
                "신현경": {"hcap": 17.0, "dept": "전자"},
                "이창호": {"hcap": 23.0, "dept": "전기"}
            }
        },
        "2조": {
            "start_hole": 2,
            "players": {
                "마이클 안": {"hcap": 8.0, "dept": "국제학부"},
                "양진기": {"hcap": "NA", "dept": "전산"},
                "박종화": {"hcap": 10.0, "dept": "전산"},
                "김택규": {"hcap": 13.0, "dept": "생화학"}
            }
        },
        "3A조": {
            "start_hole": 3,
            "players": {
                "김은혁": {"hcap": 23.0, "dept": "의학"},
                "변원석": {"hcap": "NA", "dept": "기계"},
                "임봉욱": {"hcap": 17.0, "dept": "건축"},
                "이은홍": {"hcap": 25.0, "dept": "건축"}
            }
        },
        "3B조": {
            "start_hole": 3,
            "players": {
                "남명현": {"hcap": 25.0, "dept": "수학"},
                "박재효": {"hcap": 34.0, "dept": "경제"},
                "우규진": {"hcap": 18.0, "dept": "전자"},
                "이미나": {"hcap": 24.0, "dept": "영문"}
            }
        },
        "4조": {
            "start_hole": 4,
            "players": {
                "임주연": {"hcap": "NA", "dept": "세라믹"},
                "황경진": {"hcap": "NA", "dept": "금속"},
                "김윤경": {"hcap": 36.0, "dept": "-"}
            }
        },
        "5A조": {
            "start_hole": 5,
            "players": {
                "이동휘": {"hcap": "NA", "dept": "금속"},
                "양성흠": {"hcap": "NA", "dept": "-"},
                "신재원": {"hcap": "NA", "dept": "전자"},
                "송창걸": {"hcap": 14.0, "dept": "기계"}
            }
        },
        "5B조": {
            "start_hole": 5,
            "players": {
                "박준식": {"hcap": 11.0, "dept": "사체"},
                "정태양": {"hcap": "NA", "dept": "스포츠레저"},
                "최성식": {"hcap": 13.0, "dept": "생명공학"},
                "김용민": {"hcap": 5.0, "dept": "전기"}
            }
        }
    }

st.title("⛳ 연세대 골프 대회 모바일 스코어보드")
st.markdown("---")

menu = st.sidebar.radio("메뉴 선택", ["📝 스코어 입력", "🏆 실시간 리더보드", "⚙️ 운영진 관리"])

# ==========================================
# [메뉴 1] 스코어 입력
# ==========================================
if menu == "📝 스코어 입력":
    st.header("📝 홀별 스코어 입력")
    
    group_list = list(st.session_state.groups.keys())
    
    if 'selected_group' not in st.session_state or st.session_state.selected_group not in group_list:
        st.session_state.selected_group = group_list[0]
        
    default_idx = group_list.index(st.session_state.selected_group)
    group_name = st.selectbox("조 선택", group_list, index=default_idx)
    st.session_state.selected_group = group_name
    
    group_info = st.session_state.groups[group_name]
    start_hole = group_info["start_hole"]
    players_info = group_info["players"]
    
    st.info(f"📌 **{group_name}** | 시작 홀: **{start_hole}번 홀** (샷건 방식)")
    
    hole_sequence = [(start_hole - 1 + i) % 18 + 1 for i in range(18)]
    
    hole_idx_key = f"current_hole_idx_{group_name}"
    if hole_idx_key not in st.session_state:
        st.session_state[hole_idx_key] = 0
        
    current_idx = st.session_state[hole_idx_key]
    current_course_hole = hole_sequence[current_idx]
    current_par = PAR_LIST[current_course_hole - 1]
    
    col_prev, col_info, col_next = st.columns([1, 2, 1])
    with col_prev:
        if st.button("◀ 이전 홀") and current_idx > 0:
            st.session_state[hole_idx_key] -= 1
            st.rerun()
    with col_info:
        st.markdown(f"<div style='text-align: center;'><b>전체 {current_idx + 1}번째 홀</b><br>코스 {current_course_hole}번 (Par {current_par})</div>", unsafe_allow_html=True)
    with col_next:
        if st.button("다음 홀 ▶") and current_idx < 17:
            st.session_state[hole_idx_key] += 1
            st.rerun()
            
    st.markdown("---")

    with st.form(key=f"unified_score_form_{group_name}_{current_idx}"):
        st.markdown(f"#### 🏌️‍♂️ Hole {current_course_hole}, Par {current_par}")
        
        form_inputs = {}
        for player in players_info.keys():
            if player not in st.session_state.scores:
                st.session_state.scores[player] = {}
                
            current_val = st.session_state.scores[player].get(current_course_hole, 0)
            
            max_over = current_par
            options = list(range(-2, max_over + 1))
            if current_val not in options:
                current_val = 0
                
            col_name, col_select = st.columns([1.5, 2.5])
            with col_name:
                st.markdown(f"<div style='padding-top: 6px; font-weight: bold; font-size: 0.95rem;'>{player}</div>", unsafe_allow_html=True)
            with col_select:
                score_diff = st.selectbox(
                    f"{player} 성적",
                    options=options,
                    index=options.index(current_val) if current_val in options else 2,
                    format_func=lambda x: "이글(-2)" if x==-2 else ("버디(-1)" if x==-1 else ("파(0)" if x==0 else f"+{x}")),
                    key=f"input_{player}_{current_course_hole}",
                    label_visibility="collapsed"
                )
                form_
