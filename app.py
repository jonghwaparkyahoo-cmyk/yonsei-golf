import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import gspread
import json
import time
import re
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="연세대 골프 대회 모바일 스코어보드", 
    layout="centered", 
    page_icon="⛳",
    initial_sidebar_state="collapsed"
)

# 15초마다 자동 새로고침
st_autorefresh(interval=15000, key="datarefresh")

# 📱 모바일 UI 완벽 밀착(Fit) CSS
st.markdown("""
<style>
.stSelectbox div[data-baseweb="select"] { min-height: 35px; }
div.row-widget.stRadio > div {
    flex-direction: row; justify-content: space-around;
    background-color: #f0f2f6; padding: 10px; border-radius: 10px;
}

/* 🚨 모바일 환경(폭 640px 이하)에서 가로 스크롤 없이 화면에 100% 딱 맞게 압축 */
@media (max-width: 640px) {
    div[data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        gap: 0.15rem !important; /* 컬럼 사이 여백 최소화 */
    }
    div[data-testid="column"] {
        flex: 1 1 0px !important;
        width: 0 !important;      /* 내용물 크기 무시하고 화면 폭에 강제 맞춤 */
        min-width: 0 !important;
        overflow: hidden !important; /* 튀어나가는 내용 숨김 */
    }
    /* 버튼 뚱뚱한 여백 제거 */
    button[data-testid="baseButton-secondary"] {
        padding: 0.1rem 0.2rem !important;
    }
}
</style>
""", unsafe_allow_html=True)

# --- 필수 세션 상태 초기화 ---
if 'scores' not in st.session_state: st.session_state.scores = {}
if 'auto_jump' not in st.session_state: st.session_state.auto_jump = True
if 'par_list' not in st.session_state: 
    st.session_state.par_list = [4, 4, 3, 4, 5, 4, 3, 5, 4, 4, 3, 5, 4, 3, 5, 4, 4, 4]
if 'groups' not in st.session_state:
    st.session_state.groups = {"1A조": {"start_hole": 1, "players": {"연동대기중": {"hcap": "NA", "dept": "-"}}}}

# 🔑 구글 인증 함수
def get_gspread_client():
    scope1 = "https" + "://" + "www.googleapis.com" + "/auth/spreadsheets"
    scope2 = "https" + "://" + "www.googleapis.com" + "/auth/drive"
    scopes = [scope1, scope2]
    
    creds_dict = json.loads(st.secrets["gcp_json"], strict=False)
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("= ", "=\n").replace("\\n", "\n")
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

# 🎯 마스터 설정에서 현재 활성화된 대회 URL 가져오기
@st.cache_data(ttl=15)
def get_target_url():
    try:
        client = get_gspread_client()
        main_sheet = client.open_by_url(st.secrets["spreadsheet_url"])
        ws = main_sheet.worksheet("AppConfig")
        url = ws.acell('B1').value
        if url and "http" in url: return url
    except: pass
    return st.secrets["spreadsheet_url"]

# 🧠 샷건 여부 및 파(Par) 정보 스마트 스캔
def parse_tournament_settings(sheet):
    is_shotgun = False
    par_list = [4]*18
    
    try:
        ws_mode = sheet.worksheet("대회방식")
        for row in ws_mode.get_all_values():
            for cell in row:
                if "샷건" in str(cell): is_shotgun = True
    except: pass
        
    found_par = False
    for ws_name in ["스코어카드", "대회방식", "Scores"]:
        try:
            ws = sheet.worksheet(ws_name)
            vals = ws.get_all_values()
            
            for row in vals:
                nums = [int(x) for x in row if str(x).strip().isdigit() and 3 <= int(x) <= 6]
                if len(nums) >= 18 and 60 <= sum(nums[:18]) <= 80:
                    par_list = nums[:18]; found_par = True; break
            if found_par: break
            
            if len(vals) > 0:
                for col_idx in range(len(vals[0])):
                    nums = []
                    for row in vals:
                        if col_idx < len(row) and str(row[col_idx]).strip().isdigit():
                            v = int(str(row[col_idx]).strip())
                            if 3 <= v <= 6: nums.append(v)
                    if len(nums) >= 18 and 60 <= sum(nums[:18]) <= 80:
                        par_list = nums[:18]; found_par = True; break
            if found_par: break
        except: continue
        
    return is_shotgun, par_list

