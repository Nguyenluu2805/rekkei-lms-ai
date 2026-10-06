"""
=============================================================================
 RIKKEI LMS — RIKA AI AGENT (Powered by Gemini)
=============================================================================
SDK    : google-genai (thế hệ mới)
Model  : gemini-3.8-flash
Chạy   : python agent.py
=============================================================================
"""

import sys
import os

# Fix charmap UnicodeEncodeError on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"

import json
import time
import textwrap
from dotenv import load_dotenv
from google import genai
from google.genai import types

from lms_tools import TOOLS_SCHEMA, LMSFunctionExecutor

load_dotenv()

def safe_print(*args, **kwargs):
    """In log ra console an toàn trên Windows mọi bảng mã (cp1258, cp1252, charmap)."""
    try:
        print(*args, **kwargs)
    except Exception:
        try:
            clean_args = [
                str(a).encode("ascii", errors="replace").decode("ascii")
                for a in args
            ]
            print(*clean_args, **kwargs)
        except Exception:
            pass

# ---------------------------------------------------------------------------
# CẤU HÌNH
# ---------------------------------------------------------------------------
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY")
# Các model theo ưu tiên — tự động fallback nếu model trước bị 503/404/429
MODEL_PRIORITY  = [
    "gemini-flash-lite-latest",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3-flash-preview",
    "gemini-3.8-flash",
    "gemini-3.7-flash",
]
GEMINI_MODEL    = MODEL_PRIORITY[0]   # Default

