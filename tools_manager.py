"""
=============================================================================
 RIKKEI LMS — TOOLS MANAGER (Quản lý Bộ Tools của Rika AI Agent)
=============================================================================
Chức năng:
1. Xem danh sách các tools (Built-in & Custom)
2. Thêm mới tool (với JSON Schema parameters)
3. Chỉnh sửa mô tả, tham số, bật/tắt kích hoạt tool
4. Xóa tool hoặc khôi phục về mặc định ban đầu
5. Lưu trữ cấu hình persistent tại data/tools_config.json
=============================================================================
"""

import os
import json
import time
from lms_tools import TOOLS_SCHEMA

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "data", "tools_config.json")

# Phân loại mặc định cho 19 tools hệ thống
DEFAULT_CATEGORIES = {
    "get_my_profile": "Hồ sơ cá nhân",
    "list_training_systems": "Hệ thống đào tạo",
    "get_training_system_detail": "Hệ thống đào tạo",
    "list_classes": "Lớp học",
    "get_class_detail": "Lớp học",
    "list_courses": "Khoá học & Môn học",
    "get_course_detail": "Khoá học & Môn học",
    "list_students": "Quản lý Sinh viên",
    "get_student_detail": "Quản lý Sinh viên",
    "list_sent_notifications": "Thông báo",
    "list_received_notifications": "Thông báo",
    "send_notification": "Thông báo",
    "list_attendance_sessions": "Điểm danh & Chuyên cần",
    "get_session_roster": "Điểm danh & Chuyên cần",
    "get_student_attendance": "Điểm danh & Chuyên cần",
    "get_class_attendance_summary": "Điểm danh & Chuyên cần",
    "get_homework_session_detail": "Bài tập về nhà",
    "list_homework_submissions": "Bài tập về nhà",
    "get_student_homework_status": "Bài tập về nhà",
    "create_homework": "Bài tập về nhà",
    "update_homework": "Bài tập về nhà",
    "delete_homework": "Bài tập về nhà",
    "update_submission_feedback": "Bài tập về nhà",
    "get_student_training_metrics": "Chỉ số đào tạo & rPoint",
    "get_class_training_metrics": "Chỉ số đào tạo & rPoint",
    "get_course_class_roster": "Chỉ số đào tạo & rPoint",
}


def _build_default_config() -> list[dict]:
    """Tạo danh sách cấu hình mặc định từ TOOLS_SCHEMA hiện tại."""
    now = int(time.time() * 1000)
    tools = []
    for item in TOOLS_SCHEMA:
        fn = item.get("function", {})
        name = fn.get("name", "")
        tools.append({
            "name": name,
            "description": fn.get("description", ""),
            "category": DEFAULT_CATEGORIES.get(name, "Khác"),
            "enabled": True,
            "is_builtin": True,
            "parameters": fn.get("parameters", {"type": "object", "properties": {}, "required": []}),
            "createdAt": now,
            "updatedAt": now
        })
    return tools


def load_tools() -> list[dict]:
    """Đọc cấu hình tools từ data/tools_config.json hoặc khởi tạo mặc định."""
    default_tools = _build_default_config()
    if not os.path.exists(CONFIG_PATH):
        save_tools(default_tools)
        return default_tools

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list) and len(data) > 0:
                # Tự động đồng bộ các built-in tools mới nếu chưa có trong file cấu hình
                existing_names = {t.get("name") for t in data}
                has_new = False
                for dt in default_tools:
                    if dt["name"] not in existing_names:
                        data.append(dt)
                        has_new = True
                if has_new:
                    save_tools(data)
                return data
    except Exception as e:
        print(f"⚠️ Lỗi đọc data/tools_config.json: {e}. Sử dụng cấu hình mặc định.")

    save_tools(default_tools)
    return default_tools


def save_tools(tools: list[dict]):
    """Ghi danh sách tools vào data/tools_config.json."""
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(tools, f, ensure_ascii=False, indent=2)


def get_active_schema() -> list[dict]:
    """Trả về danh sách schema của các tools đang kích hoạt (enabled=True)."""
    tools = load_tools()
    active_schema = []
    for t in tools:
        if t.get("enabled", True):
            active_schema.append({
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("parameters", {"type": "object", "properties": {}, "required": []})
                }
            })
    return active_schema


def add_tool(tool_data: dict) -> dict:
    """Thêm một tool mới vào bộ công cụ."""
    name = (tool_data.get("name") or "").strip()
    if not name:
        raise ValueError("Tên tool không được để trống.")

    # Kiểm tra tên hợp lệ (chỉ chữ thường, số và gạch dưới)
    import re
    if not re.match(r"^[a-zA-Z0-9_-]+$", name):
        raise ValueError("Tên tool chỉ được chứa chữ cái, chữ số, gạch dưới (_) hoặc gạch nối (-).")

    tools = load_tools()
    if any(t["name"] == name for t in tools):
        raise ValueError(f"Tool có tên '{name}' đã tồn tại.")

    now = int(time.time() * 1000)
    params = tool_data.get("parameters") or {"type": "object", "properties": {}, "required": []}
    if isinstance(params, str):
        try:
            params = json.loads(params)
        except Exception:
            raise ValueError("Định dạng Parameters JSON schema không hợp lệ.")

    new_tool = {
        "name": name,
        "description": (tool_data.get("description") or "").strip(),
        "category": (tool_data.get("category") or "Custom").strip(),
        "enabled": tool_data.get("enabled", True),
        "is_builtin": False,
        "parameters": params,
        "createdAt": now,
        "updatedAt": now
    }

    tools.append(new_tool)
    save_tools(tools)
    return new_tool


def update_tool(name: str, tool_data: dict) -> dict:
    """Cập nhật thông tin của một tool."""
    tools = load_tools()
    target = None
    for t in tools:
        if t["name"] == name:
            target = t
            break

    if not target:
        raise ValueError(f"Không tìm thấy tool '{name}'.")

    if "description" in tool_data:
        target["description"] = (tool_data["description"] or "").strip()

    if "category" in tool_data:
        target["category"] = (tool_data["category"] or "").strip()

    if "enabled" in tool_data:
        target["enabled"] = bool(tool_data["enabled"])

    if "parameters" in tool_data:
        params = tool_data["parameters"]
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except Exception:
                raise ValueError("Định dạng Parameters JSON schema không hợp lệ.")
        target["parameters"] = params

    target["updatedAt"] = int(time.time() * 1000)
    save_tools(tools)
    return target


def toggle_tool(name: str, enabled: bool) -> dict:
    """Bật hoặc tắt trạng thái kích hoạt của một tool."""
    return update_tool(name, {"enabled": enabled})


def delete_tool(name: str) -> bool:
    """Xóa tool: nếu là custom thì xóa hẳn; nếu là builtin thì tắt enabled hoặc xóa khỏi danh sách."""
    tools = load_tools()
    new_tools = [t for t in tools if t["name"] != name]

    if len(new_tools) == len(tools):
        raise ValueError(f"Không tìm thấy tool '{name}'.")

    save_tools(new_tools)
    return True


def reset_to_default() -> list[dict]:
    """Khôi phục bộ tools về 19 tools mặc định ban đầu."""
    tools = _build_default_config()
    save_tools(tools)
    return tools
