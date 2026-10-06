"""
=============================================================================
 RIKKEI LMS — AI AGENT FUNCTION CALLING TOOLKIT
=============================================================================
Chuẩn định nghĩa: OpenAI Tool Calling / Anthropic Tool Use
Phiên bản       : 1.0.0
Tác giả         : Auto-generated từ API Discovery

Mô tả:
  Bộ công cụ (Tool) này cho phép AI Agent hiểu và thực thi
  các nghiệp vụ quản lý trên hệ thống LMS Rikkei Admin.
  Agent sẽ nhận yêu cầu từ người dùng bằng ngôn ngữ tự nhiên,
  chọn tool phù hợp, điền đúng tham số và gọi hàm tương ứng.
=============================================================================
"""

import json
import requests
from typing import Any, Optional
from datetime import datetime, timezone, timedelta
from auth_manager import RikkeiPortalAPI

BASE_URL = "https://lms-admin.rikkei.edu.vn"

# Múi giờ Việt Nam (UTC+7 / GMT+7)
VIETNAM_TZ = timezone(timedelta(hours=7))

def format_vietnam_time(dt_str: Any) -> Optional[str]:
    """Chuyển đổi chuỗi ISO UTC từ server LMS sang giờ Việt Nam (UTC+7, định dạng DD/MM/YYYY HH:mm)."""
    if not dt_str or not isinstance(dt_str, str):
        return None
    try:
        clean_str = dt_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        vn_dt = dt.astimezone(VIETNAM_TZ)
        return vn_dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        try:
            return dt_str[:16].replace("T", " ")
        except Exception:
            return dt_str


# ===========================================================================
# I. ĐỊNH NGHĨA SCHEMA CHO AI AGENT (OpenAI / Anthropic format)
# ===========================================================================