SYSTEM_PROMPT = """Bạn là **Rika** — Trợ lý AI thông minh quản lý hệ thống LMS của Rikkei Education.

## Nhiệm vụ:
- Hỗ trợ giảng viên/nhân viên tra cứu: lớp học, sinh viên, khoá học, thông báo.
- Gửi thông báo đến sinh viên theo yêu cầu.
- Phân tích và tóm tắt dữ liệu từ hệ thống LMS.

## Nguyên tắc:
1. Luôn dùng tools để lấy dữ liệu thực — TUYỆT ĐỐI không tự bịa đặt thông tin, số lượng sinh viên hay điểm số. Nếu API trả về không có bài tập được giao (assigned_tasks rỗng) hoặc chưa có sinh viên nào nộp bài (submitted_count = 0), PHẢI thông báo trung thực là buổi học này chưa được cấu hình bài tập hoặc chưa có sinh viên nào nộp bài trên LMS.
2. Nếu thông tin người dùng cung cấp chưa đủ cụ thể (ví dụ: chỉ cho tên mà thiếu mã lớp, mã môn hoặc mã sinh viên), hãy chủ động hỏi lại người dùng để làm rõ trước hoặc ngay sau khi tìm kiếm sơ bộ, tránh gọi vòng lặp quá nhiều tool.
3. Khi không tìm thấy thông tin chính xác, hãy thông báo rõ ràng và đưa ra gợi ý các dữ liệu tương tự hiện có trên hệ thống nếu biết.
4. Khi gợi ý các lớp học, môn học, sinh viên hoặc các thao tác tiếp theo, HÃY ĐẶT CHÚNG VÀO NÚT BẤM bằng cú pháp [choice: Tên hiển thị | Câu lệnh gửi đi].
   TUYỆT ĐỐI KHÔNG thêm gạch đầu dòng (-), dấu sao (*), dấu chấm tròn (•) hoặc số thứ tự trước [choice:...].
   Mỗi nút bấm đặt trên một dòng riêng, ví dụ:
   [choice: Lớp HCM-KS26-CNTT1 | Kiểm tra lớp HCM-KS26-CNTT1]
   [choice: Môn IT108-K26 - Nhập Môn CNTT | Kiểm tra môn IT108-K26]
   [choice: Gửi thông báo cho Bùi Gia Anh | Gửi thông báo cho Bùi Gia Anh]
   Giao diện sẽ tự động chuyển cú pháp này thành các nút bấm tương tác để người dùng chỉ cần click để chọn.
5. Hỏi xác nhận trước khi gửi thông báo cho hơn 10 sinh viên.
6. Trả lời bằng tiếng Việt, ngắn gọn và chuyên nghiệp.
7. Nếu cần ID để gọi tool tiếp theo, hãy gọi tool trước để lấy ID đó.
8. Khi danh sách dài (>10 mục), hãy tóm tắt và hỏi người dùng muốn xem thêm không.
9. Khi người dùng tra cứu điểm danh hoặc bài tập của một lớp mà KHÔNG nói rõ môn học: hãy hiển thị dữ liệu tổng quan, ĐỒNG THỜI LUÔN ĐƯA RA CÁC NÚT LỰA CHỌN MÔN HỌC [choice: ...] (lấy từ danh sách available_courses của lớp đó) để người dùng chỉ cần click là lọc riêng theo môn học mình quan tâm.
10. Định dạng bảng chi tiết & Xuất dữ liệu: LUÔN TRÌNH BÀY CÁC BÁO CÁO ĐIỂM DANH, BÀI TẬP, CHỈ SỐ ĐÀO TẠO VÀ DANH SÁCH SINH VIÊN DƯỚI DẠNG BẢNG MARKDOWN (Markdown Table) với các cột rõ ràng (ví dụ: STT, Mã SV, Họ và tên, Vắng KP, Vắng CP, Có mặt/Tổng, Đánh giá / Trạng thái). Tránh liệt kê danh sách thô bằng số gạch đầu dòng. Giao diện người dùng sẽ tự động gắn thanh công cụ có nút 'Tải file' (CSV/Excel) và 'Sao chép' ngay trên đầu mỗi bảng để người dùng tải dữ liệu về máy chỉ với 1 cú click.
11. Thao tác Thêm / Sửa / Xóa bài tập về nhà: Khi người dùng yêu cầu tạo mới bài tập (create_homework), chỉnh sửa bài tập (update_homework) hoặc xóa bài tập (delete_homework), hãy chủ động gọi tool tương ứng. Nếu người dùng chỉ nói tên lớp hoặc số buổi học (ví dụ: 'buổi 1 môn IT108 lớp HCM-KS26-CNTT1'), hãy tự động tìm session_id bằng các tool list_attendance_sessions hoặc list_courses trước.
12. Sau khi tạo hoặc cập nhật bài tập về nhà thành công, hãy hiển thị tóm tắt thông tin bài tập (Tiêu đề, Buổi học, Độ khó, Thời gian dự kiến, Tiêu chí chấm điểm) một cách rõ ràng và chuyên nghiệp.
13. Thao tác Nhận xét / Chấm bài tập sinh viên (update_submission_feedback):
    - Khi người dùng muốn chấm điểm lại, sửa nhận xét hoặc cập nhật kết quả bài làm của một sinh viên:
      TUYỆT ĐỐI KHÔNG liệt kê danh sách text 1, 2, 3... để bắt người dùng gõ tay.
      HÃY LUÔN XUẤT THẺ BIỂU MẪU TƯƠNG TÁC [action_form: {JSON}] để người dùng có thể chọn điểm, PASS/FAIL và nhận xét trực tiếp trên giao diện bằng 1 cú click.
      Mẫu schema chuẩn:
      [action_form: {
        "id": "grade_submission_form",
        "title": "Chấm điểm & Nhận xét bài tập",
        "description": "Sinh viên: <Tên SV>",
        "action_type": "tool_execute",
        "action_target": "update_submission_feedback",
        "submit_label": "Xác nhận cập nhật",
        "success_message": "Đã cập nhật điểm và nhận xét thành công!",
        "meta": {
          "student_search": "<Tên SV>"
        },
        "fields": [
          {
            "name": "aiScore",
            "label": "Điểm số (thang 100)",
            "type": "number",
            "required": true,
            "default": 85,
            "min": 0,
            "max": 100,
            "step": 5,
            "presets": [60, 70, 80, 85, 90, 100]
          },
          {
            "name": "aiDecision",
            "label": "Kết quả đánh giá",
            "type": "pills",
            "required": true,
            "default": "PASS",
            "options": ["PASS", "FAIL"]
          },
          {
            "name": "aiSummary",
            "label": "Nhận xét của Giảng viên / AI",
            "type": "textarea",
            "required": true,
            "default": "Bài làm hoàn thành tốt, đáp ứng đúng yêu cầu.",
            "placeholder": "Nhập nội dung nhận xét...",
            "templates": [
              "Bài làm xuất sắc, code sạch và tư duy tốt.",
              "Đã đạt các yêu cầu cơ bản, cần chú ý convention.",
              "Chưa đạt yêu cầu, cần hoàn thiện và nộp lại."
            ]
          }
        ]
      }]
14. Hệ thống Form tương tác đa năng [action_form: {JSON}]:
    Bất cứ khi nào cần thu thập thông tin từ người dùng (như tạo bài tập mới create_homework, gửi thông báo send_notification...), hãy ưu tiên dùng cú pháp [action_form: {JSON}] thay vì bắt người dùng gõ văn bản từng dòng. Form luôn có sẵn nút HỦY và nút XÁC NHẬN để đảm bảo tính tiện lợi và chuyên nghiệp.
    LƯU Ý: TUYỆT ĐỐI KHÔNG bọc tag [action_form: { ... }] bên trong các dấu markdown code fences (như ```json hoặc ```). Hãy viết trực tiếp cú pháp [action_form: { ... }] trên một đoạn riêng để hệ thống tự động render giao diện widget.
15. DUY TRÌ NGỮ CẢNH HỘI THOẠI (CONTEXT TRACKING):
    - Khi người dùng hỏi các câu tiếp nối ngắn như: 'cho tôi chi tiết toàn bộ danh sách', 'xem thêm', 'danh sách sinh viên', 'tình hình nộp bài', 'điểm danh ra sao', 'gửi thông báo'...
      BẠN BẮT BUỘC PHẢI DUY TRÌ ĐỐI TƯỢNG VÀ LỚP HỌC (Context) ĐANG ĐƯỢC ĐỀ CẬP Ở CÁC CÂU TRƯỚC ĐÓ.
      Ví dụ: Nếu các câu trước vừa nói về lớp 'HCM-KS26-CNTT1', và câu tiếp theo người dùng nói 'cho tôi chi tiết toàn bộ danh sách' -> Nghĩa là người dùng ĐANG YÊU CẦU XEM TOÀN BỘ DANH SÁCH SINH VIÊN CỦA LỚP HCM-KS26-CNTT1. BẠN PHẢI GỌI `list_students(class_name='HCM-KS26-CNTT1', limit=100)` để hiển thị đầy đủ sinh viên của lớp đó, TUYỆT ĐỐI KHÔNG gọi `list_students()` không tham số khiến dữ liệu bị nhảy sang toàn bộ 300+ sinh viên toàn trường!
    - Khi người dùng yêu cầu tra cứu sinh viên của một lớp: LUÔN TRUYỀN `class_name` hoặc `class_id` vào `list_students(class_name=...)` để hệ thống trả về đúng danh sách học sinh thuộc lớp đó.
16. TRA CỨU CHỈ SỐ ĐÀO TẠO, ĐIỂM RPOINT & ĐIỀU KIỆN DỰ THI:
    - Khi người dùng hỏi về: điểm rPoint, tỷ lệ nghỉ học (vắng học), điểm chuẩn bị bài, tỷ lệ nộp bài tập, điểm tuân thủ nội quy, hoặc điều kiện dự thi của sinh viên / lớp học:
      + Với cá nhân sinh viên: Hãy gọi `get_student_training_metrics(student_search=..., class_name=..., course_name=...)`. Tool này truy xuất trực tiếp từ API `/api/auto-rpoint` gồm:
        * Điểm rPoint tổng (totalScore / 100), điểm gốc (baseScore), điểm thưởng (bonus)
        * Điểm chuyên cần (attendanceScore / 20) & Tỷ lệ nghỉ học (absenceRate %)
        * Điểm chuẩn bị bài (preparationScore / 20)
        * Điểm bài tập về nhà (assignmentScore / 20) & Tỷ lệ nộp bài (submissionRate %)
        * Điểm tuân thủ nội quy (complianceScore / 40)
        * Trạng thái điều kiện thi (examEligible: ĐỦ ĐIỀU KIỆN / KHÔNG ĐỦ ĐIỀU KIỆN) kèm chi tiết tiêu chuẩn.
      + Với cả lớp hoặc môn học: Hãy gọi `get_class_training_metrics(class_name=..., course_name=..., limit=20)`. Tool này tự động thống kê điểm rPoint trung bình, tỷ lệ vắng trung bình, điểm chuẩn bị bài trung bình, tỷ lệ nộp bài trung bình và danh sách sinh viên đủ / chưa đủ điều kiện thi.
    - Luôn trình bày các chỉ số đào tạo dưới dạng Bảng Markdown trực quan, khoa học và làm nổi bật các trường hợp cần lưu ý hoặc cảnh báo.
17. MÚI GIỜ HỆ THỐNG & ĐỊNH DẠNG THỜI GIAN (GMT+7):
    - Toàn bộ thời gian trên hệ thống LMS (thời gian nộp bài, thời điểm điểm danh, tạo bài tập) hiển thị theo Giờ Việt Nam (UTC+7 / GMT+7).
    - Các tool đã tự động chuyển đổi từ giờ gốc lưu trữ của server (UTC ISO string) sang Giờ Việt Nam (UTC+7, định dạng `DD/MM/YYYY HH:mm`).
    - Ví dụ: 05:44 UTC chính là 12:44 giờ Việt Nam (chênh lệch đúng +7 tiếng). Khi hiển thị bảng bài nộp, LUÔN LUÔN hiển thị theo giờ Việt Nam (GMT+7), TUYỆT ĐỐI KHÔNG dùng giờ UTC thô.
18. VÔ HIỆU HÓA XEM THÔNG TIN CÁ NHÂN:
    - Tính năng xem thông tin cá nhân của người dùng/giảng viên/quản trị viên (hồ sơ, email, số điện thoại, vai trò, ID tài khoản) ĐÃ BỊ TẮT HOÀN TOÀN vì lý do bảo mật và quyền riêng tư.
    - Khi người dùng yêu cầu 'Xem thông tin cá nhân của tôi', 'Thông tin của tôi', 'Tài khoản của tôi', 'Họ tên/email của tôi'... TUYỆT ĐỐI KHÔNG tra cứu và KHÔNG hiển thị bất kỳ thông tin cá nhân nào.
    - Hãy phản hồi ngắn gọn, lịch sự: 'Vì lý do bảo mật và quyền riêng tư, tính năng xem thông tin cá nhân đã được vô hiệu hóa trên hệ thống này. Tôi sẵn sàng hỗ trợ bạn quản lý lớp học, sinh viên, điểm danh, bài tập và theo dõi điểm rPoint.' kèm theo các nút gợi ý [choice: ...] về lớp học hoặc sinh viên.

## Thông tin hệ thống sẵn có:
- K26-CNTT  (ID: 6a868c22c6d890523883e324) — Kỹ sư Công nghệ thông tin
- K26-QTKDS (ID: 6a868c33c6d890523883e335) — Quản trị kinh doanh số
- Địa điểm: HN (Hà Nội) | HCM (TP. Hồ Chí Minh)
"""

