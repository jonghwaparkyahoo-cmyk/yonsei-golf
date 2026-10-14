import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import gspread
import json
import time
from google.oauth2.service_account import Credentials

# --- 디버깅 시작: Secrets 값이 어떻게 들어오는지 눈으로 확인하기 ---
# st.write("### 🔍 디버깅 모드")
# try:
#     raw_key = st.secrets["gcp_json"]
#     st.write(f"Key 시작 부분: `{raw_key[:50]}`")
#     st.write(f"Key 끝 부분: `{raw_key[-50:]}`")
#     st.write(f"문자열 길이: {len(raw_key)}")
#     st.write(f"줄바꿈(\\n) 개수: {raw_key.count(chr(10))} 개")
# except Exception as e:
#     st.error(f"Secrets 자체를 읽지 못함: {e}")
# st.markdown("---")

st.set_page_config(
    page_title="연세대 골프 대회 모바일 스코어보드", 
    layout="centered", 
    page_icon="⛳",
    initial_sidebar_state="collapsed"
)

# 15초마다 자동 새로고침 (모든 기기에서 실시간 동기화 유지)
st_autorefresh(interval=15000, key="datarefresh")

# 모바일 컴팩트 스타일링 CSS
st.markdown("""
<style>
.stSelectbox div[data-baseweb="select"] {
    min-height: 35px;
}
div.row-widget.stRadio > div {
    flex-direction: row;
    justify-content: space-around;
    background-color: #f0f2f6;
    padding: 10px;
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

# --- 1. 코스 파(Par) 정보 ---
PAR_LIST = [4, 4, 3, 4, 5, 4, 3, 5, 4, 4, 3, 5, 4, 3, 5, 4, 4, 4]

if 'scores' not in st.session_state:
    st.session_state.scores = {}

# 스마트 점프 기능(자동으로 빈 홀 찾기) 활성화 여부 변수
if 'auto_jump' not in st.session_state:
    st.session_state.auto_jump = True

# 🔑 통합 인증 함수
def get_gspread_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    json_str = st.secrets["gcp_json"]
    creds_dict = json.loads(json_str, strict=False)
    
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
            st.session_state.scores = {}
            return
            
        data = worksheet.get_all_records()
        
        st.session_state.scores = {}
        
        if not data:
            keys_to_delete = [k for k in st.session_state.keys() if k.startswith("input_")]
            for k in keys_to_delete:
                del st.session_state[k]
        else:
            df = pd.DataFrame(data)
            if not df.empty and all(col in df.columns for col in ["선수명", "홀번호", "점수차"]):
                for _, row in df.iterrows():
                    p_name = str(row["선수명"])
                    h_num = int(row["홀번호"])
                    diff_val = int(row["점수차"])
                    if p_name not in st.session_state.scores:
                        st.session_state.scores[p_name] = {}
                    st.session_state.scores[p_name][h_num] = diff_val
    except Exception as e:
        pass

# 앱 실행 시점 최신 데이터 로드
load_scores_from_gsheet()

# 🚨 스마트 병합(Merge) 저장 로직
def save_scores_to_gsheet(new_scores_dict):
    try:
        client = get_gspread_client()
        spreadsheet_url = st.secrets["spreadsheet_url"]
        sheet = client.open_by_url(spreadsheet_url)
        
        try:
            worksheet = sheet.worksheet("Scores")
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sheet.add_worksheet(title="Scores", rows=100, cols=3)
            
        existing_data = worksheet.get_all_records()
        db_scores = {}
        if existing_data:
            for row in existing_data:
                p = str(row["선수명"])
                h = int(row["홀번호"])
                d = int(row["점수차"])
                if p not in db_scores:
                    db_scores[p] = {}
                db_scores[p][h] = d
                
        for p, holes in new_scores_dict.items():
            if p not in db_scores:
                db_scores[p] = {}
            for h, d in holes.items():
                db_scores[p][h] = d
                
        worksheet.clear()
        worksheet.append_row(["선수명", "홀번호", "점수차"])
        rows = []
        for p, holes in db_scores.items():
            for h, d in holes.items():
                rows.append([p, h, d])
        if rows:
            worksheet.append_rows(rows)
            
        st.session_state.scores = db_scores
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
                "노재호": {"hcap": 21, "dept": "세라믹"},
                "곽재영": {"hcap": 22, "dept": "전자"},
                "박주원": {"hcap": 15, "dept": "전자"}
            }
        },
        "1B조": {
            "start_hole": 1,
            "players": {
                "이용일": {"hcap": 25, "dept": "토목"},
                "신성원": {"hcap": 14, "dept": "전기"},
                "신현경": {"hcap": 17, "dept": "전자"},
                "이창호": {"hcap": 23, "dept": "전기"}
            }
        },
        "2조": {
            "start_hole": 2,
            "players": {
                "마이클 안": {"hcap": 8, "dept": "국제학부"},
                "양진기": {"hcap": "NA", "dept": "전산"},
                "박종화": {"hcap": 10, "dept": "전산"},
                "김택규": {"hcap": 13, "dept": "생화학"}
            }
        },
        "3A조": {
            "start_hole": 3,
            "players": {
                "김은혁": {"hcap": 23, "dept": "의학"},
                "변원석": {"hcap": "NA", "dept": "기계"},
                "임봉욱": {"hcap": 17, "dept": "건축"},
                "이은홍": {"hcap": 25, "dept": "건축"}
            }
        },
        "3B조": {
            "start_hole": 3,
            "players": {
                "남명현": {"hcap": 25, "dept": "수학"},
                "박재효": {"hcap": 34, "dept": "경제"},
                "우규진": {"hcap": 18, "dept": "전자"},
                "이미나": {"hcap": 24, "dept": "영문"}
            }
        },
        "4조": {
            "start_hole": 4,
            "players": {
                "임주연": {"hcap": "NA", "dept": "세라믹"},
                "황경진": {"hcap": "NA", "dept": "금속"},
                "김윤경": {"hcap": 36, "dept": "-"}
            }
        },
        "5A조": {
            "start_hole": 5,
            "players": {
                "이동휘": {"hcap": "NA", "dept": "금속"},
                "양성흠": {"hcap": "NA", "dept": "-"},
                "신재원": {"hcap": "NA", "dept": "전자"},
                "송창걸": {"hcap": 14, "dept": "기계"}
            }
        },
        "5B조": {
            "start_hole": 5,
            "players": {
                "박준식": {"hcap": 11, "dept": "사체"},
                "정태양": {"hcap": "NA", "dept": "스포츠레저"},
                "최성식": {"hcap": 13, "dept": "생명공학"},
                "김용민": {"hcap": 5, "dept": "전기"}
            }
        }
    }

st.title("⛳ 연세대 골프 대회")

# ==========================================
# [모바일 친화적 상단 메뉴바 구성]
# ==========================================
menu = st.radio(
    "메뉴 이동",
    [":material/edit_document: 스코어 입력", ":material/leaderboard: 실시간 리더보드", ":material/settings: 관리"],
    horizontal=True,
    label_visibility="collapsed"
)
st.markdown("---")

# ==========================================
# [메뉴 1] 스코어 입력
# ==========================================
if menu == ":material/edit_document: 스코어 입력":
    
    group_list = list(st.session_state.groups.keys())
    if 'selected_group' not in st.session_state or st.session_state.selected_group not in group_list:
        st.session_state.selected_group = group_list[0]
        
    col_title, col_refresh = st.columns([2, 1])
    with col_title:
        st.header("📝 스코어 입력")
    with col_refresh:
        if st.button("🔄 데이터 갱신"):
            load_scores_from_gsheet()
            st.session_state.auto_jump = True
            st.toast("✅ 최신 데이터를 불러왔습니다!")
            st.rerun()
            
    default_idx = group_list.index(st.session_state.selected_group)
    group_name = st.selectbox("조 선택", group_list, index=default_idx)
    
    if st.session_state.selected_group != group_name:
        st.session_state.selected_group = group_name
        st.session_state.auto_jump = True
        st.rerun()
    
    group_info = st.session_state.groups[group_name]
    start_hole = group_info["start_hole"]
    players_info = group_info["players"]
    
    st.info(f"📌 **{group_name}** | 시작 홀: **{start_hole}번 홀** (샷건 방식)")
    
    hole_sequence = [(start_hole - 1 + i) % 18 + 1 for i in range(18)]
    
    hole_idx_key = f"current_hole_idx_{group_name}"
    
    if hole_idx_key not in st.session_state:
        st.session_state[hole_idx_key] = 0
        st.session_state.auto_jump = True
        
    current_idx = st.session_state[hole_idx_key]
    current_course_hole = hole_sequence[current_idx]
    
    if st.session_state.auto_jump:
        is_current_completed = True
        for p in players_info.keys():
            if p not in st.session_state.scores or current_course_hole not in st.session_state.scores[p]:
                is_current_completed = False
                break
                
        if is_current_completed:
            auto_idx = current_idx
            for idx, h_num in enumerate(hole_sequence):
                comp = True
                for p in players_info.keys():
                    if p not in st.session_state.scores or h_num not in st.session_state.scores[p]:
                        comp = False
                        break
                if not comp:
                    auto_idx = idx
                    break
            else:
                auto_idx = 17 
                
            if current_idx != auto_idx:
                st.session_state[hole_idx_key] = auto_idx
                current_idx = auto_idx
                current_course_hole = hole_sequence[current_idx]
    
    current_par = PAR_LIST[current_course_hole - 1]
    
    col_prev, col_info, col_next = st.columns([1, 2, 1])
    with col_prev:
        if st.button("◀ 이전 홀") and current_idx > 0:
            st.session_state.auto_jump = False 
            st.session_state[hole_idx_key] = current_idx - 1
            st.rerun()
    with col_info:
        st.markdown(f"<div style='text-align: center;'><b>전체 {current_idx + 1}번째 홀</b><br>코스 {current_course_hole}번 (Par {current_par})</div>", unsafe_allow_html=True)
    with col_next:
        if st.button("다음 홀 ▶") and current_idx < 17:
            st.session_state.auto_jump = False
            st.session_state[hole_idx_key] = current_idx + 1
            st.rerun()
            
    st.markdown("---")

    with st.form(key=f"unified_score_form_{group_name}_{current_idx}", clear_on_submit=True):
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
                form_inputs[player] = score_diff
            
        submitted = st.form_submit_button("💾 이 홀의 스코어 저장 및 다음 홀로 ➔")
        if submitted:
            new_inputs = {}
            for player, diff in form_inputs.items():
                new_inputs[player] = {current_course_hole: diff}
            
            success = save_scores_to_gsheet(new_inputs)
            
            if success:
                st.success("✅ 저장 완료! 구글 시트 반영 후 다음 홀로 이동합니다...")
                
                keys_to_delete = [k for k in st.session_state.keys() if k.startswith("input_")]
                for k in keys_to_delete:
                    del st.session_state[k]
                    
                st.session_state[hole_idx_key] = (current_idx + 1) % 18
                st.session_state.auto_jump = True 
                time.sleep(1.2)
                st.rerun()

    st.markdown("---")
    st.markdown(f"