# 🧑‍🤝‍🧑 조편성 시트 파싱
def parse_groupings(sheet, is_shotgun):
    try:
        ws = sheet.worksheet("조편성")
        data = ws.get_all_records()
        if not data: return None
        
        df = pd.DataFrame(data)
        df.columns = df.columns.str.strip()
        
        if "조" in df.columns:
            df["조"] = df["조"].replace('', pd.NA).ffill()
            
        new_groups = {}
        for _, row in df.iterrows():
            g_name = str(row.get("조", "")).strip()
            p_name = str(row.get("이름", "")).strip()
            if not g_name or not p_name or g_name.lower() == "nan" or p_name.lower() == "nan": continue
                
            s_hole = 1
            if is_shotgun:
                match = re.search(r'\d+', g_name)
                if match: s_hole = int(match.group())
                
            hcap = row.get("핸디캡", "NA")
            hcap_val = "NA"
            if not pd.isna(hcap) and str(hcap).strip().upper() not in ["NA", ""]:
                try: hcap_val = int(float(hcap))
                except: pass
                
            dept = row.get("학과", "-") if "학과" in df.columns else "-"
                
            if g_name not in new_groups:
                new_groups[g_name] = {"start_hole": s_hole, "players": {}}
            new_groups[g_name]["players"][p_name] = {"hcap": hcap_val, "dept": dept}
        return new_groups
    except: return None

# ⚙️ 대회 설정 정보 캐싱
@st.cache_data(ttl=600)
def get_tournament_config(target_url):
    try:
        client = get_gspread_client()
        sheet = client.open_by_url(target_url)
        is_shotgun, par_list = parse_tournament_settings(sheet)
        groups = parse_groupings(sheet, is_shotgun)
        return par_list, groups
    except: return None, None

# 🔄 전체 대회 상태 로드 엔진
def load_tournament_state():
    target_url = get_target_url()
    
    par_list, groups = get_tournament_config(target_url)
    if par_list: st.session_state.par_list = par_list
    if groups: st.session_state.groups = groups
        
    try:
        client = get_gspread_client()
        sheet = client.open_by_url(target_url)
        try: ws_scores = sheet.worksheet("Scores")
        except gspread.exceptions.WorksheetNotFound:
            ws_scores = sheet.add_worksheet(title="Scores", rows=100, cols=3)
            ws_scores.append_row(["선수명", "홀번호", "점수차"])
            
        data = ws_scores.get_all_records()
        st.session_state.scores = {}
        if data:
            df = pd.DataFrame(data)
            if not df.empty and all(col in df.columns for col in ["선수명", "홀번호", "점수차"]):
                for _, row in df.iterrows():
                    p_name = str(row["선수명"])
                    h_num = int(row["홀번호"])
                    diff_val = int(row["점수차"])
                    if p_name not in st.session_state.scores: st.session_state.scores[p_name] = {}
                    st.session_state.scores[p_name][h_num] = diff_val
    except: pass

load_tournament_state()

# 🚨 스마트 병합(Merge) 저장 로직
def save_scores_to_gsheet(new_scores_dict):
    try:
        client = get_gspread_client()
        target_url = get_target_url()
        sheet = client.open_by_url(target_url)
        
        try: ws_scores = sheet.worksheet("Scores")
        except: ws_scores = sheet.add_worksheet(title="Scores", rows=100, cols=3)
            
        existing_data = ws_scores.get_all_records()
        db_scores = {}
        if existing_data:
            for row in existing_data:
                p = str(row["선수명"]); h = int(row["홀번호"]); d = int(row["점수차"])
                if p not in db_scores: db_scores[p] = {}
                db_scores[p][h] = d
                
        for p, holes in new_scores_dict.items():
            if p not in db_scores: db_scores[p] = {}
            for h, d in holes.items(): db_scores[p][h] = d
                
        ws_scores.clear()
        ws_scores.append_row(["선수명", "홀번호", "점수차"])
        rows = [[p, h, d] for p, holes in db_scores.items() for h, d in holes.items()]
        if rows: ws_scores.append_rows(rows)
            
        st.session_state.scores = db_scores
        return True
    except Exception as e:
        st.error(f"🚨 구글 시트 저장 상세 에러: {e}")
        return False

st.title("⛳ 연세대 골프 대회")

