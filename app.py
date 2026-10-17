import os
import sqlite3
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# Optional dependency: app can still run without the OpenAI package/key.
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


# ============================================================
# PAGE CONFIG + STYLE
# ============================================================
st.set_page_config(
    page_title="FinMate | Quản lý tài chính cá nhân",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .main .block-container {padding-top: 1.6rem; padding-bottom: 3rem;}
    .hero {
        padding: 1.4rem 1.6rem; border-radius: 18px;
        background: linear-gradient(120deg, #eaf4ff, #f3fff7);
        border: 1px solid #dcebe7; margin-bottom: 1rem;
    }
    .hero h1 {margin: 0; color: #17324d;}
    .hero p {margin: .4rem 0 0 0; color: #38556a;}
    .small-note {font-size: .85rem; color: #64748b;}
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HELPERS
# ============================================================
def vnd(value):
    """Format a number as Vietnamese dong."""
    return f"{value:,.0f} đ".replace(",", ".")


def safe_float(value):
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return 0.0


def init_state():
    defaults = {
        "transactions": [],
        "chat_messages": [],
        "profile": {
            "age_group": "18–22 tuổi",
            "income": 8_000_000,
            "housing": "Thuê trọ",
            "marital": "Độc thân",
            "dependents": 0,
            "housing_cost": 2_500_000,
            "food_cost": 1_800_000,
            "transport_cost": 500_000,
            "bills_cost": 300_000,
            "other_essential": 400_000,
            "debt_payment": 0,
            "current_savings": 0,
            "goal": "Quỹ dự phòng",
            "goal_amount": 10_000_000,
            "goal_months": 12,
            "emergency_months": 3,
        },
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_api_key():
    """Read key from Streamlit secrets first, then environment variable."""
    try:
        key = st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        key = ""
    return key or os.getenv("OPENAI_API_KEY", "")


def get_model_name():
    try:
        model = st.secrets.get("OPENAI_MODEL", "")
    except Exception:
        model = ""
    return model or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


def calculate_budget(profile):
    income = safe_float(profile.get("income", 0))
    housing = safe_float(profile.get("housing_cost", 0))
    food = safe_float(profile.get("food_cost", 0))
    transport = safe_float(profile.get("transport_cost", 0))
    bills = safe_float(profile.get("bills_cost", 0))
    other = safe_float(profile.get("other_essential", 0))
    debt = safe_float(profile.get("debt_payment", 0))

    essentials = housing + food + transport + bills + other
    remaining_after_essentials_and_debt = income - essentials - debt

    # This is a suggested starting target, not a mandatory rule.
    saving_target = min(income * 0.20, max(0, remaining_after_essentials_and_debt))
    flexible = max(0, remaining_after_essentials_and_debt - saving_target)
    deficit = max(0, -remaining_after_essentials_and_debt)

    emergency_months = int(profile.get("emergency_months", 3))
    emergency_target = (essentials + debt) * emergency_months
    current_savings = safe_float(profile.get("current_savings", 0))
    emergency_gap = max(0, emergency_target - current_savings)

    goal_amount = safe_float(profile.get("goal_amount", 0))
    goal_months = max(1, int(profile.get("goal_months", 1)))
    goal_monthly_needed = max(0, goal_amount - current_savings) / goal_months

    return {
        "income": income,
        "housing": housing,
        "food": food,
        "transport": transport,
        "bills": bills,
        "other": other,
        "debt": debt,
        "essentials": essentials,
        "remaining": remaining_after_essentials_and_debt,
        "saving_target": saving_target,
        "flexible": flexible,
        "deficit": deficit,
        "emergency_target": emergency_target,
        "emergency_gap": emergency_gap,
        "goal_amount": goal_amount,
        "goal_months": goal_months,
        "goal_monthly_needed": goal_monthly_needed,
    }


def current_month_transactions():
    items = st.session_state.transactions
    this_month = date.today().strftime("%Y-%m")
    return [
        item for item in items
        if str(item.get("date", "")).startswith(this_month)
    ]


def monthly_spending_by_category():
    txns = current_month_transactions()
    totals = {}
    for item in txns:
        if item.get("kind") == "Chi":
            category = item.get("category", "Khác")
            totals[category] = totals.get(category, 0) + safe_float(item.get("amount", 0))
    return totals


def profile_summary(profile, budget):
    return f"""
HỒ SƠ TÀI CHÍNH DO NGƯỜI DÙNG CUNG CẤP (đơn vị VNĐ):
- Nhóm tuổi: {profile['age_group']}
- Thu nhập thực nhận/tháng: {vnd(budget['income'])}
- Tình trạng nhà ở: {profile['housing']}
- Tình trạng hôn nhân: {profile['marital']}
- Số người phụ thuộc: {profile['dependents']}
- Chi phí nhà ở: {vnd(budget['housing'])}
- Ăn uống: {vnd(budget['food'])}
- Đi lại: {vnd(budget['transport'])}
- Hóa đơn: {vnd(budget['bills'])}
- Chi phí thiết yếu khác: {vnd(budget['other'])}
- Tổng chi phí thiết yếu: {vnd(budget['essentials'])}
- Khoản trả nợ bắt buộc/tháng: {vnd(budget['debt'])}
- Còn lại sau chi phí thiết yếu và khoản trả nợ: {vnd(budget['remaining'])}
- Tiết kiệm hiện có: {vnd(profile['current_savings'])}
- Mục tiêu tài chính: {profile['goal']}
- Mục tiêu số tiền: {vnd(budget['goal_amount'])} trong {budget['goal_months']} tháng
- Mục tiêu tiết kiệm bình quân để đạt mục tiêu: {vnd(budget['goal_monthly_needed'])}/tháng
- Mục tiêu quỹ dự phòng tham khảo: {vnd(budget['emergency_target'])}
- Số tiền còn thiếu so với mục tiêu quỹ dự phòng: {vnd(budget['emergency_gap'])}
Lưu ý: đây là thông tin do người dùng nhập; không được tự giả định là đã xác minh.
""".strip()


def ask_finmate_ai(question, profile, budget, messages):
    if OpenAI is None:
        return "Chưa cài thư viện OpenAI. Hãy chạy: pip install openai"
    api_key = get_api_key()
    if not api_key:
        return (
            "Trợ lý AI chưa được kết nối vì chưa tìm thấy API key. "
            "Hãy cấu hình OPENAI_API_KEY trong .streamlit/secrets.toml "
            "hoặc biến môi trường. Các chức năng ngân sách vẫn sử dụng được."
        )

    client = OpenAI(api_key=api_key)
    model = get_model_name()
    instructions = f"""
Bạn là FinMate AI, trợ lý giáo dục tài chính cá nhân nói tiếng Việt.
Phong cách: thân thiện, rõ ràng, không phán xét, ưu tiên giải pháp thực tế.

PHẠM VI:
- Giải thích lập ngân sách, tiết kiệm, quỹ dự phòng, quản lý chi tiêu,
  lãi suất cơ bản và lập kế hoạch mục tiêu.
- Cá nhân hóa lời giải dựa trên hồ sơ bên dưới khi phù hợp.
- Khi tính toán, nêu công thức, đơn vị, giả định và kết quả.
- Nếu thiếu dữ liệu quan trọng, hỏi lại thay vì bịa số.
- Xem tỷ lệ 50/30/20 là một điểm tham khảo, không phải quy tắc bắt buộc.
- Nếu chi phí và khoản nợ vượt thu nhập, ưu tiên an toàn tài chính,
  nhu cầu thiết yếu và phương án điều chỉnh khả thi.
- Không cam kết lợi nhuận, không giả danh chuyên gia được cấp phép,
  không đưa ra khuyến nghị mua/bán chứng khoán hoặc sản phẩm đầu tư cụ thể.
- Không yêu cầu mật khẩu, mã OTP, số thẻ hoặc thông tin đăng nhập ngân hàng.
- Không thực hiện giao dịch, chuyển tiền hay hành động thay người dùng.
- Nếu câu hỏi nằm ngoài phạm vi tài chính cá nhân, trả lời ngắn gọn
  trong khả năng hoặc nói rõ giới hạn.
- Không lặp lại thông tin nhạy cảm nếu không cần thiết.

BỐI CẢNH TÀI CHÍNH:
{profile_summary(profile, budget)}

Hãy trả lời dễ hiểu, có thể dùng gạch đầu dòng và đưa ra bước tiếp theo cụ thể.
""".strip()

    # Send only a limited recent conversation history.
    input_messages = []
    for msg in messages[-10:]:
        if msg.get("role") in ("user", "assistant"):
            input_messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })

    response = client.responses.create(
        model=model,
        instructions=instructions,
        input=input_messages,
    )
    return (response.output_text or "").strip() or "AI chưa tạo được câu trả lời. Bà thử hỏi lại nhé."


# ============================================================
# INITIALIZE APP STATE
# ============================================================
init_state()
profile = st.session_state.profile
budget = calculate_budget(profile)


# ============================================================
# SIDEBAR: PERSONAL PROFILE
# ============================================================
with st.sidebar:
    st.markdown("## 💰 FinMate")
    st.caption("Trợ lý quản lý tài chính cá nhân")
    st.divider()
    st.subheader("Hồ sơ tài chính")

    with st.form("profile_form"):
        age_group = st.selectbox(
            "Nhóm tuổi",
            ["Dưới 18 tuổi", "18–22 tuổi", "23–30 tuổi", "31–45 tuổi", "Trên 45 tuổi"],
            index=["Dưới 18 tuổi", "18–22 tuổi", "23–30 tuổi", "31–45 tuổi", "Trên 45 tuổi"].index(profile["age_group"])
            if profile["age_group"] in ["Dưới 18 tuổi", "18–22 tuổi", "23–30 tuổi", "31–45 tuổi", "Trên 45 tuổi"]
            else 1,
        )
        income = st.number_input(
            "Thu nhập thực nhận/tháng (VNĐ)",
            min_value=0, step=500_000, value=int(profile["income"]),
        )
        housing = st.selectbox(
            "Tình trạng nhà ở",
            ["Sống cùng gia đình", "Thuê trọ", "Nhà riêng", "Trả góp nhà"],
            index=["Sống cùng gia đình", "Thuê trọ", "Nhà riêng", "Trả góp nhà"].index(profile["housing"])
            if profile["housing"] in ["Sống cùng gia đình", "Thuê trọ", "Nhà riêng", "Trả góp nhà"]
            else 1,
        )
        marital = st.selectbox(
            "Tình trạng hôn nhân",
            ["Độc thân", "Đã kết hôn", "Khác / không muốn trả lời"],
            index=["Độc thân", "Đã kết hôn", "Khác / không muốn trả lời"].index(profile["marital"])
            if profile["marital"] in ["Độc thân", "Đã kết hôn", "Khác / không muốn trả lời"]
            else 0,
        )
        dependents = st.number_input(
            "Số người phụ thuộc tài chính",
            min_value=0, max_value=30, step=1, value=int(profile["dependents"]),
        )
        st.markdown("**Chi phí hàng tháng**")
        housing_cost = st.number_input("Nhà ở (VNĐ)", min_value=0, step=100_000, value=int(profile["housing_cost"]))
        food_cost = st.number_input("Ăn uống (VNĐ)", min_value=0, step=100_000, value=int(profile["food_cost"]))
        transport_cost = st.number_input("Đi lại (VNĐ)", min_value=0, step=100_000, value=int(profile["transport_cost"]))
        bills_cost = st.number_input("Điện, nước, điện thoại... (VNĐ)", min_value=0, step=100_000, value=int(profile["bills_cost"]))
        other_essential = st.number_input("Thiết yếu khác (VNĐ)", min_value=0, step=100_000, value=int(profile["other_essential"]))
        debt_payment = st.number_input("Trả nợ bắt buộc/tháng (VNĐ)", min_value=0, step=100_000, value=int(profile["debt_payment"]))
        current_savings = st.number_input("Tiết kiệm hiện có (VNĐ)", min_value=0, step=500_000, value=int(profile["current_savings"]))

        st.markdown("**Mục tiêu tài chính**")
        goal = st.selectbox(
            "Mục tiêu ưu tiên",
            ["Quỹ dự phòng", "Học tập / chứng chỉ", "Mua sắm mục tiêu lớn", "Trả nợ", "Tích lũy dài hạn"],
            index=["Quỹ dự phòng", "Học tập / chứng chỉ", "Mua sắm mục tiêu lớn", "Trả nợ", "Tích lũy dài hạn"].index(profile["goal"])
            if profile["goal"] in ["Quỹ dự phòng", "Học tập / chứng chỉ", "Mua sắm mục tiêu lớn", "Trả nợ", "Tích lũy dài hạn"]
            else 0,
        )
        goal_amount = st.number_input("Số tiền mục tiêu (VNĐ)", min_value=0, step=500_000, value=int(profile["goal_amount"]))
        goal_months = st.number_input("Số tháng để đạt mục tiêu", min_value=1, max_value=600, step=1, value=int(profile["goal_months"]))
        emergency_months = st.selectbox(
            "Quỹ dự phòng mục tiêu (số tháng chi phí)",
            [1, 3, 6, 9, 12],
            index=[1, 3, 6, 9, 12].index(int(profile["emergency_months"]))
            if int(profile["emergency_months"]) in [1, 3, 6, 9, 12]
            else 1,
        )

        saved = st.form_submit_button("Lưu hồ sơ và cập nhật", use_container_width=True)

    if saved:
        st.session_state.profile = {
            "age_group": age_group,
            "income": income,
            "housing": housing,
            "marital": marital,
            "dependents": dependents,
            "housing_cost": housing_cost,
            "food_cost": food_cost,
            "transport_cost": transport_cost,
            "bills_cost": bills_cost,
            "other_essential": other_essential,
            "debt_payment": debt_payment,
            "current_savings": current_savings,
            "goal": goal,
            "goal_amount": goal_amount,
            "goal_months": goal_months,
            "emergency_months": emergency_months,
        }
        st.success("Đã cập nhật hồ sơ.")
        st.rerun()

    st.divider()
    st.caption("Bản mẫu lưu hồ sơ trong phiên làm việc hiện tại. Không nhập thông tin đăng nhập ngân hàng.")


# Refresh latest profile after sidebar form handling
profile = st.session_state.profile
budget = calculate_budget(profile)


# ============================================================
# HEADER
# ============================================================
st.markdown(
    """
    <div class="hero">
      <h1>FinMate</h1>
      <p>Hiểu dòng tiền của bạn. Lập kế hoạch phù hợp. Từng bước đạt mục tiêu tài chính.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

dashboard_tab, transactions_tab, ai_tab, guide_tab = st.tabs(
    ["📊 Tổng quan", "🧾 Thu chi", "🤖 FinMate AI", "📘 Hướng dẫn"]
)


# ============================================================
# TAB 1: DASHBOARD
# ============================================================
with dashboard_tab:
    st.subheader("Tổng quan tài chính tháng")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Thu nhập/tháng", vnd(budget["income"]))
    c2.metric("Chi phí thiết yếu", vnd(budget["essentials"]))
    c3.metric("Trả nợ bắt buộc", vnd(budget["debt"]))
    c4.metric("Còn lại", vnd(budget["remaining"]))

    if budget["income"] <= 0:
        st.warning("Bạn chưa nhập thu nhập. Hãy cập nhật hồ sơ ở thanh bên.")
    elif budget["deficit"] > 0:
        st.error(
            f"Chi phí thiết yếu và trả nợ đang vượt thu nhập {vnd(budget['deficit'])}/tháng. "
            "Chưa nên đặt mục tiêu tiết kiệm cố định. Hãy rà soát khoản chi có thể giảm, "
            "nghĩa vụ nợ và khả năng tăng thu nhập."
        )
    else:
        st.success(
            f"Mục tiêu tiết kiệm tham khảo: {vnd(budget['saving_target'])}/tháng. "
            "Đây là mức khởi điểm, có thể điều chỉnh theo hoàn cảnh."
        )

    left, right = st.columns([1.1, 1])
    with left:
        st.markdown("#### Ngân sách gợi ý")
        budget_rows = [
            ("Nhà ở", budget["housing"]),
            ("Ăn uống", budget["food"]),
            ("Đi lại", budget["transport"]),
            ("Hóa đơn", budget["bills"]),
            ("Thiết yếu khác", budget["other"]),
            ("Trả nợ bắt buộc", budget["debt"]),
            ("Tiết kiệm gợi ý", budget["saving_target"]),
            ("Chi tiêu linh hoạt còn lại", budget["flexible"]),
        ]
        df_budget = pd.DataFrame(budget_rows, columns=["Khoản mục", "Số tiền (VNĐ)"])
        st.dataframe(df_budget, use_container_width=True, hide_index=True)
    with right:
        st.markdown("#### Phân bổ dòng tiền")
        chart_df = pd.DataFrame(
            {
                "Khoản mục": ["Thiết yếu", "Trả nợ", "Tiết kiệm", "Linh hoạt"],
                "Số tiền": [
                    budget["essentials"],
                    budget["debt"],
                    budget["saving_target"],
                    budget["flexible"],
                ],
            }
        )
        chart_df = chart_df[chart_df["Số tiền"] > 0]
        if not chart_df.empty:
            st.bar_chart(chart_df.set_index("Khoản mục"))
        else:
            st.info("Nhập thu nhập và chi phí để xem biểu đồ.")

    st.markdown("#### Mục tiêu tài chính")
    g1, g2, g3 = st.columns(3)
    g1.metric("Mục tiêu", profile["goal"])
    g2.metric("Số tiền cần tích lũy", vnd(budget["goal_amount"]))
    g3.metric("Cần dành ra bình quân", f"{vnd(budget['goal_monthly_needed'])}/tháng")

    if budget["goal_monthly_needed"] > max(0, budget["remaining"]):
        st.warning(
            "Mục tiêu hiện tại có thể vượt khả năng ngân sách. "
            "Bạn có thể kéo dài thời hạn, giảm số tiền mục tiêu hoặc rà soát lại chi phí."
        )

    st.markdown("#### Quỹ dự phòng")
    q1, q2 = st.columns(2)
    q1.metric("Mục tiêu quỹ dự phòng", vnd(budget["emergency_target"]))
    q2.metric("Còn thiếu so với mục tiêu", vnd(budget["emergency_gap"]))
    st.caption(
        "Quỹ dự phòng là mục tiêu tham khảo dựa trên số tháng chi phí thiết yếu và trả nợ. "
        "Hãy điều chỉnh theo độ ổn định thu nhập và trách nhiệm gia đình."
    )

    spent_by_category = monthly_spending_by_category()
    if spent_by_category:
        st.markdown("#### Chi tiêu đã ghi nhận trong tháng")
        tx_df = pd.DataFrame(
            [{"Danh mục": k, "Đã chi (VNĐ)": v} for k, v in spent_by_category.items()]
        )
        st.dataframe(tx_df, use_container_width=True, hide_index=True)
        st.metric("Tổng chi đã ghi nhận", vnd(sum(spent_by_category.values())))


# ============================================================
# TAB 2: TRANSACTIONS
# ============================================================
with transactions_tab:
    st.subheader("Ghi nhận thu chi")
    st.write("Thêm khoản thu hoặc chi để theo dõi trong phiên sử dụng hiện tại.")

    with st.form("transaction_form", clear_on_submit=True):
        t1, t2, t3 = st.columns(3)
        with t1:
            tx_date = st.date_input("Ngày giao dịch", value=date.today())
            tx_kind = st.selectbox("Loại giao dịch", ["Chi", "Thu"])
        with t2:
            tx_category = st.selectbox(
                "Danh mục",
                ["Nhà ở", "Ăn uống", "Đi lại", "Hóa đơn", "Học tập",
                 "Sức khỏe", "Giải trí", "Mua sắm", "Lương/thu nhập",
                 "Thưởng", "Trả nợ", "Tiết kiệm", "Khác"],
            )
            tx_amount = st.number_input("Số tiền (VNĐ)", min_value=0, step=10_000, value=0)
        with t3:
            tx_note = st.text_input("Ghi chú (không bắt buộc)", max_chars=120)

        add_tx = st.form_submit_button("Thêm giao dịch", use_container_width=True)

    if add_tx:
        if tx_amount <= 0:
            st.error("Số tiền phải lớn hơn 0.")
        else:
            st.session_state.transactions.append(
                {
                    "date": tx_date.isoformat(),
                    "kind": tx_kind,
                    "category": tx_category,
                    "amount": float(tx_amount),
                    "note": tx_note.strip(),
                }
            )
            st.success("Đã thêm giao dịch.")
            st.rerun()

    if st.session_state.transactions:
        st.markdown("#### Lịch sử giao dịch")
        tx_df = pd.DataFrame(st.session_state.transactions)
        tx_df = tx_df.rename(
            columns={
                "date": "Ngày",
                "kind": "Loại",
                "category": "Danh mục",
                "amount": "Số tiền (VNĐ)",
                "note": "Ghi chú",
            }
        )
        st.dataframe(tx_df.sort_values("Ngày", ascending=False), use_container_width=True, hide_index=True)
        csv_data = tx_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "Tải lịch sử giao dịch CSV",
            data=csv_data,
            file_name="finmate_giao_dich.csv",
            mime="text/csv",
        )
        if st.button("Xóa toàn bộ lịch sử giao dịch trong phiên", type="secondary"):
            st.session_state.transactions = []
            st.rerun()
    else:
        st.info("Chưa có giao dịch nào. Hãy thêm khoản thu hoặc chi đầu tiên.")


# ============================================================
# TAB 3: AI CHAT
# ============================================================
with ai_tab:
    st.subheader("Trò chuyện cùng FinMate AI")
    st.write(
        "Hỏi về ngân sách, tiết kiệm, quỹ dự phòng, quản lý nợ hoặc mục tiêu tài chính. "
        "AI sẽ dùng hồ sơ hiện tại làm bối cảnh khi phù hợp."
    )

    with st.expander("Gợi ý câu hỏi"):
        suggestions = [
            "Với ngân sách hiện tại, tôi có thể tiết kiệm thêm ở đâu?",
            "Làm sao để đạt mục tiêu tài chính đúng thời hạn?",
            "Giải thích quy tắc 50/30/20 và xem có phù hợp với tôi không.",
            "Tôi nên bắt đầu xây dựng quỹ dự phòng như thế nào?",
            "Hãy giúp tôi lập kế hoạch chi tiêu trong tháng tới.",
        ]
        for suggestion in suggestions:
            st.markdown(f"- {suggestion}")

    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Nhập câu hỏi của bạn...", key="finmate_chat_input")
    if prompt:
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("FinMate AI đang trả lời..."):
                try:
                    answer = ask_finmate_ai(
                        question=prompt,
                        profile=profile,
                        budget=budget,
                        messages=st.session_state.chat_messages,
                    )
                except Exception as exc:
                    # Do not expose secret keys or full internal details to the user.
                    answer = (
                        "Hiện chưa thể kết nối AI. Hãy kiểm tra API key, tên model, "
                        "kết nối mạng và hạn mức API rồi thử lại. "
                        f"Chi tiết lỗi: {type(exc).__name__}"
                    )
                st.markdown(answer)

        st.session_state.chat_messages.append(
            {"role": "assistant", "content": answer}
        )

    chat_col1, chat_col2 = st.columns(2)
    with chat_col1:
        if st.button("Xóa hội thoại AI", use_container_width=True):
            st.session_state.chat_messages = []
            st.rerun()
    with chat_col2:
        st.caption(f"Model cấu hình: {get_model_name()}")


# ============================================================
# TAB 4: GUIDE + DISCLAIMER
# ============================================================
with guide_tab:
    st.subheader("Cách sử dụng FinMate")
    st.markdown(
        """
        1. Mở thanh bên trái và nhập hồ sơ tài chính.
        2. Nhấn **Lưu hồ sơ và cập nhật**.
        3. Xem bảng ngân sách, mục tiêu tiết kiệm và quỹ dự phòng ở tab **Tổng quan**.
        4. Thêm các giao dịch thực tế trong tab **Thu chi**.
        5. Đặt câu hỏi trong tab **FinMate AI** để nhận giải thích và gợi ý.
        """
    )
    st.warning(
        "FinMate cung cấp thông tin giáo dục và lập kế hoạch tham khảo, không thay thế "
        "tư vấn tài chính chuyên nghiệp. Hãy kiểm tra lại số liệu trước khi quyết định."
    )
    st.markdown("#### Lưu ý về dữ liệu")
    st.markdown(
        """
        - Bản mẫu này lưu hồ sơ, giao dịch và hội thoại trong phiên Streamlit hiện tại;
        dữ liệu có thể mất khi phiên bị khởi động lại.
        - Khi hỏi AI, hồ sơ tài chính đã nhập và một phần hội thoại gần đây được gửi đến API
        để tạo câu trả lời.
        - Không nhập mật khẩu, OTP, số thẻ hoặc thông tin đăng nhập ngân hàng.
        - Nếu triển khai cho nhiều khách hàng, cần bổ sung đăng nhập, cơ sở dữ liệu phù hợp, "
        phân quyền, chính sách bảo mật và thông báo quyền riêng tư.
        """
    )
    st.markdown(
        "[Tài liệu OpenAI API](https://platform.openai.com/docs/quickstart) · "
        "[Tài liệu Streamlit Chat](https://docs.streamlit.io/develop/api-reference/chat)"
    )
