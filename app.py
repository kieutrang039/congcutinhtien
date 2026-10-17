import streamlit as st
from openai import OpenAI

# Khởi tạo AI
client = OpenAI(
    api_key=st.secrets["OPENAI_API_KEY"]
)

st.header("🤖 FinMate AI")
st.write(
    "Xin chào! Tôi có thể giúp bạn lập ngân sách, "
    "tiết kiệm và giải đáp các câu hỏi tài chính cá nhân."
)

# Hồ sơ tài chính mẫu.
# Khi tích hợp vào app chính, thay các giá trị này
# bằng dữ liệu hồ sơ thực tế của người dùng.
income = 8_000_000
housing_cost = 2_500_000
essential_cost = 2_700_000
monthly_debt = 0
financial_goal = "Xây dựng quỹ dự phòng"

profile = f"""
Thu nhập hàng tháng: {income:,} VNĐ.
Chi phí nhà ở: {housing_cost:,} VNĐ.
Các chi phí thiết yếu khác: {essential_cost:,} VNĐ.
Khoản trả nợ hàng tháng: {monthly_debt:,} VNĐ.
Mục tiêu tài chính: {financial_goal}.
Đây là hồ sơ mẫu dùng để minh họa.
"""

# Lịch sử hội thoại trong phiên hiện tại
if "finmate_messages" not in st.session_state:
    st.session_state.finmate_messages = []

# Hiển thị hội thoại cũ
for message in st.session_state.finmate_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Ô nhập câu hỏi
question = st.chat_input(
    "Ví dụ: Làm sao tiết kiệm 10 triệu trong 6 tháng?"
)