# ==========================================
# [모바일 친화적 상단 메뉴바 구성]
# ==========================================
menu = st.radio(
    "메뉴 이동",
    [":material/edit_document: 스코어 입력", ":material/leaderboard: 실시간 리더보드", ":material/settings: 관리"],
    horizontal=True, label_visibility="collapsed"
)
st.markdown("---")

# ==========================================
# [메뉴 1] 스코어 입력
# ==========================================
if menu == ":material/edit_document: 스코어 입력":
    
    group_list = list(st.session_state.groups.keys())
    if 'selected_group' not in st.session_state or st.session_state.selected_group not in group_list:
        st.session_state.selected_group = group_list[0] if group_list else ""
        
    col_title, col_refresh = st.columns([2, 1])
    with col_title: st.header("📝 스코어 입력")
    with col_refresh:
        if st.button("🔄 데이터 갱신"):
            load_tournament_state()
            st.session_state.auto_jump = True
            st.toast("✅ 최신 데이터를 불러왔습니다!")
            st.rerun()
            
    if not group_list or "연동대기중" in st.session_state.groups.get("1A조", {}).get("players", {}):
        st.warning("👉 관리자 메뉴에서 대회 스프레드시트 URL을 연동해 주세요.")
    else:
        default_idx = group_list.index(st.session_state.selected_group) if st.session_state.selected_group in group_list else 0
        group_name = st.selectbox("조 선택", group_list, index=default_idx)
        
        if st.session_state.selected_group != group_name:
            st.session_state.selected_group = group_name
            st.session_state.auto_jump = True
            st.rerun()
        
        group_info = st.session_state.groups[group_name]
        start_hole = group_info["start_hole"]
        players_info = group_info["players"]
        
        st.info(f"📌 **{group_name}** | 시작 홀: **{start_hole}번 홀**")
        
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
                    is_current_completed = False; break
            if is_current_completed:
                auto_idx = current_idx
                for idx, h_num in enumerate(hole_sequence):
                    comp = True
                    for p in players_info.keys():
                        if p not in st.session_state.scores or h_num not in st.session_state.scores[p]:
                            comp = False; break
                    if not comp: auto_idx = idx; break
                else: auto_idx = 17 
                
                if current_idx != auto_idx:
                    st.session_state[hole_idx_key] = auto_idx
                    current_idx = auto_idx
                    current_course_hole = hole_sequence[current_idx]
        
        current_par = st.session_state.par_list[current_course_hole - 1]
        
        # 🚨 [비율 수정] 가운데 글씨 영역에 공간을 더 배정하여 찌그러짐 최소화
        col_prev, col_info, col_next = st.columns([1, 1.8, 1])
        with col_prev:
            if st.button("◀ 이전") and current_idx > 0:
                st.session_state.auto_jump = False 
                st.session_state[hole_idx_key] = current_idx - 1; st.rerun()
        with col_info:
            # 🚨 [폰트 수정] 모바일에서 절대 잘리지 않도록 폰트 크기 최적화 및 줄바꿈 허용 안함
            st.markdown(f"<div style='text-align: center; font-size: 0.75rem; line-height: 1.3; padding-top: 5px; white-space: nowrap;'><b>{current_idx + 1}번째 진행</b><br>{current_course_hole}번 홀 (Par {current_par})</div>", unsafe_allow_html=True)
        with col_next:
            if st.button("다음 ▶") and current_idx < 17:
                st.session_state.auto_jump = False
                st.session_state[hole_idx_key] = current_idx + 1; st.rerun()
                
        st.markdown("---")

        with st.form(key=f"unified_score_form_{group_name}_{current_idx}", clear_on_submit=True):
            st.markdown(f"#### 🏌️‍♂️ Hole {current_course_hole}, Par {current_par}")
            form_inputs = {}
            for player in players_info.keys():
                if player not in st.session_state.scores: st.session_state.scores[player] = {}
                current_val = st.session_state.scores[player].get(current_course_hole, 0)
                
                options = list(range(-2, current_par + 1))
                if current_val not in options: current_val = 0
                    
                # 🚨 [비율 수정] 선수 이름 영역과 스코어 선택창 비율 재조정
                col_name, col_select = st.columns([1.2, 2.8])
                with col_name: 
                    st.markdown(f"<div style='padding-top: 10px; font-weight: bold; font-size: 0.9rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>{player}</div>", unsafe_allow_html=True)
                with col_select:
                    score_diff = st.selectbox(
                        f"{player} 성적", options=options, index=options.index(current_val) if current_val in options else 2,
                        format_func=lambda x: "이글(-2)" if x==-2 else ("버디(-1)" if x==-1 else ("파(0)" if x==0 else f"+{x}")),
                        key=f"input_{player}_{current_course_hole}", label_visibility="collapsed"
                    )
                    form_inputs[player] = score_diff
                
            if st.form_submit_button("💾 이 홀의 스코어 저장 및 다음 홀로 ➔"):
                new_inputs = {p: {current_course_hole: d} for p, d in form_inputs.items()}
                if save_scores_to_gsheet(new_inputs):
                    st.success("✅ 저장 완료! 다음 홀로 이동합니다...")
                    for k in [k for k in st.session_state.keys() if k.startswith("input_")]: del st.session_state[k]
                    st.session_state[hole_idx_key] = (current_idx + 1) % 18
                    st.session_state.auto_jump = True 
                    time.sleep(1.2); st.rerun()

        st.markdown("---")
        st.markdown(f"📋 **[{group_name} 최근 성적 요약]**")
        start_history_idx = max(0, current_idx - 4)
        history_indices = list(range(start_history_idx, current_idx + 1))
        
        history_table_rows = []
        for player in players_info.keys():
            row_data = {"선수명": player}
            p_scores = st.session_state.scores.get(player, {})
            
            tot_diff = sum(p_scores.values())
            if len(p_scores) > 0:
                tot_str = f"+{tot_diff}" if tot_diff > 0 else (str(tot_diff) if tot_diff < 0 else "E")
            else:
                tot_str = "-"
                
            for idx in history_indices:
                h_num = hole_sequence[idx]
                h_str = f"{h_num}H"
                if h_num in p_scores:
                    diff = p_scores[h_num]
                    row_data[h_str] = "0" if diff==0 else (f"버디({diff})" if diff==-1 else (f"이글({diff})" if diff==-2 else f"+{diff}"))
                else: row_data[h_str] = "-"
                
            row_data["TOT"] = tot_str
            history_table_rows.append(row_data)
            
        if history_table_rows:
            df_history = pd.DataFrame(history_table_rows)
            cols = ["선수명"] + [f"{hole_sequence[idx]}H" for idx in history_indices] + ["TOT"]
            df_history = df_history[cols]
            
            def highlight_tot(col):
                if col.name == 'TOT':
                    return ['background-color: #fff3cd; color: #856404; font-weight: bold;'] * len(col)
                return [''] * len(col)
                
            styled_df = df_history.style.apply(highlight_tot, axis=0)
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
        else: st.caption("아직 기록된 점수가 없습니다.")