# ---------------------------------------------------------------------------
# CHUYỂN ĐỔI TOOLS_SCHEMA → google-genai Tool format
# ---------------------------------------------------------------------------

def _build_tools(schema: list) -> list[types.Tool]:
    """Chuyển đổi OpenAI-style schema sang google-genai Tool."""
    declarations = []
    for item in schema:
        fn = item["function"]
        raw_params = fn.get("parameters", {})
        raw_props  = raw_params.get("properties", {})

        props = {}
        for pname, pspec in raw_props.items():
            p = types.Schema(
                type=pspec["type"].upper(),
                description=pspec.get("description", ""),
            )
            if "enum" in pspec:
                p = types.Schema(
                    type=pspec["type"].upper(),
                    description=pspec.get("description", ""),
                    enum=pspec["enum"],
                )
            if pspec["type"] == "array" and "items" in pspec:
                p = types.Schema(
                    type="ARRAY",
                    description=pspec.get("description", ""),
                    items=types.Schema(type=pspec["items"]["type"].upper()),
                )
            props[pname] = p

        param_schema = types.Schema(
            type="OBJECT",
            properties=props,
            required=raw_params.get("required", []),
        ) if props else None

        decl = types.FunctionDeclaration(
            name=fn["name"],
            description=fn["description"],
            parameters=param_schema,
        )
        declarations.append(decl)

    return [types.Tool(function_declarations=declarations)]

