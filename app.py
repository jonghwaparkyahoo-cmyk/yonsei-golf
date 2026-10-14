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
    st.markdown(f"📋 **[{group_name} 최근 성적 요약]**")
    
    start_history_idx = max(0, current_idx - 4)
    history_indices = list(range(start_history_idx, current_idx + 1))
    
    history_table_rows = []
    for player in players_info.keys():
        row_data = {"선수명": player}
        p_scores = st.session_state.scores.get(player, {})
        for idx in history_indices:
            h_num = hole_sequence[idx]
            h_str = f"{h_num}H"
            if h_num in p_scores:
                diff = p_scores[h_num]
                row_data[h_str] = "0" if diff==0 else (f"버디({diff})" if diff==-1 else (f"이글({diff})" if diff==-2 else f"+{diff}"))
            else:
                row_data[h_str] = "-"
        history_table_rows.append(row_data)
        
    if history_table_rows:
        df_history = pd.DataFrame(history_table_rows)
        cols = ["선수명"] + [f"{hole_sequence[idx]}H" for idx in history_indices]
        df_history = df_history[cols]
        st.dataframe(df_history, use_container_width=True, hide_index=True)
    else:
        st.caption("아직 기록된 점수가 없습니다.")

# ==========================================
# [메뉴 2] 실시간 리더보드
# ==========================================
elif menu == ":material/leaderboard: 실시간 리더보드":
    
    col_lb_title, col_lb_refresh = st.columns([2, 1])
    with col_lb_title:
        st.header("🏆 실시간 리더보드")
    with col_lb_refresh:
        if st.button("🔄 새로고침"):
            load_scores_from_gsheet()
            st.toast("✅ 순위표가 업데이트되었습니다!")
            
    st.caption("🔄 구글 시트와 연동되어 실시간으로 15초마다 자동 갱신됩니다.")
    
    leaderboard_data = []
    for group_name, info in st.session_state.groups.items():
        start_hole = info["start_hole"]
        hole_sequence = [(start_hole - 1 + i) % 18 + 1 for i in range(18)]
        
        for player, p_data in info["players"].items():
            hcap = p_data["hcap"]
            p_scores = st.session_state.scores.get(player, {})
            played_count = len(p_scores)
            
            gross_total = 0
            for h, diff in p_scores.items():
                gross_total += (PAR_LIST[h-1] + diff)
                
            has_hcap = (hcap != "NA")
            
            if played_count > 0 and has_hcap:
                net_val = round(gross_total - int(float(hcap)))
                net_score = str(net_val)
            else:
                net_score = "-"
                
            if has_hcap:
                display_hcap = str(int(float(hcap)))
            else:
                display_hcap = "NA"
                
            if played_count == 0:
                current_pos = "0"
            elif played_count >= 18:
                current_pos = "F"
            else:
                last_played_idx = played_count - 1
                current_pos = str(hole_sequence[last_played_idx])
                
            leaderboard_data.append({
                "선수명": player,
                "핸디캡": display_hcap,
                "Gross": str(gross_total) if played_count > 0 else "-",
                "Net": net_score,
                "시작홀": str(start_hole),
                "현재위치": current_pos,
                "Sort_HasHcap": 0 if has_hcap else 1,
                "Sort_Net": float(net_score) if net_score != "-" else 999
            })
            
    df_lb = pd.DataFrame(leaderboard_data)
    if not df_lb.empty:
        df_lb = df_lb.sort_values(by=["Sort_HasHcap", "Sort_Net"], ascending=[True, True])
        df_display = df_lb[["선수명", "핸디캡", "Gross", "Net", "시작홀", "현재위치"]].reset_index(drop=True)
        df_display.index += 1
        st.dataframe(df_display, use_container_width=True)
    else:
        st.info("아직 등록된 성적이 없습니다.")