# ==========================================
# [메뉴 2] 실시간 리더보드
# ==========================================
elif menu == ":material/leaderboard: 실시간 리더보드":
    col_lb_title, col_lb_refresh = st.columns([2, 1])
    with col_lb_title: st.header("🏆 실시간 리더보드")
    with col_lb_refresh:
        if st.button("🔄 새로고침"):
            load_tournament_state()
            st.toast("✅ 순위표가 업데이트되었습니다!")
            
    st.caption("🔄 구글 시트와 연동되어 실시간으로 15초마다 자동 갱신됩니다.")
    
    leaderboard_data = []
    for group_name, info in st.session_state.groups.items():
        if "연동대기중" in info.get("players", {}): continue
        start_hole = info["start_hole"]
        hole_sequence = [(start_hole - 1 + i) % 18 + 1 for i in range(18)]
        
        for player, p_data in info["players"].items():
            hcap = p_data["hcap"]
            p_scores = st.session_state.scores.get(player, {})
            played_count = len(p_scores)
            
            gross_diff_total = 0
            for h, diff in p_scores.items():
                gross_diff_total += diff
                
            has_hcap = (hcap != "NA")
            
            if played_count > 0 and has_hcap:
                net_val = round(gross_diff_total - int(float(hcap)))
                net_score = str(net_val)
            else: net_score = "-"
                
            if played_count >= 18:
                current_pos = "F"
            else:
                current_pos = str(hole_sequence[played_count])
                
            if played_count > 0:
                gross_str = f"+{gross_diff_total}" if gross_diff_total > 0 else (str(gross_diff_total) if gross_diff_total < 0 else "E")
            else:
                gross_str = "-"
                
            leaderboard_data.append({
                "선수명": player, "핸디캡": str(int(float(hcap))) if has_hcap else "NA",
                "Gross": gross_str, "Net": net_score,
                "시작홀": str(start_hole), "현재위치": current_pos,
                "Sort_HasHcap": 0 if has_hcap else 1, "Sort_Net": float(net_score) if net_score != "-" else 999
            })
            
    df_lb = pd.DataFrame(leaderboard_data)
    if not df_lb.empty:
        df_lb = df_lb.sort_values(by=["Sort_HasHcap", "Sort_Net"], ascending=[True, True])
        df_display = df_lb[["선수명", "핸디캡", "Gross", "Net", "시작홀", "현재위치"]].reset_index(drop=True)
        df_display.index += 1
        st.dataframe(df_display, use_container_width=True)
    else:
        st.info("아직 등록된 성적이 없거나 조편성이 동기화되지 않았습니다.")