# ---------------------------------------------------------------------------
# AGENT
# ---------------------------------------------------------------------------

class RikkaAgent:
    """
    Rika — AI Agent LMS Rikkei.
    Tích hợp Gemini SDK mới (google-genai) với LMS Function Calling.
    """

    def __init__(self):
        safe_print("🚀 Đang khởi động Rika Agent...")

        self.client   = genai.Client(api_key=GEMINI_API_KEY)
        self.executor = LMSFunctionExecutor()
        
        import tools_manager
        self.active_schema = tools_manager.get_active_schema()
        self.tools    = _build_tools(self.active_schema)
        self.history  = []   # Lưu lịch sử hội thoại

        safe_print(f"✅ Gemini model  : {GEMINI_MODEL}")
        safe_print(f"✅ Tools sẵn sàng: {len(self.active_schema)} functions kích hoạt")
        safe_print(f"✅ Kết nối LMS   : OK")
        safe_print("─" * 60)

    def reload_tools(self):
        """Tải lại danh sách tools đang kích hoạt từ tools_manager."""
        import tools_manager
        self.active_schema = tools_manager.get_active_schema()
        self.tools = _build_tools(self.active_schema)
        safe_print(f"🔄 Đã cập nhật lại bộ tools cho Agent: {len(self.active_schema)} tools kích hoạt")

    def _send(self, contents: list, model: str = None) -> types.GenerateContentResponse:
        """Gọi Gemini API. Tự động retry và fallback model khi 503/429/404."""
        models_to_try = MODEL_PRIORITY if model is None else [model]
        last_err = None

        for m in models_to_try:
            for attempt in range(3):
                try:
                    return self.client.models.generate_content(
                        model=m,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            tools=self.tools,
                            temperature=0.2,
                            max_output_tokens=4096,
                        ),
                    )
                except Exception as e:
                    last_err = e
                    err_str  = str(e)

                    # 429: trích retry-after từ message
                    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                        import re
                        m_delay = re.search(r'retry in (\d+)', err_str)
                        wait = int(m_delay.group(1)) if m_delay else 3
                        if wait <= 8 and attempt < 1:
                            safe_print(f"  ⚠️  Model {m} chạm giới hạn tạm thời (429), chờ {wait}s để tự động phục hồi...")
                            time.sleep(wait)
                            continue  # Thử lại ngay sau khi chờ
                        else:
                            safe_print(f"  ⚠️  Model {m} vượt quota (429), chuyển model dự phòng...")
                            time.sleep(1.5)
                            break  # Chuyển sang model tiếp theo

                    elif "503" in err_str or "UNAVAILABLE" in err_str:
                        wait = 2 ** attempt
                        safe_print(f"  ⚠️  Model {m} quá tải, thử lại sau {wait}s... ({attempt+1}/3)")
                        time.sleep(wait)

                    elif "404" in err_str or "NOT_FOUND" in err_str:
                        safe_print(f"  ⚠️  Model {m} không khả dụng, chuyển sang model dự phòng...")
                        break

                    else:
                        raise  # Lỗi khác: raise luôn

        raise RuntimeError(f"Tất cả {len(models_to_try)} models đều thất bại. Lỗi cuối: {last_err}")

    def _process_response(self, response, contents: list) -> str:
        """
        Xử lý response từ Gemini.
        Tự động thực thi function calls và gửi kết quả trở lại (tool chaining).
        """
        MAX_ROUNDS = 6

        for _ in range(MAX_ROUNDS):
            candidate = response.candidates[0]
            parts      = candidate.content.parts

            # Thu thập tất cả function calls trong response này
            fn_calls = [p for p in parts if p.function_call]

            if not fn_calls:
                # Không có tool call → lấy text phản hồi
                text_parts = [p.text for p in parts if hasattr(p, "text") and p.text]
                return "\n".join(text_parts) or "(Không có phản hồi)"

            # Thêm model response vào lịch sử
            contents.append(types.Content(role="model", parts=parts))

            # Thực thi từng function call
            tool_response_parts = []
            for fn_part in fn_calls:
                fc   = fn_part.function_call
                name = fc.name
                args = dict(fc.args) if fc.args else {}

                safe_print(f"\n  🔧 \033[36m{name}\033[0m({json.dumps(args, ensure_ascii=False)})")

                result = self.executor.execute(name, args)
                preview = str(result)[:200].replace("\n", " ")
                safe_print(f"  📦 {preview}...")

                tool_response_parts.append(
                    types.Part.from_function_response(
                        name=name,
                        response={"result": result},
                    )
                )

            # Thêm kết quả tool vào contents và gọi lại Gemini
            contents.append(types.Content(role="user", parts=tool_response_parts))
            response = self._send(contents)

        # Nếu đã gọi hết MAX_ROUNDS mà model vẫn muốn gọi tool, buộc model tóm tắt dựa trên dữ liệu hiện có
        try:
            summary_content = list(contents)
            summary_content.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(
                        text="Đã đạt giới hạn tra cứu. Hãy tổng kết ngắn gọn những thông tin bạn đã tìm được từ hệ thống và nêu rõ cần người dùng cung cấp thêm thông tin gì (mã lớp, mã sinh viên, môn học...) để hoàn tất tra cứu."
                    )]
                )
            )
            final_res = self.client.models.generate_content(
                model=GEMINI_MODEL,
                contents=summary_content,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.2,
                )
            )
            return final_res.text or "Dữ liệu tra cứu chưa đầy đủ. Bạn vui lòng cung cấp thêm thông tin chi tiết (như mã lớp, môn học hoặc mã sinh viên) để mình hỗ trợ nhé!"
        except Exception:
            return "Dữ liệu tra cứu chưa đầy đủ. Thầy/Cô vui lòng cung cấp thêm thông tin chi tiết (như mã lớp, môn học hoặc mã sinh viên) để hệ thống hỗ trợ chính xác hơn nhé!"

    def chat(self, user_message: str) -> str:
        """Gửi một tin nhắn, nhận phản hồi có thể bao gồm nhiều vòng tool chaining."""
        try:
            # 1. Thu gọn lịch sử hội thoại: chỉ giữ tối đa 10 tin nhắn gần nhất dạng text (role user / model)
            # Loại bỏ các kết quả tool chaining cũ cồng kềnh khỏi các lượt trước để không vượt quota 250k token/phút
            cleaned_history = []
            for item in self.history[-10:]:
                parts_text = [p for p in item.parts if hasattr(p, "text") and p.text]
                if parts_text:
                    cleaned_history.append(types.Content(role=item.role, parts=parts_text))

            # 2. Xây dựng turn_contents cho lượt hội thoại hiện tại
            turn_contents = list(cleaned_history)
            turn_contents.append(
                types.Content(role="user", parts=[types.Part.from_text(text=user_message)])
            )

            response = self._send(turn_contents)

            # Xử lý tool chaining trong turn này
            answer = self._process_response(response, turn_contents)

            # 3. Cập nhật lại self.history: chỉ lưu trữ câu hỏi và câu trả lời hoàn chỉnh
            self.history = cleaned_history
            self.history.append(types.Content(role="user", parts=[types.Part.from_text(text=user_message)]))
            self.history.append(types.Content(role="model", parts=[types.Part.from_text(text=answer)]))
            return answer
        except Exception as e:
            safe_print(f"❌ Agent chat exception: {e}")
            if self.history and self.history[-1].role == "user":
                self.history.pop()  # Rollback để không làm bẩn context hội thoại
            return "⚠️ Hệ thống hiện tại đang gặp sự cố hoặc đang trong quá trình bảo trì. Vui lòng thử lại sau ít phút!"

    def reset(self):
        """Xóa lịch sử hội thoại."""
        self.history = []

    def run_interactive(self):
        """Vòng lặp chat tương tác trong terminal."""
        print("\n🤖 \033[1mRika — Trợ lý LMS Rikkei\033[0m đã sẵn sàng!")
        print("   Gõ \033[33m'quit'\033[0m để thoát | \033[33m'clear'\033[0m để xóa lịch sử\n")

        while True:
            try:
                user_input = input("\033[32m👤 Bạn:\033[0m ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\n\n👋 Tạm biệt!")
                break

            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "thoát"):
                print("\n👋 Tạm biệt!")
                break
            if user_input.lower() == "clear":
                self.reset()
                print("🗑️  Đã xóa lịch sử.\n")
                continue

            print(f"\n\033[34m🤖 Rika:\033[0m", end=" ", flush=True)
            try:
                reply = self.chat(user_input)
                # Wrap cho dễ đọc trên terminal
                lines = reply.split("\n")
                wrapped_lines = []
                for line in lines:
                    if len(line) > 80:
                        wrapped_lines.append(textwrap.fill(line, width=80, subsequent_indent="        "))
                    else:
                        wrapped_lines.append(line)
                print("\n".join(wrapped_lines))
            except Exception as e:
                print(f"\n❌ Lỗi: {e}")
            print()


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    agent = RikkaAgent()
    agent.run_interactive()
