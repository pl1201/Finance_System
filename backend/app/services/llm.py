"""Trợ lý tổng hợp (LLM) cho trang Live MT5 — docs/plans/plan_tro_ly_tong_hop.md.

Đọc bản tóm gọn của thuật toán ở nến cuối của luồng (``LiveManager.llm_context``), gọi OpenRouter (mặc định DeepSeek
Flash, ``MSL_LLM_MODEL`` để đổi), kiểm mọi con số trong câu trả lời so với dữ liệu đầu vào, ghi nhật ký chỉ ghi thêm
(``llm_log`` + ``llm_data`` trong live.sqlite). Chỉ là lớp đọc: không đổi output của thuật toán, không khuyên giao dịch.
Khoá: ``OPENROUTER_API_KEY`` (biến môi trường) — không lưu, không ghi vào nhật ký.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from typing import Any, Iterator, Optional

import httpx

from backend.app.errors import ServiceError
from backend.app.services.live import live_manager

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "deepseek/deepseek-v4.1-flash-1017"
MAX_HISTORY = 20              # tin nhắn lịch sử giữ lại (10 lượt hỏi — đáp)
MAX_TEXT = 4000               # ký tự mỗi tin nhắn
TIMEOUT_S = 90.0
KEY_HINT_VI = ("Chưa đặt OPENROUTER_API_KEY: tạo khoá ở openrouter.ai/keys, rồi trong PowerShell chạy "
               "setx OPENROUTER_API_KEY \"khoá-của-bạn\", mở cửa sổ PowerShell mới và chạy lại run.ps1.")

RULES_VI = """\
Bạn là trợ lý đọc chart của một lab NGHIÊN CỨU cấu trúc thị trường (không phải hệ thống giao dịch). Bạn nhận dữ liệu JSON
là output của thuật toán ở nến cuối và trả lời bằng tiếng Việt, ngắn gọn, rõ ràng.

Quy tắc bắt buộc:
1. Chỉ dựa trên dữ liệu được đưa. Không bịa mức giá, sự kiện, tin tức hay chỉ báo không có trong dữ liệu. Thiếu thì nói
   «không có trong dữ liệu».
2. Giữ nguyên con số như trong dữ liệu (dấu chấm thập phân, ví dụ 4006.42); có thể làm tròn bớt chữ số nhưng không tự tính
   ra mức giá mới.
3. Xác suất và khoảng giá là của thuật toán: nói kèm điểm thật nếu dữ liệu có. Khoảng giá không nói giá lên hay xuống.
4. KHÔNG khuyên giao dịch: không mua / bán, không điểm vào lệnh, dừng lỗ, chốt lời, khối lượng. Nếu được hỏi, nói rõ đây
   là công cụ nghiên cứu và chỉ mô tả trạng thái, điều kiện làm trạng thái đổi.