if question:
    st.session_state.finmate_messages.append({
        "role": "user",
        "content": question
    })

    with st.chat_message("user"):
        st.markdown(question)

    instructions = f"""
Bạn là FinMate AI, trợ lý giáo dục tài chính cá nhân.

NHIỆM VỤ:
- Trả lời bằng tiếng Việt thân thiện, dễ hiểu.
- Giúp lập ngân sách, tiết kiệm, theo dõi chi tiêu,
  giải thích kiến thức tài chính và so sánh phương án.
- Cá nhân hóa câu trả lời dựa trên hồ sơ được cung cấp.
- Nếu thiếu dữ liệu, hãy hỏi lại thay vì tự bịa số liệu.
- Khi tính toán, trình bày công thức và giả định.
- Không khẳng định tỷ lệ 50/30/20 phù hợp với tất cả mọi người.
- Không cam kết lợi nhuận hoặc khuyến nghị đầu tư
  cá nhân hóa vượt quá phạm vi hỗ trợ của bạn.
- Nếu người dùng có dấu hiệu khó trả nợ,
  hãy ưu tiên nghĩa vụ thiết yếu và phương án an toàn.
- Không yêu cầu mật khẩu, mã OTP hay thông tin đăng nhập ngân hàng.
- Nhắc người dùng kiểm tra các giả định quan trọng.

HỒ SƠ TÀI CHÍNH:
{profile}

Chỉ sử dụng hồ sơ này cho câu hỏi hiện tại.
Không mặc định hồ sơ mẫu là dữ liệu thật của khách hàng.
"""

    with st.chat_message("assistant"):
        with st.spinner("FinMate AI đang suy nghĩ..."):
            try:
                # Gửi lịch sử hội thoại gần đây
                recent_messages = (
                    st.session_state.finmate_messages[-10:]
                )

                response = client.responses.create(
                    model="gpt-4.1-mini",
                    instructions=instructions,
                    input=recent_messages
                )

                answer = response.output_text
                st.markdown(answer)

            except Exception:
                answer = (
                    "Xin lỗi, hiện chưa thể kết nối trợ lý AI. "
                    "Bạn hãy thử lại sau."
                )
                st.error(answer)

    st.session_state.finmate_messages.append({
        "role": "assistant",
        "content": answer
import pandas as pd

st.set_page_config(
    page_title="FinMate - Quản lý tài chính",
    page_icon="💰",
    layout="wide"
)

st.title("💰 FINMATE")
st.subheader("Trợ lý quản lý tài chính cá nhân")
st.write(
    "Lập ngân sách phù hợp với thu nhập, "
    "chi phí và mục tiêu của bạn."
)

st.header("1. Hồ sơ tài chính")

col1, col2 = st.columns(2)

with col1:
    age = st.selectbox(
        "Nhóm tuổi",
        ["Dưới 18", "18–22", "23–30", "31–45", "Trên 45"]
    )

    income = st.number_input(
        "Thu nhập thực nhận/tháng (VNĐ)",
        min_value=0,
        value=8000000,
        step=500000
    )

    housing = st.selectbox(
        "Tình trạng nhà ở",
        ["Sống cùng gia đình", "Thuê trọ",
         "Nhà riêng", "Trả góp nhà"]
    )

with col2:
    family = st.selectbox(
        "Tình trạng hôn nhân",
        ["Độc thân", "Đã kết hôn"]
    )

    dependents = st.number_input(
        "Số người phụ thuộc",
        min_value=0,
        value=0,
        step=1
    )

    goal = st.selectbox(
        "Mục tiêu tài chính",
        ["Quỹ dự phòng", "Học tập",
         "Mua sắm mục tiêu lớn",
         "Trả nợ", "Tích lũy dài hạn"]
    )

st.header("2. Chi phí thực tế")

col3, col4 = st.columns(2)

with col3:
    housing_cost = st.number_input(
        "Chi phí nhà ở/tháng",
        min_value=0,
        value=2500000,
        step=100000
    )

    food = st.number_input(
        "Ăn uống/tháng",
        min_value=0,
        value=1800000,
        step=100000
    )

    transport = st.number_input(
        "Đi lại/tháng",
        min_value=0,
        value=500000,
        step=100000
    )

with col4:
    bills = st.number_input(
        "Điện, nước, điện thoại...",
        min_value=0,
        value=300000,
        step=100000
    )

    debt = st.number_input(
        "Khoản trả nợ bắt buộc/tháng",
        min_value=0,
        value=0,
        step=100000
    )

    other = st.number_input(
        "Chi phí thiết yếu khác",
        min_value=0,
        value=400000,
        step=100000
    )

st.header("3. Kết quả đề xuất")

if st.button("Phân tích tài chính", type="primary"):

    essential = (
        housing_cost + food + transport
        + bills + other
    )

    available = income - essential - debt

    st.subheader("Tổng quan")

    c1, c2, c3 = st.columns(3)
    c1.metric("Thu nhập", f"{income:,.0f} đ")
    c2.metric("Chi phí thiết yếu", f"{essential:,.0f} đ")
    c3.metric("Còn lại sau chi phí và nợ",
              f"{available:,.0f} đ")

    if income == 0:
        st.error(
            "Chưa có thu nhập. Hãy nhập thu nhập "
            "hoặc xây dựng kế hoạch chi tiêu riêng."
        )

    elif available < 0:
        st.error(
            "Chi phí thiết yếu và khoản trả nợ "
            "đang vượt thu nhập. Cần điều chỉnh "
            "ngân sách trước khi đặt mục tiêu tiết kiệm."
        )

    else:
        # Mục tiêu tiết kiệm khởi điểm:
        # tối đa 20% thu nhập và không vượt số tiền còn lại.
        saving = min(income * 0.20, available)

        # Dành phần còn lại cho chi tiêu linh hoạt.
        flexible = available - saving

        st.success(
            f"Mục tiêu tiết kiệm tham khảo: "
            f"{saving:,.0f} VNĐ/tháng"
        )

        st.info(
            f"Ngân sách chi tiêu linh hoạt còn lại: "
            f"{flexible:,.0f} VNĐ/tháng"
        )

        if saving < income * 0.20:
            st.warning(
                "Chưa thể dành 20% thu nhập để tiết kiệm "
                "với mức chi phí hiện tại. Không cần "
                "ép bản thân theo tỷ lệ cố định."
            )

        if goal == "Quỹ dự phòng":
            st.write(
                "Gợi ý: xây dựng quỹ dự phòng dựa trên "
                "chi phí thiết yếu thực tế. Có thể bắt đầu "
                "với mục tiêu nhỏ, sau đó tăng dần."
            )

        elif goal == "Trả nợ":
            st.write(
                "Gợi ý: kiểm tra lãi suất và nghĩa vụ "
                "thanh toán của từng khoản nợ trước khi "
                "phân bổ thêm tiền trả nợ."
            )

        elif goal == "Học tập":
            st.write(
                "Gợi ý: xác định tổng học phí hoặc "
                "chi phí chứng chỉ, rồi chia cho số tháng "
                "còn lại trước hạn thanh toán."
            )

        elif goal == "Mua sắm mục tiêu lớn":
            st.write(
                "Gợi ý: xác định giá mục tiêu và thời hạn "
                "để tính số tiền cần dành ra mỗi tháng."
            )

        else:
            st.write(
                "Gợi ý: ưu tiên quỹ dự phòng và các "
                "nghĩa vụ tài chính trước khi lựa chọn "
                "mục tiêu tích lũy dài hạn."
            )

        budget = pd.DataFrame({
            "Khoản mục": [
                "Nhà ở", "Ăn uống", "Đi lại",
                "Hóa đơn", "Thiết yếu khác",
                "Trả nợ", "Tiết kiệm",
                "Chi tiêu linh hoạt"
            ],
            "Số tiền (VNĐ)": [
                housing_cost, food, transport,
                bills, other, debt, saving, flexible
            ]
        })

        st.subheader("Bảng ngân sách tháng")
        st.dataframe(budget, use_container_width=True)

        st.subheader("Biểu đồ phân bổ ngân sách")
        chart = budget.set_index("Khoản mục")
        st.bar_chart(chart)

st.caption(
    "FinMate là công cụ lập kế hoạch tham khảo. "
    "Kết quả phụ thuộc vào dữ liệu người dùng nhập."
)