TOOLS_SCHEMA = [

    # -----------------------------------------------------------------------
    # NHÓM 1: HỒ SƠ & THÔNG TIN CÁ NHÂN
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "get_my_profile",
            "description": (
                "Lấy thông tin hồ sơ cá nhân của nhân viên/giảng viên đang đăng nhập. "
                "Dùng khi người dùng hỏi: 'Thông tin tài khoản của tôi', 'Tôi có role gì', "
                "'Tôi đang dạy hệ thống nào', 'Họ tên email của tôi là gì'."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },

    # -----------------------------------------------------------------------
    # NHÓM 2: QUẢN LÝ HỆ THỐNG ĐÀO TẠO
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "list_training_systems",
            "description": (
                "Liệt kê tất cả các hệ thống/chương trình đào tạo hiện có (ví dụ: K26-CNTT, K26-QTKDS). "
                "Dùng khi người dùng hỏi: 'Có những chương trình đào tạo nào', 'Hệ thống CNTT là gì', "
                "'Danh sách ngành học', 'Các khóa K26 gồm những gì'."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_training_system_detail",
            "description": (
                "Lấy thông tin chi tiết của một hệ thống/chương trình đào tạo theo ID. "
                "Dùng sau khi đã biết systemId từ list_training_systems, "
                "khi người dùng muốn xem chi tiết về một chương trình cụ thể."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "system_id": {
                        "type": "string",
                        "description": "ID duy nhất của hệ thống đào tạo (MongoDB ObjectId). Ví dụ: '6a868c22c6d890523883e324'"
                    }
                },
                "required": ["system_id"]
            }
        }
    },

    # -----------------------------------------------------------------------
    # NHÓM 3: QUẢN LÝ LỚP HỌC
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "list_classes",
            "description": (
                "Lấy danh sách tất cả các lớp học mà nhân viên/giảng viên hiện tại có quyền quản lý. "
                "Dùng khi người dùng hỏi: 'Tôi đang quản lý những lớp nào', 'Danh sách lớp học', "
                "'Có bao nhiêu lớp', 'Lớp HN-KS26-CNTT1 có tồn tại không'. "
                "Hỗ trợ lọc theo tên lớp, phân trang."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Số lớp tối đa trả về mỗi trang. Mặc định: 20, tối đa: 100.",
                        "default": 20
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Số bản ghi bỏ qua để phân trang. Mặc định: 0.",
                        "default": 0
                    },
                    "search": {
                        "type": "string",
                        "description": "Từ khoá tìm kiếm lớp theo tên hoặc mã lớp (classCode). Ví dụ: 'HN-KS26-CNTT'"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_class_detail",
            "description": (
                "Lấy thông tin chi tiết của một lớp học cụ thể theo ID. "
                "Trả về mã lớp (classCode), loại hình (FULLTIME/PARTTIME), "
                "danh sách ID khoá học (courseIds), ID hệ thống (systemIds). "
                "Dùng khi người dùng muốn xem chi tiết về một lớp cụ thể."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "class_id": {
                        "type": "string",
                        "description": "ID duy nhất của lớp học. Ví dụ: '6aac917e6fde2b6e692ed504'"
                    }
                },
                "required": ["class_id"]
            }
        }
    },

    # -----------------------------------------------------------------------
    # NHÓM 4: QUẢN LÝ KHOÁ HỌC / MÔN HỌC
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "list_courses",
            "description": (
                "Lấy danh sách tất cả các khoá học/môn học mà nhân viên có quyền xem. "
                "Bao gồm: Tiếng Anh (ENG), Tiếng Nhật (JPN), CNTT (IT), Kỹ năng mềm (SSK), "
                "Marketing, AI, DA, Project... "
                "Dùng khi người dùng hỏi: 'Có những môn học nào', 'Danh sách khoá học', "
                "'Môn IT101 có không', 'Khoá học Orientation là gì'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Số khoá học tối đa trả về. Mặc định: 50.",
                        "default": 50
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Số bản ghi bỏ qua để phân trang. Mặc định: 0.",
                        "default": 0
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_course_detail",
            "description": (
                "Lấy thông tin chi tiết của một khoá học/môn học theo ID. "
                "Trả về: tên, mã khoá (courseCode), số buổi học (totalSessions), "
                "công thức tính điểm (scoringFormula với trọng số: attendance, quiz, hackathon, finalExam), "
                "loại thi (examType: PROJECT/EXAM), phương pháp chấm (scoringMethod). "
                "Dùng khi người dùng muốn biết cấu trúc điểm của một môn học."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "course_id": {
                        "type": "string",
                        "description": "ID duy nhất của khoá học. Ví dụ: '6aae5ad27d22545796a8eeaa'"
                    }
                },
                "required": ["course_id"]
            }
        }
    },

    # -----------------------------------------------------------------------
    # NHÓM 5: QUẢN LÝ SINH VIÊN
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "list_students",
            "description": (
                "Lấy danh sách sinh viên với nhiều bộ lọc linh hoạt. "
                "Dùng khi người dùng hỏi: 'Danh sách sinh viên', 'Sinh viên lớp CNTT', "
                "'Có bao nhiêu sinh viên đang học', 'Sinh viên ở Hà Nội', "
                "'Tìm sinh viên tên Nguyễn Văn A'. "
                "Có thể lọc theo hệ thống, địa điểm, trạng thái, tên."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Số sinh viên tối đa trả về mỗi trang. Mặc định: 20.",
                        "default": 20
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Số bản ghi bỏ qua để phân trang. Mặc định: 0.",
                        "default": 0
                    },
                    "system_id": {
                        "type": "string",
                        "description": (
                            "Lọc sinh viên theo ID hệ thống đào tạo. "
                            "K26-CNTT: '6a868c22c6d890523883e324', "
                            "K26-QTKDS: '6a868c33c6d890523883e335'"
                        )
                    },
                    "search": {
                        "type": "string",
                        "description": "Tìm kiếm theo tên hoặc mã sinh viên (studentCode, ví dụ: RE26449)"
                    },
                    "status": {
                        "type": "string",
                        "description": "Lọc theo trạng thái học tập.",
                        "enum": ["ĐANG HỌC", "BẢO LƯU", "ĐÃ TỐT NGHIỆP", "NGHỈ HỌC"]
                    },
                    "location": {
                        "type": "string",
                        "description": "Lọc theo địa điểm học.",
                        "enum": ["HN", "HCM"]
                    },
                    "class_id": {
                        "type": "string",
                        "description": "Lọc danh sách sinh viên theo ID lớp học cụ thể."
                    },
                    "class_name": {
                        "type": "string",
                        "description": "Lọc sinh viên theo tên hoặc mã lớp học (Ví dụ: 'HCM-KS26-CNTT1', 'HN-KS26-CNTT1')."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_student_detail",
            "description": (
                "Lấy thông tin chi tiết đầy đủ của một sinh viên theo ID. "
                "Trả về: mã sinh viên, họ tên, email, SĐT, ngày sinh, trạng thái, "
                "địa điểm học (HN/HCM), hệ thống đào tạo, tên lớp. "
                "Dùng khi cần xem profile cụ thể của một sinh viên."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "student_id": {
                        "type": "string",
                        "description": "ID duy nhất của sinh viên (MongoDB ObjectId). Ví dụ: '6ab0ee764cf535213d26a981'"
                    }
                },
                "required": ["student_id"]
            }
        }
    },

    # -----------------------------------------------------------------------
    # NHÓM 6: THÔNG BÁO
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "list_sent_notifications",
            "description": (
                "Lấy danh sách các thông báo mà nhân viên/hệ thống đã gửi đi trước đây. "
                "Dùng khi người dùng hỏi: 'Tôi đã gửi thông báo gì', 'Lịch sử thông báo', "
                "'Những thông báo nào đã được gửi', 'Kiểm tra thông báo lịch học đã gửi chưa'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Số thông báo tối đa trả về. Mặc định: 10.",
                        "default": 10
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Số bản ghi bỏ qua để phân trang. Mặc định: 0.",
                        "default": 0
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_received_notifications",
            "description": (
                "Lấy danh sách các thông báo mà nhân viên NHẬN ĐƯỢC từ sinh viên hoặc hệ thống. "
                "Bao gồm: đơn xin nghỉ phép, thông báo từ sinh viên. "
                "Dùng khi người dùng hỏi: 'Tôi có thông báo mới không', 'Có đơn nghỉ phép nào chưa xử lý không', "
                "'Sinh viên nào vừa gửi đơn xin phép'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Số thông báo tối đa trả về. Mặc định: 10.",
                        "default": 10
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Số bản ghi bỏ qua để phân trang. Mặc định: 0.",
                        "default": 0
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_notification",
            "description": (
                "Gửi thông báo đến một hoặc nhiều sinh viên cụ thể thông qua hệ thống LMS. "
                "Dùng khi người dùng yêu cầu: 'Gửi thông báo cho lớp HN-KS26-CNTT1', "
                "'Nhắc nhở sinh viên RE26449 về lịch nộp bài', "
                "'Thông báo lịch thi cho tất cả sinh viên CNTT'. "
                "QUAN TRỌNG: Phải có danh sách targetStudentIds trước khi gọi hàm này. "
                "Nếu chưa có, hãy gọi list_students trước để lấy ID sinh viên."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Tiêu đề ngắn gọn của thông báo. Tối đa 100 ký tự. Ví dụ: 'Thông báo lịch thi cuối kỳ'"
                    },
                    "message": {
                        "type": "string",
                        "description": "Nội dung thông báo chính. Ví dụ: 'Lịch thi môn IT101 sẽ diễn ra vào ngày 30/09/2026'"
                    },
                    "target_student_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Danh sách ID của các sinh viên sẽ nhận thông báo. "
                            "Đây là MongoDB ObjectId của sinh viên. "
                            "Ví dụ: ['6ab0ee764cf535213d26a981', '6aae50fc7d22545796a8dbdb']"
                        )
                    },
                    "body": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Danh sách các dòng nội dung chi tiết bổ sung (tuỳ chọn). "
                            "Ví dụ: ['Phòng thi: A301', 'Thời gian: 8:00 - 10:00', 'Mang theo CMND/CCCD']"
                        )
                    }
                },
                "required": ["title", "message", "target_student_ids"]
            }
        }
    },

    # -----------------------------------------------------------------------
    # NHÓM 7: QUẢN LÝ ĐIỂM DANH (ATTENDANCE)
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "list_attendance_sessions",
            "description": (
                "Lấy danh sách các buổi học / điểm danh trong hệ thống. "
                "Có thể lọc theo ID lớp học (class_id) hoặc ID môn học (course_id). "
                "Dùng khi người dùng hỏi: 'Danh sách các buổi học của lớp HCM-KS26-CNTT1', "
                "'Có những buổi điểm danh nào'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "class_id": {
                        "type": "string",
                        "description": "ID lớp học. Ví dụ: '6aac91736fde2b6e692ed4f8'"
                    },
                    "course_id": {
                        "type": "string",
                        "description": "ID môn học. Ví dụ: '6aad0918f00919310d3f102b'"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_session_roster",
            "description": (
                "Lấy chi tiết danh sách điểm danh (roster) của một buổi học cụ thể theo session_id. "
                "Trả về danh sách sinh viên cùng trạng thái điểm danh (PRESENT, ABSENT, LATE...). "
                "Dùng khi muốn xem điểm danh của một buổi học nhất định."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "ID duy nhất của buổi học điểm danh. Ví dụ: '6ab077dfd2575492aebd621b'"
                    }
                },
                "required": ["session_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_student_attendance",
            "description": (
                "Tra cứu chi tiết lịch sử điểm danh, các ngày nghỉ học (vắng không phép, vắng có phép, đi muộn) "
                "của một sinh viên cụ thể trong toàn bộ các buổi học hoặc theo một môn học nhất định. "
                "DÙNG KHI người dùng hỏi: 'Bùi Gia Anh nghỉ những ngày nào', 'Điểm danh của sinh viên X', "
                "'Sinh viên RE26444 đã nghỉ các buổi nào môn IT108-K26'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "student_id": {
                        "type": "string",
                        "description": "ID duy nhất của sinh viên (MongoDB ObjectId) nếu biết."
                    },
                    "search": {
                        "type": "string",
                        "description": "Họ và tên hoặc Mã sinh viên (Ví dụ: 'Bùi Gia Anh' hoặc 'RK2600063')"
                    },
                    "course_id": {
                        "type": "string",
                        "description": "Tùy chọn: ID môn học nếu chỉ muốn lọc ngày nghỉ theo 1 môn cụ thể (Ví dụ: '6a88fb77a493e63f11a75432')"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_class_attendance_summary",
            "description": (
                "Báo cáo tổng hợp tình hình điểm danh / chuyên cần của toàn bộ sinh viên trong lớp học. "
                "Tự động quét tất cả các buổi học của lớp (hoặc theo môn học), thống kê tổng số buổi có mặt, "
                "nghỉ có phép và nghỉ KHÔNG PHÉP (ABSENT_UNEXCUSED) của từng sinh viên. "
                "Đặc biệt tự động lọc ra danh sách các sinh viên nghỉ không phép nhiều nhất hoặc nghỉ quá số buổi quy định. "
                "DÙNG KHI người dùng hỏi: 'Sinh viên nào nghỉ không phép quá 2 buổi', 'Tình hình điểm danh lớp HCM-KS26-CNTT1', "
                "'Ai vắng học nhiều nhất trong lớp', 'Danh sách chuyên cần toàn lớp'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "class_id": {
                        "type": "string",
                        "description": "ID duy nhất của lớp học (Ví dụ: '6aac91736fde2b6e692ed4f8')"
                    },
                    "class_name": {
                        "type": "string",
                        "description": "Tên hoặc mã lớp học nếu chưa có class_id (Ví dụ: 'HCM-KS26-CNTT1')"
                    },
                    "course_id": {
                        "type": "string",
                        "description": "Tùy chọn: ID môn học nếu chỉ muốn lọc điểm danh theo 1 môn cụ thể (Ví dụ: '6a88fb77a493e63f11a75432')"
                    },
                    "min_unexcused": {
                        "type": "integer",
                        "description": "Tùy chọn: Số buổi nghỉ không phép tối thiểu cần lọc (Mặc định: 1, nếu tìm > 2 buổi thì truyền 3)"
                    }
                },
                "required": []
            }
        }
    },

    # -----------------------------------------------------------------------
    # NHÓM 8: QUẢN LÝ BÀI TẬP VỀ NHÀ (HOMEWORK & SUBMISSIONS)
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "get_homework_session_detail",
            "description": (
                "Lấy thông tin đề bài tập về nhà, mô tả yêu cầu, và đáp án/tiêu chí chấm điểm (gradingCriteria) "
                "của một buổi học theo session_id. "
                "Dùng khi người dùng hỏi: 'Đề bài tập buổi 1 là gì', 'Tiêu chí chấm điểm bài tập session X'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "ID duy nhất của buổi học (sessionId). Ví dụ: '6aae2d7f051be35c19c09b49'"
                    }
                },
                "required": ["session_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_homework_submissions",
            "description": (
                "Lấy danh sách tình hình nộp bài tập về nhà của toàn bộ sinh viên trong lớp theo session_id và class_id. "
                "Trả về danh sách sinh viên cùng trạng thái nộp bài (COMPLETED/chưa nộp), link nộp bài (Docs/Github), thời gian nộp. "
                "Dùng khi người dùng hỏi: 'Danh sách nộp bài tập buổi 1 của lớp HCM-KS26-CNTT1', "
                "'Có bao nhiêu sinh viên đã làm bài tập'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "ID buổi học. Ví dụ: '6aae2d7f051be35c19c09b49'"
                    },
                    "class_id": {
                        "type": "string",
                        "description": "ID lớp học. Ví dụ: '6aac91736fde2b6e692ed4f8'"
                    }
                },
                "required": ["session_id", "class_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_student_homework_status",
            "description": (
                "Kểm tra trạng thái nộp bài tập về nhà của một sinh viên cụ thể trong một buổi học. "
                "Dùng khi người dùng hỏi: 'Phan Gia Hiển đã nộp bài tập buổi 1 chưa', "
                "'Link bài nộp của sinh viên RE26444'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "ID buổi học. Ví dụ: '6aae2d7f051be35c19c09b49'"
                    },
                    "class_id": {
                        "type": "string",
                        "description": "ID lớp học. Ví dụ: '6aac91736fde2b6e692ed4f8'"
                    },
                    "search": {
                        "type": "string",
                        "description": "Tên hoặc Mã sinh viên (Ví dụ: 'Phan Gia Hiển' hoặc 'RE26444')"
                    }
                },
                "required": ["session_id", "class_id", "search"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_homework",
            "description": (
                "Tạo mới bài tập về nhà cho một buổi học trên hệ thống LMS Rikkei. "
                "Có thể truyền session_id của buổi học, tiêu đề, mô tả đề bài, tiêu chí chấm điểm (gradingCriteria), "
                "độ khó (EASY, MEDIUM, HARD), thời lượng dự kiến (phút) và số lần tối đa AI chấm bài. "
                "Dùng khi người dùng yêu cầu: 'Tạo bài tập về nhà cho buổi 1', 'Thêm bài tập session X', "
                "'Giao bài tập về nhà cho lớp'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "ID duy nhất của buổi học (có thể là sessionId của giáo trình hoặc attendanceSessionId)."
                    },
                    "title": {
                        "type": "string",
                        "description": "Tiêu đề bài tập về nhà (Ví dụ: 'BÀI TẬP VỀ NHÀ SESSION 01: Học tập chủ động')."
                    },
                    "description": {
                        "type": "string",
                        "description": "Nội dung chi tiết đề bài, tình huống thực tế hoặc các câu hỏi nhiệm vụ sinh viên cần hoàn thành."
                    },
                    "grading_criteria": {
                        "type": "string",
                        "description": "Tiêu chí chấm điểm, rubric phân bổ điểm (thang điểm 100), hoặc đáp án/hướng dẫn chấm cho AI."
                    },
                    "difficulty_level": {
                        "type": "string",
                        "enum": ["EASY", "MEDIUM", "HARD"],
                        "description": "Mức độ khó của bài tập: EASY (Dễ), MEDIUM (Trung bình), HARD (Khó). Mặc định là MEDIUM."
                    },
                    "expected_time": {
                        "type": "integer",
                        "description": "Thời gian dự kiến hoàn thành bài tập tính theo phút (Ví dụ: 60)."
                    },
                    "max_ai_grade_attempts": {
                        "type": "integer",
                        "description": "Số lần tối đa sinh viên được AI chấm thử lại (mặc định là 3)."
                    }
                },
                "required": ["session_id", "title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_homework",
            "description": (
                "Chỉnh sửa hoặc cập nhật nội dung bài tập về nhà đã tồn tại trên LMS Rikkei. "
                "Cho phép cập nhật tiêu đề, nội dung đề bài, tiêu chí chấm điểm, độ khó hoặc thời gian làm bài. "
                "Chỉ cần truyền homework_id hoặc session_id (hệ thống sẽ tự tìm bài tập của buổi học đó). "
                "Dùng khi người dùng yêu cầu: 'Sửa bài tập buổi 1', 'Cập nhật tiêu chí chấm điểm bài tập', "
                "'Thay đổi deadline/thời gian làm bài tập session X'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "homework_id": {
                        "type": "string",
                        "description": "ID duy nhất của bài tập về nhà (_id) nếu đã biết."
                    },
                    "session_id": {
                        "type": "string",
                        "description": "ID của buổi học nếu không biết homework_id (hệ thống sẽ tự động tra cứu bài tập của buổi học này)."
                    },
                    "title": {
                        "type": "string",
                        "description": "Tiêu đề mới của bài tập (để trống nếu không muốn thay đổi)."
                    },
                    "description": {
                        "type": "string",
                        "description": "Nội dung mô tả / đề bài mới (để trống nếu không muốn thay đổi)."
                    },
                    "grading_criteria": {
                        "type": "string",
                        "description": "Tiêu chí chấm điểm mới (để trống nếu không muốn thay đổi)."
                    },
                    "difficulty_level": {
                        "type": "string",
                        "enum": ["EASY", "MEDIUM", "HARD"],
                        "description": "Mức độ khó mới (EASY, MEDIUM, HARD)."
                    },
                    "expected_time": {
                        "type": "integer",
                        "description": "Thời gian dự kiến làm bài mới tính theo phút."
                    },
                    "max_ai_grade_attempts": {
                        "type": "integer",
                        "description": "Số lần tối đa AI chấm bài mới."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_homework",
            "description": (
                "Xóa bài tập về nhà của một buổi học trên hệ thống LMS Rikkei. "
                "Chỉ định homework_id hoặc session_id của buổi học cần xóa bài tập. "
                "Dùng khi người dùng yêu cầu: 'Xóa bài tập về nhà buổi 1', 'Hủy bài tập session X'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "homework_id": {
                        "type": "string",
                        "description": "ID duy nhất của bài tập về nhà (_id) cần xóa."
                    },
                    "session_id": {
                        "type": "string",
                        "description": "ID của buổi học cần xóa bài tập nếu không có homework_id."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_submission_feedback",
            "description": (
                "Chỉnh sửa hoặc cập nhật nhận xét đánh giá của AI (aiSummary), điểm số (aiScore) và kết quả (aiDecision: PASS/FAIL) "
                "cho bài nộp bài tập về nhà của sinh viên trên LMS Rikkei. "
                "Có thể truyền trực tiếp submission_id, hoặc cung cấp (session_id, class_id, student_search) "
                "để hệ thống tự động tra cứu bài nộp của sinh viên đó. "
                "Dùng khi người dùng yêu cầu: 'Sửa nhận xét bài tập của sinh viên X', 'Chấm điểm lại cho bài tập của Y', "
                "'Cập nhật aiSummary và aiScore cho bài nộp'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "submission_id": {
                        "type": "string",
                        "description": "ID bài nộp của sinh viên (latestSubmissionId hoặc submissionId)."
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Tùy chọn: ID của buổi học (dùng để tự tìm bài nộp nếu chưa có submission_id)."
                    },
                    "class_id": {
                        "type": "string",
                        "description": "Tùy chọn: ID của lớp học (dùng để tự tìm bài nộp nếu chưa có submission_id)."
                    },
                    "student_search": {
                        "type": "string",
                        "description": "Tùy chọn: Tên hoặc mã sinh viên (dùng để tự tìm bài nộp nếu chưa có submission_id)."
                    },
                    "ai_summary": {
                        "type": "string",
                        "description": "Nội dung văn bản nhận xét mới dành cho bài làm của sinh viên."
                    },
                    "ai_score": {
                        "type": "number",
                        "description": "Điểm số mới cho bài tập của sinh viên (Ví dụ: 90 hoặc 8.5)."
                    },
                    "ai_decision": {
                        "type": "string",
                        "enum": ["PASS", "FAIL", "NOT_PASS"],
                        "description": "Kết quả đánh giá: 'PASS' (Đạt) hoặc 'FAIL' / 'NOT_PASS' (Không đạt)."
                    }
                },
                "required": []
            }
        }
    },

    # -----------------------------------------------------------------------
    # NHÓM 9: CHỈ SỐ ĐÀO TẠO, ĐIỂM RPOINT & ĐIỀU KIỆN THI
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "get_student_training_metrics",
            "description": (
                "Tra cứu chi tiết toàn bộ các chỉ số đào tạo của một sinh viên trong một môn học / lớp học: "
                "Điểm rPoint (totalScore, baseScore), tỷ lệ nghỉ học (absenceRate %), tỷ lệ nộp bài tập (submissionRate %), "
                "điểm chuẩn bị bài (preparationScore), điểm chuyên cần (attendanceScore), điểm bài tập (assignmentScore), "
                "điểm tuân thủ (complianceScore), và điều kiện dự thi (examEligible: Đạt / Không đạt kèm chi tiết từng tiêu chí). "
                "Hỗ trợ tìm kiếm thông minh bằng tên/mã sinh viên, tên/mã lớp học và tên môn học. "
                "Dùng khi người dùng hỏi: 'Điểm rPoint của sinh viên X là bao nhiêu', 'Tỷ lệ nghỉ học của X', "
                "'Điểm chuẩn bị bài của X', 'X có đủ điều kiện thi môn này không', 'Xem bảng chỉ số đào tạo của X'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "student_search": {
                        "type": "string",
                        "description": "Tên hoặc mã sinh viên (Ví dụ: 'Phạm Đăng Khoa', 'N26DTCN049', 'Nguyễn Vũ Quốc Anh')"
                    },
                    "student_id": {
                        "type": "string",
                        "description": "ID sinh viên nếu đã biết (Ví dụ: '6aa9f0c2bd4a73a68ce4bce7')"
                    },
                    "class_name": {
                        "type": "string",
                        "description": "Tên hoặc mã lớp học (Ví dụ: 'HCM-KS26-CNTT1', 'HCM-KS26-CNTT2')"
                    },
                    "class_id": {
                        "type": "string",
                        "description": "ID lớp học nếu đã biết"
                    },
                    "course_name": {
                        "type": "string",
                        "description": "Tên hoặc mã môn học (Ví dụ: 'Nhập Môn Công Nghệ Thông Tin'). Nếu để trống hệ thống sẽ tự lấy môn học hiện tại của lớp."
                    },
                    "course_id": {
                        "type": "string",
                        "description": "ID môn học nếu đã biết"
                    }
                },
                "required": ["student_search"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_class_training_metrics",
            "description": (
                "Báo cáo và thống kê các chỉ số đào tạo tổng hợp của cả lớp trong một môn học: "
                "Điểm rPoint trung bình, tỷ lệ nghỉ học trung bình, điểm chuẩn bị bài trung bình, tỷ lệ nộp bài trung bình, "
                "số lượng sinh viên đủ điều kiện thi / nguy cơ cấm thi, và danh sách chi tiết các sinh viên (rPoint, vắng học %, chuẩn bị bài, nộp bài, điều kiện thi). "
                "Dùng khi người dùng hỏi: 'Tình hình rPoint của lớp', 'Thống kê tỷ lệ nghỉ học của lớp HCM-KS26-CNTT2', "
                "'Lớp có bao nhiêu bạn chuẩn bị bài tốt', 'Danh sách đủ điều kiện thi môn CNTT'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "class_name": {
                        "type": "string",
                        "description": "Tên hoặc mã lớp học (Ví dụ: 'HCM-KS26-CNTT1', 'HCM-KS26-CNTT2')"
                    },
                    "class_id": {
                        "type": "string",
                        "description": "ID lớp học nếu đã biết"
                    },
                    "course_name": {
                        "type": "string",
                        "description": "Tên môn học (Ví dụ: 'Nhập Môn Công Nghệ Thông Tin'). Nếu để trống sẽ lấy môn học chính của lớp."
                    },
                    "course_id": {
                        "type": "string",
                        "description": "ID môn học nếu đã biết"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Số lượng sinh viên hiển thị chi tiết (mặc định 20)."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_course_class_roster",
            "description": (
                "Lấy danh sách sinh viên ghi danh chính thức trong một lớp học môn học (course-class roster). "
                "Bao gồm họ tên, mã sinh viên, email, trạng thái học tập (STUDYING), thời điểm ghi danh. "
                "Dùng khi người dùng hỏi: 'Danh sách sinh viên học môn Nhập môn CNTT lớp X', 'Roster lớp môn học'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "class_name": {
                        "type": "string",
                        "description": "Tên hoặc mã lớp học"
                    },
                    "class_id": {
                        "type": "string",
                        "description": "ID lớp học"
                    },
                    "course_name": {
                        "type": "string",
                        "description": "Tên môn học"
                    },
                    "course_id": {
                        "type": "string",
                        "description": "ID môn học"
                    }
                },
                "required": []
            }
        }
    },
]


