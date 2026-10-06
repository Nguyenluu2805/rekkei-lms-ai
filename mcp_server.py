"""
=============================================================================
 RIKKEI LMS — MODEL CONTEXT PROTOCOL (MCP) SERVER
=============================================================================
Chuẩn: Model Context Protocol (Anthropic / Cursor / Windsurf / Claude Desktop)
Phiên bản: MCP 2.x
Chạy độc lập:
  • Chế độ stdio (Mặc định cho Cursor, Claude Desktop):
      python mcp_server.py
  • Chế độ SSE (HTTP Server cho web clients):
      python mcp_server.py --transport sse --port 8001
=============================================================================
"""

import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"

import argparse
from mcp.server.mcpserver import MCPServer
from lms_tools import LMSFunctionExecutor
import tools_manager

def create_mcp_server() -> MCPServer:
    """Tạo và khởi tạo MCP Server với toàn bộ công cụ LMS Rikkei."""
    server = MCPServer(
        name="rikkei-lms",
        title="Rikkei LMS Toolkit MCP Server",
        description="Bộ công cụ quản lý đào tạo, chuyên cần, điểm danh và bài tập về nhà trên LMS Rikkei Admin."
    )
    executor = LMSFunctionExecutor()
    tools = tools_manager.load_tools()

    registered_count = 0
    for t in tools:
        if not t.get("enabled", True):
            continue
        name = t["name"]
        desc = t.get("description", "")
        fn = getattr(executor, name, None)
        if fn and callable(fn):
            server.add_tool(fn, name=name, description=desc)
            registered_count += 1

    return server


def main():
    parser = argparse.ArgumentParser(description="Rikkei LMS MCP Server")
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio", help="Giao thức truyền thông (mặc định: stdio)")
    parser.add_argument("--port", type=int, default=8001, help="Cổng chạy SSE (nếu dùng --transport sse)")
    args = parser.parse_args()

    server = create_mcp_server()

    if args.transport == "stdio":
        # Chế độ stdio dùng cho Cursor IDE, Claude Desktop, Windsurf
        server.run(transport="stdio")
    elif args.transport == "sse":
        # Chế độ SSE Server qua HTTP
        print(f"🚀 Rikkei LMS MCP Server đang chạy chế độ SSE trên cổng {args.port}...")
        server.run(transport="sse", port=args.port)


if __name__ == "__main__":
    main()