# ==========================================
# [메뉴 3] 운영진 관리
# ==========================================
elif menu == ":material/settings: 관리":
    st.header("⚙️ 운영진 전용 관리 패널")
    
    if 'admin_auth' not in st.session_state:
        st.session_state.admin_auth = False
        
    CORRECT_PASSWORD = "yonsei2026"
    
    if not st.session_state.admin_auth:
        admin_password = st.text_input("운영진 비밀번호를 입력하세요", type="password")
        if admin_password == CORRECT_PASSWORD:
            st.session_state.admin_auth = True
            st.rerun()
        elif admin_password != "":
            st.error("비밀번호가 틀렸습니다.")
    else:
        st.success("인증되었습니다. 당일 조편성 및 스코어 데이터를 관리할 수 있습니다.")
        if st.button("🔒 로그아웃 (잠금)"):
            st.session_state.admin_auth = False
            st.rerun()
            
        st.markdown("---")
        
        st.subheader("🚨 경기 전 데이터 초기화")
        st.warning("대회 시작 전 테스트로 입력된 모든 점수 기록을 구글 시트에서 일괄 삭제합니다.")
        
        confirm_reset = st.checkbox("⚠️ 모든 스코어 기록을 삭제하는 것에 동의합니다 (초기화 활성화)")
        if confirm_reset:
            if st.button("🗑️ 구글 시트 포함 전체 스코어 초기화 실행"):
                try:
                    client = get_gspread_client()
                    sheet = client.open_by_url(st.secrets["spreadsheet_url"])
                    worksheet = sheet.worksheet("Scores")
                    worksheet.clear()
                    worksheet.append_row(["선수명", "홀번호", "점수차"])
                    
                    st.session_state.scores = {}
                    
                    st.success("✅ 모든 스코어 기록이 완벽하게 초기화되었습니다! (새로고침 중...)")
                    time.sleep(2.0)
                    st.rerun()
                except Exception as e:
                    st.error(f"초기화 중 오류 발생: {e}")
        else:
            st.button("🗑️ 구글 시트 포함 전체 스코어 초기화 실행", disabled=True)
            
        st.markdown("---")
        st.subheader("📋 조편성 및 선수 명단 관리")
        
        groups_to_delete = []
        for group_name, info in list(st.session_state.groups.items()):
            with st.expander(f"조: {group_name} (시작홀: {info['start_hole']}번)"):
                new_start_hole = st.number_input(f"시작 홀 변경 ({group_name})", min_value=1, max_value=18, value=int(info['start_hole']), key=f"sh_{group_name}")
                st.session_state.groups[group_name]['start_hole'] = new_start_hole
                
                st.markdown("**소속 선수 및 핸디캡 수정**")
                players_to_delete = []
                for player, p_val in list(info['players'].items()):
                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        new_name = st.text_input("선수명", value=player, key=f"pname_{group_name}_{player}")
                    with col2:
                        h_val_str = str(int(float(p_val['hcap']))) if p_val['hcap'] != "NA" else "NA"
                        new_hcap = st.text_input("핸디캡 (숫자 또는 NA)", value=h_val_str, key=f"phcap_{group_name}_{player}")
                    with col3:
                        if st.button("삭제", key=f"del_p_{group_name}_{player}"):
                            players_to_delete.append(player)
                            
                    if new_name != player and new_name not in st.session_state.groups[group_name]['players']:
                        st.session_state.groups[group_name]['players'][new_name] = st.session_state.groups[group_name]['players'].pop(player)
                        player = new_name
                    
                    try:
                        if new_hcap.upper() == "NA":
                            st.session_state.groups[group_name]['players'][player]['hcap'] = "NA"
                        else:
                            st.session_state.groups[group_name]['players'][player]['hcap'] = int(float(new_hcap))
                    except ValueError:
                        pass
                        
                for p in players_to_delete:
                    del st.session_state.groups[group_name]['players'][p]
                    st.rerun()
                    
                with st.form(key=f"add_player_{group_name}"):
                    col_ap1, col_ap2, col_ap3, col_ap4 = st.columns([2, 1.5, 1.5, 1])
                    with col_ap1:
                        add_name = st.text_input("선수명")
                    with col_ap2:
                        add_dept = st.text_input("소속", value="-")
                    with col_ap3:
                        add_hcap = st.text_input("핸디캡", value="NA")
                    with col_ap4:
                        add_btn = st.form_submit_button("추가")
                    if add_btn and add_name:
                        try:
                            h_val = int(float(add_hcap)) if add_hcap.upper() != "NA" else "NA"
                        except ValueError:
                            h_val = "NA"
                        st.session_state.groups[group_name]['players'][add_name] = {"hcap": h_val, "dept": add_dept}
                        st.success(f"{add_name} 선수 추가 완료!")
                        st.rerun()
                        
                if st.button(f"🗑️ '{group_name}' 조 전체 삭제", key=f"del_g_{group_name}"):
                    groups_to_delete.append(group_name)
                    
        for g in groups_to_delete:
            del st.session_state.groups[g]
            st.rerun()
            
        st.markdown("---")
        st.subheader("➕ 새 조 추가하기")
        with st.form(key="add_group_form"):
            new_g_name = st.text_input("새 조 이름 (예: 6A조)")
            new_g_start = st.number_input("시작 홀", min_value=1, max_value=18, value=1)
            add_g_btn = st.form_submit_button("조 생성하기")
            if add_g_btn and new_g_name:
                if new_g_name not in st.session_state.groups:
                    st.session_state.groups[new_g_name] = {"start_hole": int(new_g_start), "players": {}}
                    st.success(f"'{new_g_name}' 조가 생성되었습니다!")
                    st.rerun()
                else:
                    st.error("이미 존재하는 조 이름입니다.")