5. Thời gian: nêu theo giờ UTC hoặc New York như trong dữ liệu.
6. Định dạng: tiêu đề ngắn bằng «### », gạch đầu dòng «- », in đậm bằng **…**; không bảng, không HTML.
7. Lịch sử trò chuyện có thể nói về nến trước (câu hỏi ghi [nến #…]); số liệu hiện tại luôn lấy từ dữ liệu nến cuối.
"""

#: Số trong câu trả lời: thập phân chấm hoặc phẩy, ngăn nghìn, phần trăm. Ngày, chỉ số nến (#123), «120h» bỏ trước khi so.
NUM = re.compile(r"(?<![\w.,])-?\d(?:[\d.,]*\d)?%?")
SKIP = re.compile(r"\d{4}-\d{2}-\d{2}|#\d+|\b\d+h\b")

_client: Optional[httpx.Client] = None
_client_lock = threading.Lock()


def _key() -> str:
    return os.environ.get("OPENROUTER_API_KEY", "").strip()


def model() -> str:
    return os.environ.get("MSL_LLM_MODEL", "").strip() or DEFAULT_MODEL


def status() -> dict[str, Any]:
    return {"co_khoa": bool(_key()), "mo_hinh": model(), "goi_y_khoa": KEY_HINT_VI}


def _http() -> httpx.Client:
    """Client dùng chung (giữ kết nối TLS tới OpenRouter giữa các lượt), tạo khi cần; ``close()`` lúc backend dừng."""
    global _client
    with _client_lock:
        if _client is None:
            _client = httpx.Client(timeout=TIMEOUT_S)
        return _client


def close() -> None:
    global _client
    with _client_lock:
        if _client is not None:
            _client.close()
            _client = None


def _parse_number(tok: str) -> Optional[tuple[float, int]]:
    """(giá trị, số chữ số thập phân) của 1234.56 / 1,234.56 / 4.006,42 / 3,5 / 12% — có cả chấm và phẩy thì dấu đứng
    sau là dấu thập phân."""
    raw = tok.rstrip("%")
    if "," in raw and "." in raw:
        dec = max(".", ",", key=raw.rfind)
        raw = raw.replace("," if dec == "." else ".", "").replace(",", ".")
    elif "," in raw:
        raw = raw.replace(",", "") if re.fullmatch(r"-?\d{1,3}(,\d{3})+", raw) else raw.replace(",", ".")
    elif raw.count(".") > 1:
        raw = raw.replace(".", "")
    try:
        return float(raw), len(raw.split(".")[1]) if "." in raw else 0
    except ValueError:
        return None


def _numbers(obj: Any) -> Iterator[float]:
    """Mọi con số trong dữ liệu (số và số viết trong chuỗi), duyệt sâu."""
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        yield float(obj)
    elif isinstance(obj, str):
        for m in NUM.finditer(obj):
            parsed = _parse_number(m.group(0))
            if parsed is not None:
                yield parsed[0]
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _numbers(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _numbers(v)


def unknown_numbers(answer: str, *sources: Any) -> list[str]:
    """Số trong câu trả lời không có trong dữ liệu (sai số làm tròn theo số chữ số của chính số đó). Chỉ kiểm số thập phân,
    số ≥ 100 và phần trăm; số nguyên nhỏ (đếm nến, giờ) bỏ qua."""
    known = {x for src in sources for x in _numbers(src)}
    pct = {v * 100 for v in known if 0 <= v <= 1} | {v for v in known if 0 <= v <= 100}
    out: list[str] = []
    for m in NUM.finditer(SKIP.sub(" ", answer)):
        tok = m.group(0)
        parsed = _parse_number(tok)
        if parsed is None:
            continue
        v, ndec = parsed
        if tok.endswith("%"):
            ok = any(abs(v - p) <= 0.6 for p in pct)
        elif ndec or abs(v) >= 100:                # so trị tuyệt đối: «3972.71 - 3999.10» tách ra «-3999.10»
            tol = 0.5 * 10 ** -ndec + 1e-9
            ok = any(abs(abs(v) - abs(k)) <= tol for k in known)
        else:
            continue
        if not ok and tok not in out:
            out.append(tok)
    return out


def _call(client: httpx.Client, key: str, messages: list[dict[str, str]]) -> dict[str, Any]:
    body = {"model": model(), "messages": messages, "max_tokens": 2000,
            "reasoning": {"effort": "low", "exclude": True}}
    headers = {"Authorization": "Bearer " + key, "HTTP-Referer": "http://127.0.0.1",
               "X-OpenRouter-Title": "Market Structure Lab"}
    try:
        r = client.post(OPENROUTER_URL, json=body, headers=headers, timeout=TIMEOUT_S)
    except httpx.HTTPError as exc:
        raise ServiceError("Không gọi được OpenRouter: %s" % exc) from exc
    try:
        payload = r.json()
    except ValueError:
        payload = {}
    if r.status_code != 200:
        err = (payload.get("error") or {}).get("message") if isinstance(payload, dict) else None
        raise ServiceError("OpenRouter trả lỗi %d: %s" % (r.status_code, err or r.text[:300]))
    return payload


def _add_usage(total: dict[str, Any], usage: dict[str, Any]) -> None:
    """Cộng dồn token / chi phí qua các lần gọi của một lượt (lần thử lại cũng tính tiền)."""
    parts = {"prompt_tokens": usage.get("prompt_tokens"), "completion_tokens": usage.get("completion_tokens"),
             "cached_tokens": (usage.get("prompt_tokens_details") or {}).get("cached_tokens"), "cost": usage.get("cost")}
    for k, v in parts.items():
        total[k] = v if total.get(k) is None else total[k] + (v or 0)


def chat(feed_id: str, mode: str, question: str = "", history: Any = None, digits: int = 2, *,
         client: Optional[httpx.Client] = None) -> dict[str, Any]:
    """Một lượt: ``mode`` = tong_hop (câu lệnh tổng hợp của thuật toán) hoặc hoi (``question``); ``history`` = các tin
    {role: user | assistant, content} trước đó (route đã kiểm). Trả câu trả lời + nến dữ liệu, mô hình, token, chi phí,
    số lạ."""
    question = (question or "").strip()[:MAX_TEXT]
    key = _key()
    if not key:
        raise ServiceError(KEY_HINT_VI)
    if mode != "tong_hop" and not question:
        raise ServiceError("Chưa có câu hỏi.")
    hist = [{"role": m["role"], "content": m["content"][:MAX_TEXT]} for m in (history or [])[-MAX_HISTORY:]]
    ctx = live_manager.llm_context(feed_id, digits)
    data_json = json.dumps(ctx["data"], ensure_ascii=False, separators=(",", ":"))
    bar = ctx["data"]["nen_cuoi"]
    messages = ([{"role": "system", "content": RULES_VI + "\n" + ctx["glossary"]},      # cố định → cache được
                 {"role": "user", "content": "Dữ liệu ở nến cuối #%d (JSON):\n%s" % (bar["chi_so"], data_json)}]
                + hist + [{"role": "user", "content": ctx["summary"] if mode == "tong_hop" else question}])
    usage: dict[str, Any] = {}
    for attempt in range(2):               # nội dung rỗng thỉnh thoảng xảy ra → thử lại một lần (trừ khi hết token)
        payload = _call(client or _http(), key, messages)
        _add_usage(usage, payload.get("usage") or {})
        choice = (payload.get("choices") or [{}])[0]
        answer = ((choice.get("message") or {}).get("content") or "").strip()
        if answer:
            break
        if attempt or choice.get("finish_reason") == "length":
            raise ServiceError("Mô hình trả về rỗng (lý do: %s)." % (choice.get("finish_reason") or "không rõ"))
    user_text = [m["content"] for m in hist if m["role"] == "user"] + [question]   # số người dùng nêu được nhắc lại
    out = {
        "tra_loi": answer, "nen": bar["chi_so"], "nen_dong_luc": bar["dong_luc_utc"],
        "mo_hinh": payload.get("model") or model(), **usage,
        "so_la": unknown_numbers(answer, ctx["data"], ctx["glossary"], user_text),
        "cat_ngan": choice.get("finish_reason") == "length",
    }
    live_manager.store.add_llm_log(dict(
        out, feed_id=feed_id, at=live_manager.clock().isoformat(), mode=mode, cau_hoi=question,
        so_la=json.dumps(out["so_la"], ensure_ascii=False), cat_ngan=int(out["cat_ngan"]),
        data_sha256=hashlib.sha256(data_json.encode("utf-8")).hexdigest()), data_json)
    return out
