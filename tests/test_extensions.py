# ============================================================
# tests/test_extensions.py — 新模块的单元测试（离线可跑，零 API 消耗）
# ------------------------------------------------------------
# 测的都是纯函数：切片/向量/检索/权限闸门/MCP 协议分发。
# 涉网的部分（LLM 调用、子进程握手）留给 step24/25/26 手动实测。
# ============================================================
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from step24_rag import chunk_text, embed_local, cosine, search, CHUNK_SIZE
from step26_api import command_allowed, execute_tool
from mini_mcp_server import handle_request, TOOLS


# ---------- RAG：切片 ----------
def test_chunk_respects_size_and_overlap():
    text = "A" * 700
    chunks = chunk_text(text)
    assert len(chunks) >= 2
    assert all(len(c) <= CHUNK_SIZE for c in chunks)
    assert all(c for c in chunks)                       # 没有空切片


def test_chunk_short_text_single_piece():
    assert chunk_text("短文本") == ["短文本"]
    assert chunk_text("") == []


# ---------- RAG：向量与检索 ----------
def test_embed_local_deterministic_and_normalized():
    v1 = embed_local("Agent Loop 工具调用")
    v2 = embed_local("Agent Loop 工具调用")
    assert v1 == v2                                     # 稳定哈希：跨次运行结果一致
    assert len(v1) == 256
    norm = sum(x * x for x in v1) ** 0.5
    assert abs(norm - 1.0) < 1e-6                       # L2 归一化


def test_search_ranks_most_similar_first():
    index = [
        {"source": "a.md", "text": "Agent Loop 是 while 循环", "vec": embed_local("Agent Loop 是 while 循环")},
        {"source": "b.md", "text": "今天天气很好", "vec": embed_local("今天天气很好")},
    ]
    hits = search(index, embed_local("什么是 Agent Loop？"))
    assert hits[0][1]["source"] == "a.md"               # 相关的排第一
    assert hits[0][0] > hits[1][0]                      # 分数单调


def test_cosine_identical_is_one():
    v = embed_local("MCP 协议")
    assert abs(cosine(v, v) - 1.0) < 1e-6


# ---------- 权限闸门（step23 升级版）----------
def test_whitelist_allows_safe_commands():
    assert command_allowed("dir")
    assert command_allowed("echo hello")
    assert command_allowed("python --version")


def test_whitelist_blocks_dangerous_commands():
    assert not command_allowed("del diary.txt")         # 不在白名单
    assert not command_allowed("")                      # 空


def test_whitelist_blocks_chained_injection():
    # step23 已知漏洞的回归测试：白名单只看第一个词时这行会穿透
    assert not command_allowed("echo hello && del diary.txt")
    assert not command_allowed("dir | del diary.txt")
    assert not command_allowed("echo $(rm -rf /)")


# ---------- 工具执行：未知工具优雅拒绝 ----------
def test_execute_tool_unknown_graceful():
    assert "未知工具" in execute_tool("no_such_tool", {})


# ---------- MCP 协议分发（纯函数，不起子进程）----------
def test_mcp_initialize_handshake():
    resp = handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    assert resp["serverInfo"]["name"] == "mini-mcp-server"
    assert "protocolVersion" in resp


def test_mcp_tools_list_has_schemas():
    resp = handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    names = [t["name"] for t in resp["tools"]]
    assert "word_count" in names
    for t in resp["tools"]:
        assert "inputSchema" in t                       # 菜单三件套齐全


def test_mcp_tools_call_word_count():
    resp = handle_request({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                           "params": {"name": "word_count",
                                      "arguments": {"text": "hello world foo"}}})
    assert "words=3" in resp["content"][0]["text"]
    assert resp["isError"] is False


def test_mcp_tools_call_unknown_tool_is_error_not_crash():
    resp = handle_request({"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                           "params": {"name": "no_such", "arguments": {}}})
    assert resp["isError"] is True                      # 优雅拒绝，不崩


def test_mcp_unknown_method_raises_mapped_to_error():
    with pytest.raises(KeyError):
        handle_request({"jsonrpc": "2.0", "id": 5, "method": "no/such/method"})


def test_tools_menu_count():
    assert len(TOOLS) == 2