# ===========================================================================
# II. LỚP THỰC THI HÀM (Function Executor)
# ===========================================================================

class LMSFunctionExecutor:
    """
    Thực thi các function call từ AI Agent.
    Nhận tên hàm + tham số, gọi API tương ứng, trả về kết quả chuẩn hoá.
    """

    def __init__(self):
        self._api = RikkeiPortalAPI()
        # Không xác thực ngay — lazy auth khi gọi API đầu tiên
        # Điều này cho phép server khởi động ngay kể cả khi token hết hạn

    def _get(self, path: str, params: dict = None) -> dict:
        url = BASE_URL + path
        resp = self._api._make_request("GET", url, params=params or {})
        return resp.json()

    def _post(self, path: str, payload: dict = None) -> dict:
        url = BASE_URL + path
        resp = self._api._make_request("POST", url, json=payload or {})
        if resp.status_code == 204:
            return {"success": True, "message": "Thực thi thành công (No Content)"}
        return resp.json()

    def _patch(self, path: str, payload: dict = None) -> dict:
        url = BASE_URL + path
        resp = self._api._make_request("PATCH", url, json=payload or {})
        if resp.status_code == 204:
            return {"success": True, "message": "Cập nhật thành công (No Content)"}
        try:
            return resp.json()
        except Exception:
            return {"statusCode": resp.status_code, "text": resp.text}

    def _delete(self, path: str) -> dict:
        url = BASE_URL + path
        resp = self._api._make_request("DELETE", url)
        if resp.status_code == 204:
            return {"success": True, "message": "Xóa thành công (No Content)"}
        try:
            return resp.json()
        except Exception:
            return {"statusCode": resp.status_code, "text": resp.text}

    # --- NHÓM 1: HỒ SƠ ---

    def get_my_profile(self) -> dict:
        """Lấy thông tin hồ sơ cá nhân của người dùng đang đăng nhập (ĐÃ VÔ HIỆU HÓA)."""
        return {
            "statusCode": 403,
            "message": "Tính năng xem thông tin cá nhân đã bị vô hiệu hóa vì lý do bảo mật và quyền riêng tư."
        }

    # --- NHÓM 2: HỆ THỐNG ĐÀO TẠO ---

    def list_training_systems(self) -> dict:
        """Liệt kê tất cả hệ thống/chương trình đào tạo."""
        return self._get("/api/systems")

    def get_training_system_detail(self, system_id: str) -> dict:
        """Chi tiết một hệ thống đào tạo theo ID."""
        return self._get(f"/api/systems/{system_id}")

    # --- NHÓM 3: LỚP HỌC ---

    def list_classes(self, limit: int = 20, offset: int = 0, search: str = None) -> dict:
        """Danh sách lớp học với tuỳ chọn tìm kiếm."""
        params = {"limit": limit, "offset": offset}
        if search:
            params["search"] = search
        return self._get("/api/staff/classes", params)

    def get_class_detail(self, class_id: str) -> dict:
        """Chi tiết một lớp học theo ID."""
        return self._get(f"/api/staff/classes/{class_id}")

    # --- NHÓM 4: KHOÁ HỌC ---

    def list_courses(self, limit: int = 50, offset: int = 0) -> dict:
        """Danh sách tất cả khoá học/môn học."""
        return self._get("/api/staff/courses", {"limit": limit, "offset": offset})

    def get_course_detail(self, course_id: str) -> dict:
        """Chi tiết khoá học theo ID, bao gồm công thức tính điểm."""
        return self._get(f"/api/staff/courses/{course_id}")

    # --- NHÓM 5: SINH VIÊN ---

    def list_students(
        self,
        limit: int = 20,
        offset: int = 0,
        system_id: str = None,
        search: str = None,
        status: str = None,
        location: str = None,
        class_id: str = None,
        class_name: str = None
    ) -> dict:
        """Danh sách sinh viên với nhiều bộ lọc. Hỗ trợ lọc theo lớp học, tên hoặc mã sinh viên."""
        # --- Trường hợp lọc theo lớp học (class_id hoặc class_name) ---
        if class_id or class_name:
            if not class_id and class_name:
                c_res = self.list_classes(search=class_name.strip(), limit=10)
                c_items = c_res.get("data", {}).get("items", []) if isinstance(c_res.get("data"), dict) else []
                matched = [c for c in c_items if c.get("classCode") == class_name.strip() or c.get("name") == class_name.strip()]
                if not matched:
                    matched = [c for c in c_items if class_name.strip().lower() in (c.get("classCode") or "").lower() or class_name.strip().lower() in (c.get("name") or "").lower()]
                if matched:
                    class_id = matched[0]["id"]
                    class_name = matched[0].get("classCode") or matched[0].get("name")

            if class_id:
                # Quét roster từ các buổi học của lớp để lấy danh sách sinh viên thực tế thuộc lớp
                sess_res = self.list_attendance_sessions(class_id=class_id)
                sessions = sess_res.get("data", []) if isinstance(sess_res.get("data"), list) else []
                if sessions:
                    sid = sessions[0].get("_id")
                    roster_res = self.get_session_roster(sid)
                    roster = roster_res.get("data", {}).get("roster", []) if isinstance(roster_res.get("data"), dict) else []
                    
                    students = []
                    for r in roster:
                        st = {
                            "id": r.get("studentId"),
                            "studentCode": r.get("studentCode"),
                            "fullName": r.get("fullName"),
                            "className": class_name or "N/A",
                            "classId": class_id,
                            "status": "ĐANG HỌC"
                        }
                        if search:
                            q = search.strip().lower()
                            if q not in (st["fullName"] or "").lower() and q not in (st["studentCode"] or "").lower():
                                continue
                        students.append(st)

                    total_count = len(students)
                    paged = students[offset : offset + limit] if (limit and limit > 0) else students
                    return {
                        "statusCode": 200,
                        "data": {
                            "class_id": class_id,
                            "class_name": class_name,
                            "total": total_count,
                            "page": (offset // limit) + 1 if limit else 1,
                            "limit": limit,
                            "items": paged
                        }
                    }

        params = {"limit": limit, "offset": offset}
        if system_id:
            params["systemId"] = system_id
        if status:
            params["status"] = status
        if location:
            params["location"] = location

        if search:
            clean_search = search.strip()
            # 1. Thử tìm kiếm theo fullName/name
            res_name = self._get("/api/students", {**params, "name": clean_search})
            items_name = res_name.get("data", {}).get("items", []) if isinstance(res_name.get("data"), dict) else []
            if items_name:
                return res_name

            # 2. Thử tìm kiếm theo studentCode
            res_code = self._get("/api/students", {**params, "studentCode": clean_search})
            items_code = res_code.get("data", {}).get("items", []) if isinstance(res_code.get("data"), dict) else []
            if items_code:
                return res_code

            # 3. Fallback: gửi name=search
            params["name"] = clean_search
            return self._get("/api/students", params)

        return self._get("/api/students", params)

    def get_student_detail(self, student_id: str) -> dict:
        """Chi tiết một sinh viên theo ID."""
        return self._get(f"/api/students/{student_id}")

    # --- NHÓM 6: THÔNG BÁO ---

    def list_sent_notifications(self, limit: int = 10, offset: int = 0) -> dict:
        """Danh sách thông báo đã gửi."""
        return self._get("/api/staff/notifications", {"limit": limit, "offset": offset})

    def list_received_notifications(self, limit: int = 10, offset: int = 0) -> dict:
        """Danh sách thông báo nhận được (đơn nghỉ phép, v.v.)."""
        return self._get("/api/staff/notifications/received", {"limit": limit, "offset": offset})

    def send_notification(
        self,
        title: str,
        message: str,
        target_student_ids: list,
        body: list = None
    ) -> dict:
        """Gửi thông báo đến các sinh viên được chỉ định."""
        payload = {
            "title": title,
            "message": message,
            "targetStudentIds": target_student_ids,
        }
        if body:
            payload["body"] = body
        return self._post("/api/staff/notifications", payload)

    # --- NHÓM 7: ĐIỂM DANH ---

    def list_attendance_sessions(self, class_id: str = None, course_id: str = None) -> dict:
        """Lấy danh sách các buổi điểm danh (sessions)."""
        params = {}
        if class_id:
            params["classId"] = class_id
        if course_id:
            params["courseId"] = course_id
        return self._get("/api/staff/attendance/sessions", params)

    def get_session_roster(self, session_id: str) -> dict:
        """Lấy danh sách chi tiết điểm danh của 1 buổi học theo session_id."""
        return self._get(f"/api/staff/attendance/sessions/{session_id}/roster")

    def get_student_attendance(
        self,
        student_id: str = None,
        search: str = None,
        course_id: str = None
    ) -> dict:
        """Tra cứu lịch sử điểm danh và danh sách ngày nghỉ chi tiết của một sinh viên."""
        from concurrent.futures import ThreadPoolExecutor

        # 1. Tìm thông tin sinh viên
        target_student = {}
        if not student_id and search:
            st_res = self.list_students(search=search.strip(), limit=5)
            items = st_res.get("data", {}).get("items", []) if isinstance(st_res.get("data"), dict) else []
            # Ưu tiên khớp chính xác tên hoặc mã sinh viên
            matched = [s for s in items if s.get("fullName") == search.strip() or s.get("studentCode") == search.strip()]
            target_student = matched[0] if matched else (items[0] if items else {})
            if target_student:
                student_id = target_student.get("id")
            else:
                return {"error": f"Không tìm thấy sinh viên khớp với từ khoá '{search}'."}
        elif student_id:
            st_detail = self.get_student_detail(student_id)
            target_student = st_detail.get("data", {})
        else:
            return {"error": "Cần cung cấp student_id hoặc từ khoá search."}

        # 2. Tìm lớp của sinh viên
        class_name = target_student.get("className")
        class_id = None
        if class_name:
            classes_res = self.list_classes(search=class_name, limit=10)
            c_items = classes_res.get("data", {}).get("items", []) if isinstance(classes_res.get("data"), dict) else []
            matched = [c for c in c_items if c.get("classCode") == class_name or c.get("name") == class_name]
            if matched:
                class_id = matched[0]["id"]

        # 3. Lấy danh sách sessions (lọc theo course_id nếu có)
        sess_params = {"class_id": class_id}
        if course_id:
            sess_params["course_id"] = course_id
        sessions_res = self.list_attendance_sessions(**sess_params)
        sessions = sessions_res.get("data", []) if isinstance(sessions_res.get("data"), list) else []

        if not sessions:
            return {
                "student": {
                    "id": student_id,
                    "fullName": target_student.get("fullName"),
                    "studentCode": target_student.get("studentCode"),
                    "className": target_student.get("className")
                },
                "total_sessions_checked": 0,
                "message": "Không tìm thấy buổi học điểm danh nào."
            }

        # Tra cứu thông tin tên môn học để hiển thị rõ ràng
        course_ids = list(set(s.get("courseId") for s in sessions if s.get("courseId")))
        course_name_map = {}
        for cid in course_ids:
            c_res = self.get_course_detail(cid)
            c_name = c_res.get("data", {}).get("name") or cid
            c_code = c_res.get("data", {}).get("courseCode") or ""
            course_name_map[cid] = f"{c_name} ({c_code})" if c_code else c_name

        # 4. Quét roster song song bằng ThreadPoolExecutor
        def _check_session(sess):
            sid = sess.get("_id")
            date = (sess.get("date") or "")[:10]
            meta = sess.get("sessionId", {})
            lesson = meta.get("name", "N/A") if isinstance(meta, dict) else str(meta)
            cid = sess.get("courseId")
            c_title = course_name_map.get(cid, "Chưa phân môn")

            r_data = self.get_session_roster(sid)
            roster = r_data.get("data", {}).get("roster", []) if isinstance(r_data, dict) else []
            for item in roster:
                if item.get("studentId") == student_id or item.get("studentCode") == target_student.get("studentCode"):
                    return {
                        "date": date,
                        "lesson_name": lesson,
                        "course_name": c_title,
                        "status": item.get("status"), # PRESENT, ABSENT_UNEXCUSED, ABSENT_EXCUSED, LATE
                        "note": item.get("note") or ""
                    }
            return None

        with ThreadPoolExecutor(max_workers=8) as pool:
            records = [r for r in pool.map(_check_session, sessions) if r]

        # Sắp xếp theo ngày giảm dần (buổi gần nhất lên đầu)
        records.sort(key=lambda x: x["date"], reverse=True)

        absent_unexcused = [r for r in records if r["status"] == "ABSENT_UNEXCUSED"]
        absent_excused = [r for r in records if r["status"] == "ABSENT_EXCUSED"]
        late_records = [r for r in records if r["status"] == "LATE"]
        present_records = [r for r in records if r["status"] == "PRESENT"]

        return {
            "student": {
                "id": student_id,
                "fullName": target_student.get("fullName"),
                "studentCode": target_student.get("studentCode"),
                "className": target_student.get("className")
            },
            "total_sessions_checked": len(sessions),
            "summary": {
                "absent_unexcused_count": len(absent_unexcused),
                "absent_excused_count": len(absent_excused),
                "late_count": len(late_records),
                "present_count": len(present_records)
            },
            "absent_unexcused_dates": absent_unexcused,
            "absent_excused_dates": absent_excused,
            "late_dates": late_records,
            "recent_records": records[:10]
        }

    def get_class_attendance_summary(
        self,
        class_id: str = None,
        class_name: str = None,
        course_id: str = None,
        min_unexcused: int = 1
    ) -> dict:
        """
        Báo cáo tổng hợp tình hình điểm danh / chuyên cần của toàn bộ sinh viên trong lớp học.
        Tự động quét tất cả các buổi học của lớp bằng đa luồng song song, tính tổng số buổi
        có mặt, nghỉ có phép, nghỉ không phép của từng sinh viên.
        """
        from concurrent.futures import ThreadPoolExecutor

        # 1. Nếu chưa có class_id, tìm theo class_name
        if not class_id and class_name:
            classes_res = self.list_classes(search=class_name, limit=10)
            c_items = classes_res.get("data", {}).get("items", [])
            matched = [c for c in c_items if c.get("classCode") == class_name or c.get("name") == class_name]
            if not matched:
                matched = [c for c in c_items if class_name.lower() in (c.get("classCode") or "").lower() or class_name.lower() in (c.get("name") or "").lower()]
            if matched:
                class_id = matched[0]["id"]
                class_name = matched[0].get("classCode") or matched[0].get("name")

        if not class_id:
            return {"error": "Không tìm thấy mã hoặc ID lớp học tương ứng."}

        # 2. Lấy danh sách sessions của lớp
        sess_params = {"class_id": class_id}
        if course_id:
            sess_params["course_id"] = course_id
        sessions_res = self.list_attendance_sessions(**sess_params)
        sessions = sessions_res.get("data", []) if isinstance(sessions_res.get("data"), list) else []

        if not sessions:
            return {
                "class_id": class_id,
                "class_name": class_name,
                "total_sessions": 0,
                "message": "Không có buổi học điểm danh nào được ghi nhận cho lớp này."
            }

        # 3. Quét roster song song bằng ThreadPoolExecutor
        def _fetch_roster(sess):
            sid = sess.get("_id")
            meta = sess.get("sessionId", {})
            name = meta.get("name", "N/A") if isinstance(meta, dict) else str(meta)
            date = (sess.get("date") or "")[:10]
            period = sess.get("period")
            c_id = sess.get("courseId")

            r_data = self.get_session_roster(sid)
            roster = []
            if isinstance(r_data, dict) and r_data.get("statusCode") == 200:
                roster = r_data.get("data", {}).get("roster", [])

            return {
                "session_id": sid,
                "date": date,
                "period": period,
                "lesson": name,
                "course_id": c_id,
                "roster": roster
            }

        with ThreadPoolExecutor(max_workers=8) as pool:
            fetched_results = list(pool.map(_fetch_roster, sessions))

        # 4. Thống kê theo từng sinh viên
        students_map = {}
        for f_res in fetched_results:
            date = f_res["date"]
            lesson = f_res["lesson"]
            for item in f_res["roster"]:
                stu_id = item.get("studentId")
                code = item.get("studentCode") or "N/A"
                name = item.get("fullName") or "N/A"
                status = item.get("status")

                if stu_id not in students_map:
                    students_map[stu_id] = {
                        "studentId": stu_id,
                        "studentCode": code,
                        "fullName": name,
                        "present_count": 0,
                        "excused_count": 0,
                        "unexcused_count": 0,
                        "unexcused_details": []
                    }

                if status in ("PRESENT", "LATE"):
                    students_map[stu_id]["present_count"] += 1
                elif status == "ABSENT_EXCUSED":
                    students_map[stu_id]["excused_count"] += 1
                elif status == "ABSENT_UNEXCUSED":
                    students_map[stu_id]["unexcused_count"] += 1
                    students_map[stu_id]["unexcused_details"].append({
                        "date": date,
                        "lesson": lesson
                    })

        all_students = list(students_map.values())
        all_students.sort(key=lambda x: -x["unexcused_count"])

        # Thu thập danh sách các môn học xuất hiện trong các buổi học của lớp
        course_ids = list(set(s.get("courseId") for s in sessions if s.get("courseId")))
        available_courses = []
        for cid in course_ids:
            c_res = self.get_course_detail(cid)
            c_name = c_res.get("data", {}).get("name") or cid
            c_code = c_res.get("data", {}).get("courseCode") or ""
            sess_count = sum(1 for s in sessions if s.get("courseId") == cid)
            available_courses.append({
                "course_id": cid,
                "course_name": f"{c_name} ({c_code})" if c_code else c_name,
                "sessions_count": sess_count
            })

        # Lọc danh sách sinh viên vi phạm / nghỉ không phép
        threshold = min_unexcused if min_unexcused is not None else 1
        flagged_students = [st for st in all_students if st["unexcused_count"] >= threshold]

        return {
            "class_id": class_id,
            "class_name": class_name,
            "total_sessions_scanned": len(sessions),
            "total_students": len(all_students),
            "available_courses": available_courses,
            "filter_min_unexcused": threshold,
            "flagged_count": len(flagged_students),
            "flagged_students": flagged_students[:20],
            "top_summary": [
                {
                    "code": st["studentCode"],
                    "name": st["fullName"],
                    "unexcused": st["unexcused_count"],
                    "present": st["present_count"],
                    "excused": st["excused_count"]
                }
                for st in all_students[:10]
            ]
        }

    # --- NHÓM 8: BÀI TẬP VỀ NHÀ (HOMEWORK) ---

    def get_homework_session_detail(self, session_id: str) -> dict:
        """Lấy chi tiết đề bài tập về nhà và tiêu chí chấm điểm của buổi học."""
        return self._get(f"/api/homework/session/{session_id}")

    def list_homework_submissions(self, session_id: str, class_id: str) -> dict:
        """Lấy danh sách nộp bài tập về nhà của lớp theo buổi học và tính toán thống kê chuẩn xác."""
        # 1. Kiểm tra đề bài tập được giao trong buổi này
        hw_detail_res = self.get_homework_session_detail(session_id)
        assigned_tasks = []
        if isinstance(hw_detail_res, dict) and hw_detail_res.get("statusCode") == 200:
            tasks_data = hw_detail_res.get("data", [])
            if isinstance(tasks_data, list):
                assigned_tasks = [
                    {"id": t.get("_id"), "title": t.get("title") or t.get("name")}
                    for t in tasks_data
                ]

        # 2. Lấy danh sách submission từ API
        submissions_raw = self._get(f"/api/homework/completion/session/{session_id}", {"classId": class_id})
        items = submissions_raw.get("data", []) if isinstance(submissions_raw.get("data"), list) else []

        submitted = []
        unsubmitted = []

        for item in items:
            st = item.get("student", {}) or {}
            code = st.get("studentCode") or "N/A"
            name = st.get("fullName") or "N/A"
            status = item.get("status")
            submitted_at = item.get("submittedAt")
            github = item.get("githubUrl")
            ai_score = item.get("aiScore")

            # Học viên được tính là đã nộp khi có status khác null/None hoặc có submittedAt hoặc có link github
            is_submitted = bool(status and status not in ("NOT_SUBMITTED", "NONE")) or bool(submitted_at) or bool(github)

            record = {
                "studentCode": code,
                "fullName": name,
                "submissionId": item.get("latestSubmissionId") or item.get("_id") or item.get("id"),
                "status": status or ("CHƯA_NỘP" if not is_submitted else "ĐÃ_NỘP"),
                "submittedAt": format_vietnam_time(submitted_at),
                "aiScore": ai_score,
                "aiSummary": item.get("aiSummary"),
                "aiDecision": item.get("aiDecision"),
                "githubUrl": github
            }

            if is_submitted:
                submitted.append(record)
            else:
                unsubmitted.append(record)

        return {
            "session_id": session_id,
            "class_id": class_id,
            "has_assigned_homework": len(assigned_tasks) > 0,
            "assigned_tasks_count": len(assigned_tasks),
            "assigned_tasks": assigned_tasks,
            "total_students": len(items),
            "submitted_count": len(submitted),
            "unsubmitted_count": len(unsubmitted),
            "submitted_students": submitted,
            "unsubmitted_students": unsubmitted,
            "system_note": "Nếu has_assigned_homework là false hoặc submitted_count là 0, hãy thông báo trung thực là buổi này chưa có bài tập được giao hoặc chưa có sinh viên nào nộp trên LMS, tuyệt đối không bịa số liệu."
        }

    def get_student_homework_status(self, session_id: str, class_id: str, search: str) -> dict:
        """Kiểm tra tình hình nộp bài tập của 1 sinh viên cụ thể trong buổi học."""
        submissions_raw = self._get(f"/api/homework/completion/session/{session_id}", {"classId": class_id})
        items = submissions_raw.get("data", []) if isinstance(submissions_raw.get("data"), list) else []
        
        search_lower = search.lower().strip()
        matched = []
        for s in items:
            st = s.get("student", {}) or {}
            code = (st.get("studentCode") or "").lower()
            name = (st.get("fullName") or "").lower()
            sid  = (st.get("id") or "").lower()
            if search_lower in code or search_lower in name or search_lower in sid:
                matched.append({
                    "studentCode": st.get("studentCode"),
                    "fullName": st.get("fullName"),
                    "email": st.get("email"),
                    "submissionId": s.get("latestSubmissionId") or s.get("_id") or s.get("id"),
                    "status": s.get("status") or "CHƯA NỘP",
                    "submittedAt": format_vietnam_time(s.get("submittedAt")),
                    "githubUrl": s.get("githubUrl"),
                    "aiScore": s.get("aiScore"),
                    "aiSummary": s.get("aiSummary"),
                    "aiDecision": s.get("aiDecision"),
                    "checkedAt": format_vietnam_time(s.get("checkedAt"))
                })
        
        return {
            "search": search,
            "session_id": session_id,
            "class_id": class_id,
            "found": len(matched),
            "results": matched
        }

    def _resolve_syllabus_session_id(self, session_id: str) -> str:
        """
        Xác định chính xác sessionId của giáo trình môn học.
        Nếu truyền vào attendanceSessionId, tự động tra cứu để lấy course sessionId tương ứng.
        """
        if not session_id:
            return session_id
        try:
            roster_res = self.get_session_roster(session_id)
            if isinstance(roster_res, dict) and roster_res.get("statusCode") == 200:
                sess_obj = roster_res.get("data", {}).get("session", {})
                inner_meta = sess_obj.get("sessionId")
                if isinstance(inner_meta, dict) and inner_meta.get("_id"):
                    return inner_meta["_id"]
        except Exception:
            pass
        return session_id

    def create_homework(
        self,
        session_id: str,
        title: str,
        description: str = "",
        grading_criteria: str = "",
        difficulty_level: str = "MEDIUM",
        expected_time: int = 60,
        max_ai_grade_attempts: int = 3
    ) -> dict:
        """Tạo bài tập về nhà mới cho một buổi học."""
        resolved_sid = self._resolve_syllabus_session_id(session_id)
        payload = {
            "sessionId": resolved_sid,
            "title": title,
            "description": description or "",
            "gradingCriteria": grading_criteria or "",
            "difficultyLevel": (difficulty_level or "MEDIUM").upper(),
            "expectedTime": int(expected_time) if expected_time is not None else 60,
            "maxAiGradeAttempts": int(max_ai_grade_attempts) if max_ai_grade_attempts is not None else 3
        }
        res = self._post("/api/homework", payload)
        if isinstance(res, dict) and res.get("statusCode") in (200, 201):
            return {
                "ok": True,
                "message": f"Tạo bài tập về nhà thành công cho buổi học ({resolved_sid}).",
                "homework": res.get("data", res)
            }
        return {
            "ok": False,
            "error": res.get("message") or res.get("messageCode") or "Không thể tạo bài tập về nhà trên LMS.",
            "raw": res
        }

    def update_homework(
        self,
        homework_id: str = None,
        session_id: str = None,
        title: str = None,
        description: str = None,
        grading_criteria: str = None,
        difficulty_level: str = None,
        expected_time: int = None,
        max_ai_grade_attempts: int = None
    ) -> dict:
        """Chỉnh sửa hoặc cập nhật thông tin bài tập về nhà đã có."""
        hw_id = homework_id
        if not hw_id and session_id:
            resolved_sid = self._resolve_syllabus_session_id(session_id)
            hw_res = self.get_homework_session_detail(resolved_sid)
            hw_data = hw_res.get("data")
            if isinstance(hw_data, list) and len(hw_data) > 0:
                hw_id = hw_data[0].get("_id") or hw_data[0].get("id")
            elif isinstance(hw_data, dict):
                hw_id = hw_data.get("_id") or hw_data.get("id")

        if not hw_id:
            return {"ok": False, "error": "Cần cung cấp homework_id hoặc session_id hợp lệ có bài tập để cập nhật."}

        payload = {}
        if title is not None:
            payload["title"] = title
        if description is not None:
            payload["description"] = description
        if grading_criteria is not None:
            payload["gradingCriteria"] = grading_criteria
        if difficulty_level is not None:
            payload["difficultyLevel"] = difficulty_level.upper()
        if expected_time is not None:
            payload["expectedTime"] = int(expected_time)
        if max_ai_grade_attempts is not None:
            payload["maxAiGradeAttempts"] = int(max_ai_grade_attempts)

        if not payload:
            return {"ok": False, "error": "Không có thông tin nào được chỉ định để cập nhật."}

        res = self._patch(f"/api/homework/{hw_id}", payload)
        if isinstance(res, dict) and res.get("statusCode") == 200:
            return {
                "ok": True,
                "message": f"Cập nhật bài tập về nhà '{hw_id}' thành công.",
                "homework": res.get("data", res)
            }
        return {
            "ok": False,
            "error": res.get("message") or res.get("messageCode") or "Không thể cập nhật bài tập về nhà trên LMS.",
            "raw": res
        }

    def delete_homework(self, homework_id: str = None, session_id: str = None) -> dict:
        """Xóa bài tập về nhà khỏi buổi học."""
        hw_id = homework_id
        if not hw_id and session_id:
            resolved_sid = self._resolve_syllabus_session_id(session_id)
            hw_res = self.get_homework_session_detail(resolved_sid)
            hw_data = hw_res.get("data")
            if isinstance(hw_data, list) and len(hw_data) > 0:
                hw_id = hw_data[0].get("_id") or hw_data[0].get("id")
            elif isinstance(hw_data, dict):
                hw_id = hw_data.get("_id") or hw_data.get("id")

        if not hw_id:
            return {"ok": False, "error": "Cần cung cấp homework_id hoặc session_id có bài tập để xóa."}

        res = self._delete(f"/api/homework/{hw_id}")
        if isinstance(res, dict) and (res.get("statusCode") == 200 or res.get("success")):
            return {
                "ok": True,
                "message": f"Đã xóa bài tập về nhà '{hw_id}' thành công trên LMS."
            }
        return {
            "ok": False,
            "error": res.get("message") or "Không thể xóa bài tập về nhà trên LMS.",
            "raw": res
        }

    def update_submission_feedback(
        self,
        submission_id: str = None,
        session_id: str = None,
        class_id: str = None,
        student_search: str = None,
        ai_summary: str = None,
        ai_score: float = None,
        ai_decision: str = None
    ) -> dict:
        """
        Chỉnh sửa hoặc cập nhật nhận xét đánh giá của AI (aiSummary), điểm số (aiScore) và kết quả (aiDecision)
        cho bài nộp bài tập về nhà của sinh viên trên LMS Rikkei.
        """
        target_sub_id = submission_id

        # Nếu chưa có submission_id nhưng có session_id, class_id và student_search -> tự động tìm
        if not target_sub_id and session_id and (student_search or class_id):
            resolved_sid = self._resolve_syllabus_session_id(session_id)
            params = {}
            if class_id:
                params["classId"] = class_id
            submissions_raw = self._get(f"/api/homework/completion/session/{resolved_sid}", params)
            items = submissions_raw.get("data", []) if isinstance(submissions_raw.get("data"), list) else []

            s_query = (student_search or "").lower().strip()
            for it in items:
                st = it.get("student", {}) or {}
                code = (st.get("studentCode") or "").lower()
                name = (st.get("fullName") or "").lower()
                sid = (st.get("id") or "").lower()
                if not s_query or s_query in code or s_query in name or s_query in sid:
                    target_sub_id = it.get("latestSubmissionId") or it.get("_id") or it.get("id")
                    break

        if not target_sub_id:
            return {
                "ok": False,
                "error": "Cần cung cấp submission_id hoặc bộ tham số (session_id, class_id, student_search) để tìm bài nộp của sinh viên."
            }

        url = f"/api/homework/completion/submission/{target_sub_id}/feedback"
        payload = {}
        if ai_summary is not None:
            payload["aiSummary"] = ai_summary
        if ai_score is not None:
            payload["aiScore"] = float(ai_score)
        if ai_decision is not None:
            payload["aiDecision"] = ai_decision.upper()

        if not payload:
            return {"ok": False, "error": "Cần cung cấp ít nhất một thông tin cần cập nhật (ai_summary, ai_score, ai_decision)."}

        res = self._patch(url, payload)
        if isinstance(res, dict) and res.get("statusCode") == 200:
            return {
                "ok": True,
                "message": f"Cập nhật nhận xét bài nộp '{target_sub_id}' thành công trên LMS.",
                "data": res.get("data", res)
            }
        return {
            "ok": False,
            "error": res.get("message") or res.get("messageCode") or "Không thể cập nhật nhận xét bài nộp trên LMS.",
            "raw": res
        }

    # --- NHÓM 9: CHỈ SỐ ĐÀO TẠO, ĐIỂM RPOINT & ĐIỀU KIỆN THI ---

    def _resolve_course_and_class(self, class_id: str = None, class_name: str = None, course_id: str = None, course_name: str = None) -> tuple:
        """Helper phân giải class_id, class_obj, course_id, course_obj."""
        resolved_class_id = class_id
        resolved_class_name = class_name
        class_obj = {}

        if not resolved_class_id and class_name:
            c_res = self.list_classes(search=class_name.strip(), limit=10)
            c_items = c_res.get("data", {}).get("items", []) if isinstance(c_res.get("data"), dict) else []
            matched = [c for c in c_items if c.get("classCode") == class_name.strip() or c.get("name") == class_name.strip()]
            if not matched:
                matched = [c for c in c_items if class_name.strip().lower() in (c.get("classCode") or "").lower() or class_name.strip().lower() in (c.get("name") or "").lower()]
            if matched:
                resolved_class_id = matched[0]["id"]
                resolved_class_name = matched[0].get("classCode") or matched[0].get("name")
                class_obj = matched[0]

        if resolved_class_id and not class_obj:
            detail_res = self.get_class_detail(resolved_class_id)
            if isinstance(detail_res, dict) and detail_res.get("data"):
                class_obj = detail_res.get("data", {})
                if not resolved_class_name:
                    resolved_class_name = class_obj.get("classCode") or class_obj.get("name")

        resolved_course_id = course_id
        resolved_course_name = course_name

        if not resolved_course_id and course_name:
            courses_res = self.list_courses(limit=50)
            courses_items = courses_res.get("data", {}).get("items", []) if isinstance(courses_res.get("data"), dict) else []
            matched_c = [c for c in courses_items if (c.get("name") or "").lower() == course_name.strip().lower() or (c.get("code") or "").lower() == course_name.strip().lower()]
            if not matched_c:
                matched_c = [c for c in courses_items if course_name.strip().lower() in (c.get("name") or "").lower() or course_name.strip().lower() in (c.get("code") or "").lower()]
            if matched_c:
                resolved_course_id = matched_c[0]["id"]
                resolved_course_name = matched_c[0].get("name")

        # Fallback: nếu chưa có course_id, lấy courseId đầu tiên từ class
        if not resolved_course_id and class_obj and class_obj.get("courseIds"):
            resolved_course_id = class_obj["courseIds"][0]

        if resolved_course_id and not resolved_course_name:
            c_detail = self.get_course_detail(resolved_course_id)
            if isinstance(c_detail, dict) and c_detail.get("data"):
                resolved_course_name = c_detail["data"].get("name")

        return resolved_class_id, resolved_class_name, class_obj, resolved_course_id, resolved_course_name

    def get_course_class_roster(self, class_id: str = None, class_name: str = None, course_id: str = None, course_name: str = None) -> dict:
        """Lấy danh sách sinh viên ghi danh trong lớp học môn học."""
        cid, cname, cobj, crsid, crsname = self._resolve_course_and_class(class_id, class_name, course_id, course_name)
        if not cid or not crsid:
            return {"error": "Không xác định được classId hoặc courseId để lấy danh sách roster.", "classId": cid, "courseId": crsid}

        url = f"/api/staff/course-classes/roster"
        res = self._get(url, {"classId": cid, "courseId": crsid})
        return {
            "statusCode": 200,
            "data": {
                "classId": cid,
                "className": cname,
                "courseId": crsid,
                "courseName": crsname,
                "total": len(res.get("data", [])) if isinstance(res.get("data"), list) else 0,
                "items": res.get("data", [])
            }
        }

    def get_student_training_metrics(
        self,
        student_search: str = None,
        student_id: str = None,
        class_id: str = None,
        class_name: str = None,
        course_id: str = None,
        course_name: str = None
    ) -> dict:
        """Tra cứu chi tiết toàn bộ chỉ số đào tạo của một sinh viên (rPoint, nghỉ học, chuẩn bị bài, nộp bài, điều kiện thi)."""
        cid, cname, cobj, crsid, crsname = self._resolve_course_and_class(class_id, class_name, course_id, course_name)
        
        target_student_id = student_id
        student_info = {}

        # Nếu chưa có student_id, tìm qua student_search
        if not target_student_id and student_search:
            # 1. Thử tìm trong roster nếu có cid & crsid
            if cid and crsid:
                roster_res = self.get_course_class_roster(class_id=cid, course_id=crsid)
                items = roster_res.get("data", {}).get("items", [])
                q = student_search.strip().lower()
                for it in items:
                    st = it.get("student", {})
                    if q == (st.get("studentCode") or "").lower() or q in (st.get("fullName") or "").lower():
                        target_student_id = st.get("id")
                        student_info = st
                        break
            
            # 2. Nếu chưa tìm thấy, gọi list_students
            if not target_student_id:
                s_res = self.list_students(search=student_search, limit=5)
                items = s_res.get("data", {}).get("items", []) if isinstance(s_res.get("data"), dict) else []
                if items:
                    target_student_id = items[0].get("id")
                    student_info = items[0]

        if not target_student_id:
            return {"error": f"Không tìm thấy sinh viên tương ứng với '{student_search}'."}

        if not cid or not crsid:
            return {"error": "Cần cung cấp thêm thông tin lớp học (class_name hoặc class_id) hoặc môn học (course_name hoặc course_id) để tra cứu chỉ số đào tạo."}

        # Gọi API auto-rpoint
        url = f"/api/auto-rpoint/{target_student_id}/{crsid}"
        metric_res = self._get(url, {"classId": cid})
        data = metric_res.get("data", {}) if isinstance(metric_res.get("data"), dict) else {}

        if not data:
            return {
                "statusCode": 404,
                "message": f"Chưa có dữ liệu chỉ số đào tạo cho sinh viên '{student_search or target_student_id}' tại lớp môn học này.",
                "raw": metric_res
            }

        return {
            "statusCode": 200,
            "student": {
                "id": target_student_id,
                "fullName": student_info.get("fullName") or data.get("fullName"),
                "studentCode": student_info.get("studentCode") or data.get("studentCode"),
                "email": student_info.get("email") or data.get("email"),
            },
            "class": {
                "id": cid,
                "name": cname
            },
            "course": {
                "id": crsid,
                "name": crsname
            },
            "metrics": {
                "rpoint": {
                    "totalScore": data.get("totalScore"),
                    "baseScore": data.get("baseScore"),
                    "bonusTotal": data.get("bonusTotal", 0),
                    "minRequired": data.get("formulaSnapshot", {}).get("eligibility", {}).get("rpointMin", 80)
                },
                "attendance": {
                    "score": data.get("attendanceScore"),
                    "maxScore": data.get("formulaSnapshot", {}).get("attendance", {}).get("max", 20),
                    "absenceRate": data.get("absenceRate", 0),
                    "maxAbsenceRateAllowed": 100 - data.get("formulaSnapshot", {}).get("eligibility", {}).get("attendanceRateMin", 80)
                },
                "preparation": {
                    "score": data.get("preparationScore"),
                    "maxScore": data.get("formulaSnapshot", {}).get("preparation", {}).get("max", 20)
                },
                "homework": {
                    "score": data.get("assignmentScore") or data.get("homeworkScore"),
                    "maxScore": data.get("formulaSnapshot", {}).get("assignment", {}).get("max", 20),
                    "submissionRate": data.get("submissionRate", 0),
                    "missingRate": data.get("homeworkMissingRate", 0)
                },
                "compliance": {
                    "score": data.get("complianceScore"),
                    "maxScore": data.get("formulaSnapshot", {}).get("compliance", {}).get("max", 40),
                    "violationCount": data.get("violationCount", 0)
                },
                "examEligibility": {
                    "eligible": data.get("examEligible", False),
                    "detail": data.get("eligibilityDetail", {})
                }
            },
            "raw": data
        }

    def get_class_training_metrics(
        self,
        class_id: str = None,
        class_name: str = None,
        course_id: str = None,
        course_name: str = None,
        limit: int = 20
    ) -> dict:
        """Tổng hợp và thống kê toàn bộ chỉ số đào tạo của lớp theo môn học."""
        cid, cname, cobj, crsid, crsname = self._resolve_course_and_class(class_id, class_name, course_id, course_name)
        if not cid or not crsid:
            return {"error": "Không xác định được classId hoặc courseId để tổng hợp chỉ số đào tạo.", "classId": cid, "courseId": crsid}

        roster_res = self.get_course_class_roster(class_id=cid, course_id=crsid)
        roster_items = roster_res.get("data", {}).get("items", [])
        if not roster_items:
            return {"statusCode": 200, "message": "Lớp học chưa có sinh viên ghi danh trong môn học này.", "data": {"total": 0, "items": []}}

        from concurrent.futures import ThreadPoolExecutor

        def _fetch_one(item):
            st = item.get("student", {})
            sid = st.get("id")
            if not sid:
                return None
            url = f"/api/auto-rpoint/{sid}/{crsid}"
            try:
                res = self._get(url, {"classId": cid})
                d = res.get("data", {}) if isinstance(res.get("data"), dict) else {}
                return {
                    "studentId": sid,
                    "studentCode": st.get("studentCode"),
                    "fullName": st.get("fullName"),
                    "email": st.get("email"),
                    "rpoint": d.get("totalScore", 0),
                    "absenceRate": d.get("absenceRate", 0),
                    "preparationScore": d.get("preparationScore", 0),
                    "submissionRate": d.get("submissionRate", 0),
                    "attendanceScore": d.get("attendanceScore", 0),
                    "complianceScore": d.get("complianceScore", 0),
                    "examEligible": d.get("examEligible", False)
                }
            except Exception:
                return {
                    "studentId": sid,
                    "studentCode": st.get("studentCode"),
                    "fullName": st.get("fullName"),
                    "email": st.get("email"),
                    "rpoint": None,
                    "absenceRate": None,
                    "preparationScore": None,
                    "submissionRate": None,
                    "examEligible": None
                }

        with ThreadPoolExecutor(max_workers=8) as ex:
            records = list(ex.map(_fetch_one, roster_items))

        valid_records = [r for r in records if r and r.get("rpoint") is not None]
        total_students = len(valid_records)
        avg_rpoint = round(sum(r["rpoint"] for r in valid_records) / total_students, 1) if total_students else 0
        avg_absence = round(sum(r["absenceRate"] for r in valid_records) / total_students, 1) if total_students else 0
        avg_prep = round(sum(r["preparationScore"] for r in valid_records) / total_students, 1) if total_students else 0
        avg_submission = round(sum(r["submissionRate"] for r in valid_records) / total_students, 1) if total_students else 0
        eligible_count = sum(1 for r in valid_records if r.get("examEligible") is True)
        ineligible_count = sum(1 for r in valid_records if r.get("examEligible") is False)

        display_records = valid_records[:limit] if (limit and limit > 0) else valid_records

        return {
            "statusCode": 200,
            "data": {
                "classId": cid,
                "className": cname,
                "courseId": crsid,
                "courseName": crsname,
                "summary": {
                    "totalStudents": total_students,
                    "avgRpoint": avg_rpoint,
                    "avgAbsenceRate": f"{avg_absence}%",
                    "avgPreparationScore": f"{avg_prep}/20",
                    "avgSubmissionRate": f"{avg_submission}%",
                    "examEligibleCount": eligible_count,
                    "ineligibleCount": ineligible_count
                },
                "total": total_students,
                "items": display_records
            }
        }

    # --- DISPATCHER: Agent gọi qua đây ---

    def execute(self, function_name: str, arguments: dict) -> Any:
        """
        Điểm vào duy nhất để AI Agent gọi.
        Nhận tên hàm và tham số, trả về kết quả JSON.
        """
        dispatch = {
            "get_my_profile":                self.get_my_profile,
            "list_training_systems":         self.list_training_systems,
            "get_training_system_detail":    self.get_training_system_detail,
            "list_classes":                  self.list_classes,
            "get_class_detail":              self.get_class_detail,
            "list_courses":                  self.list_courses,
            "get_course_detail":             self.get_course_detail,
            "list_students":                 self.list_students,
            "get_student_detail":            self.get_student_detail,
            "list_sent_notifications":       self.list_sent_notifications,
            "list_received_notifications":   self.list_received_notifications,
            "send_notification":             self.send_notification,
            "list_attendance_sessions":      self.list_attendance_sessions,
            "get_session_roster":            self.get_session_roster,
            "get_student_attendance":        self.get_student_attendance,
            "get_class_attendance_summary":  self.get_class_attendance_summary,
            "get_homework_session_detail":   self.get_homework_session_detail,
            "list_homework_submissions":     self.list_homework_submissions,
            "get_student_homework_status":   self.get_student_homework_status,
            "create_homework":               self.create_homework,
            "update_homework":               self.update_homework,
            "delete_homework":               self.delete_homework,
            "update_submission_feedback":    self.update_submission_feedback,
            "get_student_training_metrics":  self.get_student_training_metrics,
            "get_class_training_metrics":    self.get_class_training_metrics,
            "get_course_class_roster":       self.get_course_class_roster,
        }

        fn = dispatch.get(function_name)
        if not fn:
            return {"error": f"Hàm '{function_name}' không tồn tại trong toolkit."}

        try:
            result = fn(**arguments)
            return result
        except Exception as e:
            return {"error": str(e), "function": function_name, "arguments": arguments}


# ===========================================================================
# III. DEMO — Mô phỏng vòng lặp Agent
# ===========================================================================

if __name__ == "__main__":
    import json

    executor = LMSFunctionExecutor()

    print("=" * 60)
    print("DEMO: Mô phỏng AI Agent gọi Function Calling")
    print("=" * 60)

    # Demo 1: Agent lấy profile người dùng
    print("\n[AGENT] → Gọi: get_my_profile()")
    result = executor.execute("get_my_profile", {})
    data = result.get("data", {})
    print(f"[RESULT] Xin chào, {data.get('fullName')}!")
    print(f"         Email: {data.get('email')}")
    print(f"         Roles: {[r['name'] for r in data.get('roles', [])]}")

    # Demo 2: Agent lấy danh sách lớp
    print("\n[AGENT] → Gọi: list_classes(limit=5)")
    result2 = executor.execute("list_classes", {"limit": 5})
    items = result2.get("data", {}).get("items", [])
    print(f"[RESULT] Tìm thấy {len(items)} lớp học:")
    for cls in items:
        print(f"  • {cls['classCode']} (ID: {cls['id']})")

    # Demo 3: Agent lấy sinh viên theo hệ thống CNTT
    print("\n[AGENT] → Gọi: list_students(system_id='6a868c22c6d890523883e324', limit=3)")
    result3 = executor.execute("list_students", {
        "system_id": "6a868c22c6d890523883e324",
        "limit": 3
    })
    students = result3.get("data", {}).get("items", [])
    print(f"[RESULT] Sinh viên K26-CNTT (3 đầu):")
    for s in students:
        print(f"  • {s['studentCode']} - {s['fullName']} ({s.get('location', 'N/A')})")

    # Demo 4: Xuất TOOLS_SCHEMA để dùng với OpenAI/Anthropic
    print("\n[SCHEMA] Xuất tools schema ra file để dùng với LLM API...")
    with open("lms_tools_schema.json", "w", encoding="utf-8") as f:
        json.dump(TOOLS_SCHEMA, f, ensure_ascii=False, indent=2)
    print(f"[OK] Đã lưu schema vào: lms_tools_schema.json")
    print(f"     Tổng số tools: {len(TOOLS_SCHEMA)}")
