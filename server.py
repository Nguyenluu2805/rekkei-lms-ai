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
from agent import RikkaAgent

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

        # Patch executor để ghi lại tool calls
        original_execute = agent.executor.execute
        def tracked_execute(fn_name, args):
            tool_calls_log.append({"name": fn_name, "args": args})
            return original_execute(fn_name, args)
        agent.executor.execute = tracked_execute

        try:
            loop = asyncio.get_event_loop()

            # Bước 1: Gửi event "thinking" ngay lập tức
            yield f"data: {json.dumps({'type': 'thinking'})}\n\n"

            # Bước 2: Chạy agent trong thread riêng
            reply, tool_calls = await loop.run_in_executor(
                _executor, _run_agent_with_stream_final, agent, req.message, tool_calls_log
            )

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


def _run_agent_with_stream_final(agent: RikkaAgent, message: str, tool_calls_log: list):
    """Chạy agent, trả về (reply_text, tool_calls_snapshot)."""
    reply = agent.chat(message)
    tool_calls = list(tool_calls_log)
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
