"""
=============================================================================
 RIKA AGENT — FastAPI Backend với Streaming SSE
=============================================================================
Giải pháp tăng tốc:
1. Stream token từng chữ từ Gemini về ngay lập tức (như ChatGPT)
2. Tool calls xử lý bình thường → rồi stream kết quả cuối
3. Async hoàn toàn — không block event loop
=============================================================================
"""

import sys
import os

# Fix charmap UnicodeEncodeError on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"

import json
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from agent import RikkaAgent, safe_print
import lms_tools

app = FastAPI(title="Rika LMS Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# SESSION MANAGEMENT
# ---------------------------------------------------------------------------

sessions: dict[str, RikkaAgent] = {}
_session_lock = threading.Lock()
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="rika-worker")


def _create_or_get_agent(session_id: str) -> RikkaAgent:
    """Chạy trong thread executor — an toàn với sync_playwright."""
    with _session_lock:
        if session_id not in sessions:
            sessions[session_id] = RikkaAgent()
        return sessions[session_id]


async def get_agent(session_id: str) -> RikkaAgent:
    """Async wrapper — chạy _create_or_get_agent trong thread riêng."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _create_or_get_agent, session_id)


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


# ---------------------------------------------------------------------------
# STREAMING ENDPOINT (Server-Sent Events)
# ---------------------------------------------------------------------------

@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    """
    Streaming endpoint — gửi từng chunk về frontend ngay khi có.
    Format SSE: data: {json}\n\n
    """

    async def event_generator():
        # --- Khởi tạo agent (lazy, có thể cần đăng nhập lại) ---
        try:
            agent = await get_agent(req.session_id)
        except Exception as auth_err:
            print(f"❌ Lỗi khởi tạo / auth agent: {auth_err}")
            reply = "⚠️ Hệ thống hiện tại đang gặp sự cố hoặc đang trong quá trình bảo trì. Vui lòng thử lại sau ít phút!"
            for i in range(0, len(reply), 4):
                yield f"data: {json.dumps({'type': 'chunk', 'data': reply[i:i+4]})}\n\n"
                await asyncio.sleep(0.005)
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return

        tool_calls_log = []
        progress_queue = asyncio.Queue()

        # Patch executor để ghi lại tool calls và progress
        original_execute = agent.executor.execute
        def tracked_execute(fn_name, args):
            tool_calls_log.append({"name": fn_name, "args": args})
            return original_execute(fn_name, args)
        agent.executor.execute = tracked_execute

        loop = asyncio.get_event_loop()
        def on_progress(msg: str):
            loop.call_soon_threadsafe(progress_queue.put_nowait, {"type": "status", "data": msg})
        agent.executor.progress_callback = on_progress

        try:
            # Bước 1: Gửi event "thinking" ngay lập tức
            yield f"data: {json.dumps({'type': 'thinking'})}\n\n"

            # Bước 2: Chạy agent trong thread riêng và đồng thời stream progress
            agent_future = loop.run_in_executor(
                _executor, _run_agent_with_stream_final, agent, req.message, tool_calls_log
            )

            while not agent_future.done():
                try:
                    event = await asyncio.wait_for(progress_queue.get(), timeout=0.1)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    pass

            while not progress_queue.empty():
                event = progress_queue.get_nowait()
                yield f"data: {json.dumps(event)}\n\n"

            reply, tool_calls = await agent_future

            # Bước 3: Gửi tool calls
            if tool_calls:
                yield f"data: {json.dumps({'type': 'tool_calls', 'data': tool_calls})}\n\n"

            # Bước 4: Stream text từng chunk
            chunk_size = 4
            for i in range(0, len(reply), chunk_size):
                chunk = reply[i:i+chunk_size]
                yield f"data: {json.dumps({'type': 'chunk', 'data': chunk})}\n\n"
                await asyncio.sleep(0.008)

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            print(f"❌ Streaming server error: {e}")
            fallback_msg = "⚠️ Hệ thống hiện tại đang gặp sự cố hoặc đang trong quá trình bảo trì. Vui lòng thử lại sau ít phút!"
            for i in range(0, len(fallback_msg), 4):
                yield f"data: {json.dumps({'type': 'chunk', 'data': fallback_msg[i:i+4]})}\n\n"
                await asyncio.sleep(0.005)
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        finally:
            agent.executor.execute = original_execute

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


def _sanitize_and_patch_plagiarism_table(reply: str, message: str, agent: RikkaAgent, tool_calls: list) -> str:
    """
    Đảm bảo 100% bảng Markdown nghi vấn sao chép luôn được hiển thị đầy đủ,
    không bị LLM bỏ sót dòng, không bị cụt do token limit, và không bị lỗi parser.
    """
    try:
        import re
        from datetime import datetime

        # 1. Kiểm tra cache dữ liệu plagiarism (RAM + Disk file)
        cache = getattr(agent.executor, "_plagiarism_cache", {}) or getattr(lms_tools, "GLOBAL_PLAGIARISM_CACHE", {})
        has_plag_call = any(tc.get("name") == "check_session_homework_plagiarism" for tc in tool_calls)
        msg_low = (message or "").lower()
        is_plag_intent = any(w in msg_low for w in ["sao chép", "nghi vấn", "gian lận", "toàn bộ", "xem tiếp", "còn lại", "16", "17", "bài tập", "plagiarism", "buổi", "session"])

        c_data = None
        if cache:
            valid_keys = [k for k in cache.keys() if k != "_latest"]
            if valid_keys:
                latest_key = max(valid_keys, key=lambda k: cache[k][0])
                c_time, c_data = cache[latest_key]
            elif "_latest" in cache:
                c_time, c_data = cache["_latest"]

        # Nếu RAM cache không có, tải ngay từ disk cache
        if not c_data and hasattr(lms_tools, "load_plagiarism_disk_cache"):
            c_data = lms_tools.load_plagiarism_disk_cache()

        if not c_data:
            return reply

        if not has_plag_call and not is_plag_intent:
            return reply

        data = c_data.get("data", {})
        if not data:
            return reply

        table_top15 = data.get("formatted_table_top15", "")
        table_remaining = data.get("formatted_table_remaining", "")
        table_all = data.get("formatted_table_all", "")
        rem_count = data.get("remaining_count", 0)
        summary = data.get("summary", {})
        flagged_count = summary.get("flaggedPairsCount", 0)

        # 2. Quyết định hiển thị bảng nào dựa trên ngữ cảnh người dùng
        is_all_req = any(w in msg_low for w in [
            "toàn bộ", "tất cả", "toan bo", "tat ca", "full", "hết cả", "toàn thể", "mọi cặp", "xem het"
        ])
        is_rem_req = any(w in msg_low for w in [
            "còn lại", "con lai", "xem tiếp", "xem tiep", "tiếp theo", "tiep theo",
            "trang sau", "kế tiếp", "các cặp sau", "hiển thị tiếp", "các cặp còn lại"
        ]) or bool(re.search(r'cặp\s*(?:thứ\s*|từ\s*)?16', msg_low))

        if is_all_req or rem_count == 0:
            target_table = table_all
            show_paging_hint = False
        elif is_rem_req and table_remaining:
            target_table = table_remaining
            show_paging_hint = False
        else:
            target_table = table_top15
            show_paging_hint = (rem_count > 0)

        if not target_table:
            return reply

        # 3. Chuẩn bị khối bảng hoàn chỉnh (kèm gợi ý phân trang nếu có)
        replacement_block = target_table
        if show_paging_hint and rem_count > 0:
            replacement_block += (
                f"\n\n*(Còn {rem_count} cặp nghi vấn tiếp theo từ 16 đến {flagged_count}. "
                f"Bạn có thể yêu cầu xem tiếp danh sách các cặp còn lại bất cứ lúc nào).*\n\n"
                f"[choice: Xem tiếp các cặp còn lại | Xem tiếp các cặp nghi vấn sao chép còn lại]"
            )

        # Xóa các dòng gợi ý phân trang mồ côi nếu AI đã xuất hiện trước đó (tránh trùng lặp 2 lần)
        reply = re.sub(r'\n*\s*\(Còn\s+\d+\s+cặp[^\n]*\)?', '', reply, flags=re.IGNORECASE)

        # 4. Thay thế nếu có placeholder
        placeholder_m = re.search(r':::(?:PLAGIARISM_TABLE_TOP15|PLAGIARISM_TABLE_REMAINING|PLAGIARISM_TABLE_ALL|PLAGIARISM_TABLE):::', reply)
        if placeholder_m:
            reply = reply[:placeholder_m.start()] + replacement_block + reply[placeholder_m.end():]
            safe_print(f"  ⚡ [Auto-Patch] Replaced placeholder with verified table")
            return reply

        # 5. Tìm kiếm bảng markdown nghi vấn trong reply của AI (chỉ khớp các dòng bắt đầu bằng |)
        table_pattern = re.compile(
            r'(\|\s*STT\s*\|\s*Bài tập[^\n]*\n(?:[ \t]*\|[^\n]*\n*)*)',
            re.IGNORECASE
        )
        matches = list(table_pattern.finditer(reply))
        target_row_count = len(re.findall(r'\|\s*\d+\s*\|', target_table))

        if matches:
            match = matches[0]
            existing_table_str = match.group(1)
            existing_row_count = len(re.findall(r'\|\s*\d+\s*\|', existing_table_str))

            # Nếu bảng của AI có số dòng ít hơn bảng chuẩn HOẶC bị cụt ở cuối -> Thay thế hoàn toàn!
            if existing_row_count < target_row_count or not existing_table_str.rstrip().endswith("|"):
                reply = reply[:match.start(1)] + replacement_block + reply[match.end(1):]
                safe_print(f"  ⚡ [Auto-Patch] Replaced defective table ({existing_row_count} rows) with verified table ({target_row_count} rows)")
        else:
            # AI hoàn toàn quên render bảng -> Tự động chèn vào sau tiêu đề danh sách
            header_m = re.search(r'((?:Danh sách|Bảng|Chi tiết)[^\n]*nghi vấn[^\n]*\n+)', reply, re.IGNORECASE)
            if header_m:
                insert_pos = header_m.end(1)
                reply = reply[:insert_pos] + "\n" + replacement_block + "\n\n" + reply[insert_pos:]
                safe_print(f"  ⚡ [Auto-Patch] Inserted verified table ({target_row_count} rows) after list header")
            else:
                reply = reply + "\n\n### Danh sách các cặp bài làm có dấu hiệu nghi vấn sao chép\n\n" + replacement_block + "\n"
                safe_print(f"  ⚡ [Auto-Patch] Appended verified table ({target_row_count} rows) to end of reply")

        return reply
    except Exception as e:
        safe_print(f"  ⚠️ Error in _sanitize_and_patch_plagiarism_table: {e}")
        return reply


def _run_agent_with_stream_final(agent: RikkaAgent, message: str, tool_calls_log: list):
    """Chạy agent, trả về (reply_text, tool_calls_snapshot)."""
    reply = agent.chat(message)
    tool_calls = list(tool_calls_log)
    # Tự động vá/bảo đảm bảng Markdown nghi vấn sao chép luôn đầy đủ 100%
    reply = _sanitize_and_patch_plagiarism_table(reply, message, agent, tool_calls)
    return reply, tool_calls


# ---------------------------------------------------------------------------
# NON-STREAMING FALLBACK
# ---------------------------------------------------------------------------

@app.post("/api/chat")
async def chat(req: ChatRequest):
    try:
        agent = await get_agent(req.session_id)
        tool_calls_log = []

        original_execute = agent.executor.execute
        def tracked_execute(fn_name, args):
            tool_calls_log.append({"name": fn_name, "args": args})
            return original_execute(fn_name, args)
        agent.executor.execute = tracked_execute

        loop = asyncio.get_event_loop()
        reply = await loop.run_in_executor(_executor, agent.chat, req.message)
        reply = _sanitize_and_patch_plagiarism_table(reply, req.message, agent, tool_calls_log)
        agent.executor.execute = original_execute

        return {"reply": reply, "tool_calls": tool_calls_log}
    except Exception as e:
        print(f"❌ /api/chat error: {e}")
        return {
            "reply": "⚠️ Hệ thống hiện tại đang gặp sự cố hoặc đang trong quá trình bảo trì. Vui lòng thử lại sau ít phút!",
            "tool_calls": []
        }


@app.post("/api/reset")
async def reset_session(req: dict):
    session_id = req.get("session_id", "default")
    if session_id in sessions:
        with _session_lock:
            sessions.pop(session_id, None)
    return {"ok": True}


@app.get("/api/health")
async def health():
    import tools_manager
    tools = tools_manager.load_tools()
    active = [t for t in tools if t.get("enabled", True)]
    return {"status": "ok", "model": "gemini-3.8-flash", "tools": len(active), "total_tools": len(tools)}


class TokenUpdateRequest(BaseModel):
    token: str


@app.get("/api/token/status")
async def get_token_status():
    import time
    from auth_manager import _decode_jwt_exp
    import config
    token = None
    if os.path.exists(config.TOKEN_CACHE_FILE):
        try:
            with open(config.TOKEN_CACHE_FILE, 'r') as f:
                token = json.load(f).get('token')
        except Exception:
            pass
    if not token:
        token = os.getenv("LMS_TOKEN") or os.getenv("RIKKEI_TOKEN")

    if not token:
        return {"status": "missing", "valid": False, "message": "Chưa có token nào"}

    exp = _decode_jwt_exp(token)
    now = int(time.time())
    remaining_seconds = exp - now if exp > 0 else 0
    valid = remaining_seconds > 0

    return {
        "status": "valid" if valid else "expired",
        "valid": valid,
        "exp": exp,
        "remaining_minutes": round(remaining_seconds / 60, 1),
        "token_preview": token[:15] + "..." + token[-10:] if len(token) > 25 else token
    }


@app.post("/api/token")
async def update_token(req: TokenUpdateRequest):
    import time
    from auth_manager import save_token, _decode_jwt_exp
    raw_token = req.token.strip().replace("Bearer ", "")
    exp = _decode_jwt_exp(raw_token)
    now = int(time.time())
    
    save_token(raw_token)
    os.environ["LMS_TOKEN"] = raw_token
    
    with _session_lock:
        for s in sessions.values():
            if hasattr(s, "executor") and hasattr(s.executor, "_tools"):
                tools = s.executor._tools
                if hasattr(tools, "_api"):
                    tools._api.token = raw_token
                    
    return {
        "ok": True,
        "message": "Token đã được cập nhật thành công!",
        "remaining_minutes": round((exp - now) / 60, 1) if exp > 0 else "unknown"
    }


# ---------------------------------------------------------------------------
# TOOLSET MANAGEMENT APIS (Cài đặt bộ Tools: Xem, Thêm, Sửa, Xoá)
# ---------------------------------------------------------------------------
import tools_manager

def _broadcast_tools_reload():
    with _session_lock:
        for ag in sessions.values():
            try:
                ag.reload_tools()
            except Exception as err:
                print(f"Error reloading tools for agent session: {err}")

@app.get("/api/tools")
async def get_tools_list():
    """Xem danh sách toàn bộ các tools trong hệ thống."""
    tools = tools_manager.load_tools()
    categories = sorted(list(set(t.get("category", "Khác") for t in tools)))
    active_count = sum(1 for t in tools if t.get("enabled", True))
    return {
        "ok": True,
        "total": len(tools),
        "active": active_count,
        "categories": categories,
        "tools": tools
    }

@app.post("/api/tools")
async def create_tool(payload: dict):
    """Thêm một tool mới vào bộ công cụ."""
    try:
        new_tool = tools_manager.add_tool(payload)
        _broadcast_tools_reload()
        return {"ok": True, "message": f"Đã thêm tool '{new_tool['name']}' thành công.", "tool": new_tool}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.put("/api/tools/{name}")
async def update_tool_endpoint(name: str, payload: dict):
    """Chỉnh sửa thông tin, tham số hoặc trạng thái kích hoạt của tool."""
    try:
        updated = tools_manager.update_tool(name, payload)
        _broadcast_tools_reload()
        return {"ok": True, "message": f"Đã cập nhật tool '{name}' thành công.", "tool": updated}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.patch("/api/tools/{name}/toggle")
async def toggle_tool_endpoint(name: str, payload: dict):
    """Bật hoặc tắt nhanh trạng thái kích hoạt của tool."""
    try:
        enabled = payload.get("enabled", True)
        updated = tools_manager.toggle_tool(name, enabled)
        _broadcast_tools_reload()
        state_str = "kích hoạt" if enabled else "tắt"
        return {"ok": True, "message": f"Đã {state_str} tool '{name}'.", "tool": updated}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.delete("/api/tools/{name}")
async def delete_tool_endpoint(name: str):
    """Xóa tool khỏi hệ thống."""
    try:
        tools_manager.delete_tool(name)
        _broadcast_tools_reload()
        return {"ok": True, "message": f"Đã xóa tool '{name}' thành công."}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.post("/api/tools/reset")
async def reset_tools_endpoint():
    """Khôi phục bộ tools về mặc định ban đầu."""
    try:
        default_tools = tools_manager.reset_to_default()
        _broadcast_tools_reload()
        return {"ok": True, "message": "Đã khôi phục bộ tools về mặc định ban đầu.", "total": len(default_tools)}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/api/tools/schema")
async def get_tools_schema_endpoint():
    """Trả về chuẩn OpenAI / Anthropic Function Calling Schema của các tools đang kích hoạt."""
    return tools_manager.get_active_schema()

@app.post("/api/tools/execute")
async def execute_tool_endpoint(payload: dict):
    """
    Thực thi trực tiếp một tool từ xa (Remote Tool Execution).
    Dành cho external AI Agents (LangChain, LlamaIndex, AutoGen, CrewAI, Custom Bot...) kết nối vào.
    Body: {"name": "list_classes", "arguments": {"limit": 5}}
    """
    fn_name = payload.get("name")
    args = payload.get("arguments", {})
    if not fn_name:
        return {"ok": False, "error": "Thiếu tham số 'name' của tool cần thực thi."}
    try:
        from lms_tools import LMSFunctionExecutor
        executor = LMSFunctionExecutor()
        result = executor.execute(fn_name, args)
        return {"ok": True, "tool": fn_name, "result": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# SERVE FRONTEND
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(html_path, encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