# ==========================================
# [메뉴 3] 운영진 관리
# ==========================================
elif menu == ":material/settings: 관리":
    st.header("⚙️ 운영진 전용 관리 패널")
    
    if 'admin_auth' not in st.session_state: st.session_state.admin_auth = False
    CORRECT_PASSWORD = "yonsei2026"
    
    if not st.session_state.admin_auth:
        admin_password = st.text_input("운영진 비밀번호를 입력하세요", type="password")
        if admin_password == CORRECT_PASSWORD:
            st.session_state.admin_auth = True; st.rerun()
        elif admin_password != "": st.error("비밀번호가 틀렸습니다.")
    else:
        st.success("인증 완료. 새로운 대회를 시작하거나 기록을 초기화할 수 있습니다.")
        if st.button("🔒 로그아웃 (잠금)"): st.session_state.admin_auth = False; st.rerun()
            
        st.markdown("---")
        st.subheader("📥 새로운 대회 URL 연동")
        st.info(
            "이곳에 **조편성, 스코어카드, 대회방식** 시트가 작성된 구글 시트 URL을 넣고 동기화하세요.\n\n"
            "이 기기뿐만 아니라 **접속한 모든 사용자의 앱이 즉시 해당 대회로 전환**됩니다!"
        )
        
        current_url = get_target_url()
        new_url = st.text_input("🔗 대회용 구글 시트 URL 복사/붙여넣기", value=current_url)
        
        if st.button("🚀 새 대회로 동기화 및 시작하기"):
            if new_url:
                try:
                    with st.spinner("데이터를 가져오는 중입니다..."):
                        client = get_gspread_client()
                        test_sheet = client.open_by_url(new_url) 
                        
                        master_sheet = client.open_by_url(st.secrets["spreadsheet_url"])
                        try: ws_config = master_sheet.worksheet("AppConfig")
                        except: ws_config = master_sheet.add_worksheet(title="AppConfig", rows=10, cols=2)
                        ws_config.update_acell('A1', 'TargetURL')
                        ws_config.update_acell('B1', new_url)
                        
                        st.cache_data.clear()
                        st.success("✅ 새로운 대회 설정이 완벽하게 연동되었습니다! (새로고침 중...)")
                        time.sleep(2.0); st.rerun()
                except Exception as e:
                    st.error(f"URL 연동 실패. 시트 공유 권한을 확인해주세요. (오류: {e})")
            else: st.warning("URL을 입력해주세요.")

        st.markdown("---")
        st.subheader("🚨 현재 대회 점수 초기화")
        st.warning("현재 연동된 대회의 테스트 점수만 일괄 삭제합니다. (조편성과 파 정보는 그대로 유지됨)")
        
        if st.checkbox("⚠️ 스코어 기록 초기화 동기 확인"):
            if st.button("🗑️ 점수 데이터 전체 초기화 실행"):
                try:
                    client = get_gspread_client()
                    sheet = client.open_by_url(get_target_url())
                    try: ws_scores = sheet.worksheet("Scores")
                    except: ws_scores = sheet.add_worksheet(title="Scores", rows=100, cols=3)
                        
                    ws_scores.clear()
                    ws_scores.append_row(["선수명", "홀번호", "점수차"])
                    st.session_state.scores = {}
                    
                    st.success("✅ 모든 점수 기록이 완벽하게 지워졌습니다! (새로고침 중...)")
                    time.sleep(2.0); st.rerun()
                except Exception as e:
                    st.error(f"초기화 중 오류 발생: {e}")
