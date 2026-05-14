#!/usr/bin/env python3
"""
Copilot Diagnostic Parser v2.1 — Multi-Turn + Visual Timings

Changes from v2.0
─────────────────
• Multi-turn support: files with N questions now produce N turn rows + 6N step rows
• dq_map bug fix: dataQuestion entries matched by positional index (not tool_id string,
  which is a GUID that never matches the fc_... hex IDs in tool_calls)
• Per-turn flag detection: flags scanned only from that turn's content text, not the
  full raw file (prevents every turn getting the same flags)
• answer_type column: L0_VISUAL / L1_NL_DAX / ERROR / UNKNOWN
• context_turns column: number of prior conversational context events
• NEW visual_timings.csv: one row per visual scanned by Copilot (reportContentCopilot)
• sessions.csv: new copilot_agent_id and copilot_model_settings columns

Usage (Windows py launcher):
  py parse_diagnostics_v2.1.py --input diag.json --output-dir ./analysis/
  py parse_diagnostics_v2.1.py --input ./results/ --output-dir ./analysis/

Outputs (5 CSVs):
  sessions.csv          — 1 row per file
  turns.csv             — N rows per file (one per question/answer pair)
  steps.csv             — 6N rows per file (6 pipeline steps per turn)
  visual_citations.csv  — variable (one per visual cited in each answer)
  visual_timings.csv    — NEW: one per visual scanned at session start

Schema overview
───────────────
sessions.csv
  file_name · session_id · copilot_session_id · file_timestamp
  client_version · service_version · consumption_method
  copilot_agent_id · copilot_model_settings          ← NEW v2.1

turns.csv
  file_name · session_id · copilot_session_id · turn_index · request_id
  user_question · user_utterance · restatement · semantic_score
  user_created_at · reasoning_created_at · tool_dispatch_created_at
  user_to_reasoning_ms · reasoning_to_dispatch_ms · total_observed_ms
  tool_name · answer_text · answer_status · visuals_count
  answer_type · context_turns                         ← NEW v2.1
  warnings · errors · flags

steps.csv  ← bottleneck analysis table
  file_name · session_id · copilot_session_id · turn_index · step_index
  step_name · step_type · start_time · end_time · duration_ms
  input_summary · output_summary · status · notes

  step_type values:
    USER_INPUT          — question received (anchor; duration=0)
    LLM_ROUTING         — network + orchestrator routing to LLM
    LLM_REASONING       — LLM thinking before tool call
    TOOL_DISPATCH       — tool call fired; runtimeExecution measured here
    NL_INTERPRETATION   — Q&A model interprets utterance (internal to tool)
    ANSWER_DELIVERY     — final answer composed and returned

visual_citations.csv
  file_name · session_id · copilot_session_id · turn_index · cite_ref
  visual_id · visual_title · icon_type · page_name · section_id · url

visual_timings.csv  ← NEW v2.1
  file_name · copilot_session_id · visual_title · page_title · duration_seconds
"""

import csv
import json
import sys
import argparse
import re
from pathlib import Path
from datetime import datetime

# ─────────────────────────────────────────────────────────
# 1. TIMESTAMP HELPERS
# ─────────────────────────────────────────────────────────

_TS_FMTS = [
    "%m/%d/%Y, %I:%M:%S %p",   # 4/30/2026, 4:09:12 PM
    "%m/%d/%Y %I:%M:%S %p",    # 4/30/2026 4:09:12 PM
    "%m/%d/%Y, %H:%M:%S",      # 4/30/2026, 21:03:33
    "%m/%d/%Y %H:%M:%S",       # 04/30/2026 21:03:33
    "%Y-%m-%dT%H:%M:%S.%fZ",   # ISO
    "%Y-%m-%dT%H:%M:%SZ",
]


def parse_ts(raw: str) -> datetime | None:
    if not raw:
        return None
    raw = raw.strip()
    for fmt in _TS_FMTS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            pass
    return None


def delta_ms(start: datetime | None, end: datetime | None) -> str:
    """Return ms duration as string, or '' if either is None."""
    if start is None or end is None:
        return ""
    return str(int((end - start).total_seconds() * 1000))


# ─────────────────────────────────────────────────────────
# 2. LOW-LEVEL JSON EXTRACTORS
# ─────────────────────────────────────────────────────────

def _text_value(obj) -> str:
    """Safely pull .text.value or .text from a content object."""
    if isinstance(obj, dict):
        t = obj.get("text")
        if isinstance(t, dict):
            return str(t.get("value", ""))
        if isinstance(t, str):
            return t
    return ""


def _content_text(content) -> str:
    """Extract the first text value from a content array."""
    if isinstance(content, list):
        for item in content:
            v = _text_value(item)
            if v:
                return v
    if isinstance(content, dict):
        return _text_value(content)
    return ""


def _created_at(entry: dict) -> str:
    meta = entry.get("metadata") or {}
    return str(meta.get("createdAt", ""))


def _content_to_text_blob(content_list: list) -> str:
    """Serialize the whole content list to a text string for flag scanning."""
    try:
        return json.dumps(content_list, ensure_ascii=False)
    except Exception:
        return str(content_list)


# ─────────────────────────────────────────────────────────
# 3. VISUAL CITATION EXTRACTOR
# ─────────────────────────────────────────────────────────

def extract_visual_citations(content_list: list, file_name: str,
                              session_id: str, copilot_session_id: str,
                              turn_index: int) -> list[dict]:
    rows = []
    for item in content_list:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "annotation":
            continue
        ann = item.get("annotation")
        if not isinstance(ann, dict):
            continue
        if ann.get("type") != "powerbi-visual":
            continue
        meta = ann.get("metadata") or {}
        if isinstance(meta, str):
            # PowerShell-serialised string — best-effort extraction
            visual_id = re.search(r"visualId=(\S+?);", meta)
            section_id = re.search(r"sectionId=(\S+?);", meta)
            title = re.search(r"visualTitle=(.*?);", meta)
            icon = re.search(r"icon=(\S+?);", meta)
            page = re.search(r"pageName=(.*?)(?:;|$)", meta)
            url = re.search(r"url=(https?://\S+?)(?:;|\s)", meta)
            rows.append({
                "file_name": file_name,
                "session_id": session_id,
                "copilot_session_id": copilot_session_id,
                "turn_index": turn_index,
                "cite_ref": ann.get("id", ""),
                "visual_id": visual_id.group(1) if visual_id else "",
                "visual_title": title.group(1).strip() if title else ann.get("text", ""),
                "icon_type": icon.group(1) if icon else "",
                "page_name": page.group(1).strip() if page else "",
                "section_id": section_id.group(1) if section_id else "",
                "url": url.group(1) if url else "",
            })
        else:
            rows.append({
                "file_name": file_name,
                "session_id": session_id,
                "copilot_session_id": copilot_session_id,
                "turn_index": turn_index,
                "cite_ref": ann.get("id", ""),
                "visual_id": meta.get("visualId", ""),
                "visual_title": meta.get("visualTitle", ann.get("text", "")),
                "icon_type": meta.get("icon", ""),
                "page_name": meta.get("pageName", ""),
                "section_id": meta.get("sectionId", ""),
                "url": meta.get("url", ""),
            })
    return rows


# ─────────────────────────────────────────────────────────
# 4. VISUAL TIMINGS EXTRACTOR  (NEW v2.1)
# ─────────────────────────────────────────────────────────

def extract_visual_timings(data: dict, file_name: str, copilot_session_id: str) -> list[dict]:
    """
    Extract reportContentCopilot.visualTimings — the per-visual render scan
    Copilot performs before answering.  Returns [] if field absent.
    """
    rcc = data.get("reportContentCopilot") or {}
    timings = rcc.get("visualTimings") or []
    rows = []
    for vt in timings:
        if not isinstance(vt, dict):
            continue
        rows.append({
            "file_name": file_name,
            "copilot_session_id": copilot_session_id,
            "visual_title": vt.get("visualTitle", ""),
            "page_title": vt.get("pageTitle", ""),
            "duration_seconds": vt.get("durationInSeconds", ""),
        })
    return rows


# ─────────────────────────────────────────────────────────
# 5. KNOWN WARNING FLAGS
# ─────────────────────────────────────────────────────────

_KNOWN_FLAGS = [
    "AgentSchemaHeavilyReduced",
    "DataIndexSizeLimitReached",
    "StaleDataIndex",
    "StaleDomainModel",
    "DataIndexNotReady",
    "NoDataIndexAvailable",
    "SchemaNotAvailable",
    "ModelNotSupported",
    "CapacityThrottled",
    "TokenLimitExceeded",
]


def _detect_flags_in_text(text: str) -> list[str]:
    """Return only flags present in the given text blob (per-turn, not full file)."""
    return [f for f in _KNOWN_FLAGS if f in text]


# ─────────────────────────────────────────────────────────
# 6. CORE: PARSE ONE JSON DIAGNOSTIC FILE
# ─────────────────────────────────────────────────────────

def parse_json_file(filepath: Path) -> dict:
    """
    Returns {sessions, turns, steps, visual_citations, visual_timings}.

    v2.1 changes:
    - dq matching: positional index (dq_list[turn_idx]) not tool_id string match
    - flag detection: scoped to per-turn content blob, not full raw file
    - answer_type: L0_VISUAL / L1_NL_DAX / ERROR / UNKNOWN
    - context_turns: count of prior contextEvents in interpretRequest
    - visual_timings: extracted from reportContentCopilot.visualTimings
    - sessions: copilot_agent_id + copilot_model_settings added
    """
    raw = filepath.read_text(encoding="utf-8", errors="ignore")
    data = json.loads(raw)

    file_name = filepath.name
    session_id = data.get("sessionId", "")
    copilot_session_id = data.get("copilotSessionId", "")
    file_timestamp = data.get("timestamp", "")
    client_version = data.get("clientVersion", "")
    service_version = data.get("serviceVersion", "")
    consumption_method = data.get("consumptionMethod", "")
    copilot_agent_id = data.get("CopilotAgentId", "")

    model_settings = data.get("copilotModelSettings")
    copilot_model_settings = json.dumps(model_settings, ensure_ascii=False) if model_settings else ""

    session_row = {
        "file_name": file_name,
        "session_id": session_id,
        "copilot_session_id": copilot_session_id,
        "file_timestamp": file_timestamp,
        "client_version": client_version,
        "service_version": service_version,
        "consumption_method": consumption_method,
        "copilot_agent_id": copilot_agent_id,
        "copilot_model_settings": copilot_model_settings,
    }

    # ── Build ordered dq_list (positional, matches turn order) ──────
    # v2.0 bug: matched by tool_id string which is a GUID, but tool_calls[0].id
    # is a different fc_... hex string — they never match.
    # Fix: dataQuestion entries appear in the same order as turns in chatHistory.
    dq_list: list[dict] = []
    for _key, dq in (data.get("dataQuestion") or {}).items():
        interp_req = dq.get("interpretRequest") or {}
        conv_ctx = interp_req.get("conversationalContext") or {}
        ctx_events = conv_ctx.get("contextEvents") or []
        context_turns = len(ctx_events)

        interp_resp = dq.get("interpretResponse") or {}
        restatements = interp_resp.get("restatements") or []
        diagnostics = interp_resp.get("diagnostics") or []
        errors_list = interp_resp.get("errors") or []
        warnings_list = interp_resp.get("warnings") or []

        semantic_score = ""
        if diagnostics and diagnostics[0]:
            raw_sem = str(diagnostics[0].get("anonymizedSemantics", ""))
            m = re.search(r"\[?(\d+\.\d+)", raw_sem)
            if m:
                semantic_score = m.group(1)

        dq_list.append({
            "utterance": dq.get("utterance", ""),
            "restatement": "; ".join(str(r) for r in restatements),
            "semantic_score": semantic_score,
            "warnings": "; ".join(str(w) for w in warnings_list),
            "errors": "; ".join(str(e) for e in errors_list),
            "context_turns": context_turns,
        })

    # ── Extract visual timings (session-level, not per-turn) ─────────
    visual_timings_out = extract_visual_timings(data, file_name, copilot_session_id)

    # ── Group chatHistory into turns ─────────────────────────────────
    history: list = data.get("chatHistory") or []
    turn_groups: list[list[dict]] = []
    current: list[dict] = []
    for entry in history:
        role = entry.get("role", "")
        if role == "user" and current:
            turn_groups.append(current)
            current = [entry]
        else:
            current.append(entry)
    if current:
        turn_groups.append(current)

    turns_out: list[dict] = []
    steps_out: list[dict] = []
    visuals_out: list[dict] = []

    for turn_idx, group in enumerate(turn_groups, start=1):
        user_entry = next((e for e in group if e.get("role") == "user"), None)
        asst_entries = [e for e in group if e.get("role") == "assistant"]
        reasoning_entry = next((e for e in asst_entries if not e.get("tool_calls")), None)
        dispatch_entry = next((e for e in asst_entries if e.get("tool_calls")), None)
        tool_result_entry = next((e for e in group if e.get("role") == "tool"), None)

        # ── Timestamps ──────────────────────────────────────────────
        user_ts_raw = _created_at(user_entry) if user_entry else ""
        reasoning_ts_raw = _created_at(reasoning_entry) if reasoning_entry else ""
        dispatch_ts_raw = _created_at(dispatch_entry) if dispatch_entry else ""

        user_ts = parse_ts(user_ts_raw)
        reasoning_ts = parse_ts(reasoning_ts_raw)
        dispatch_ts = parse_ts(dispatch_ts_raw)

        user_to_reasoning_ms = delta_ms(user_ts, reasoning_ts)
        reasoning_to_dispatch_ms = delta_ms(reasoning_ts, dispatch_ts)
        total_observed_ms = delta_ms(user_ts, dispatch_ts)

        # ── User question ────────────────────────────────────────────
        user_question = ""
        if user_entry:
            user_question = _content_text(user_entry.get("content", []))

        # ── LLM Reasoning ────────────────────────────────────────────
        reasoning_text = ""
        if reasoning_entry:
            reasoning_text = _content_text(
                [reasoning_entry.get("reasoning")] if reasoning_entry.get("reasoning") else []
            )

        # ── Tool call details ────────────────────────────────────────
        request_id = ""
        tool_name = ""
        user_utterance = ""
        tool_call_id = ""
        runtime_exec_ms = ""
        if reasoning_entry:
            request_id = reasoning_entry.get("orchestratorRequestId", "")
        if dispatch_entry:
            if not request_id:
                request_id = dispatch_entry.get("orchestratorRequestId", "")
            tcs = dispatch_entry.get("tool_calls") or []
            if tcs:
                tc = tcs[0] if isinstance(tcs, list) else tcs
                if tc:
                    tool_call_id = tc.get("id", "")
                    tool_name = (tc.get("function") or {}).get("name", "")
                    try:
                        args = json.loads((tc.get("function") or {}).get("arguments", "{}"))
                        user_utterance = args.get("userUtterance", "")
                    except (json.JSONDecodeError, TypeError):
                        user_utterance = ""
                    re_val = tc.get("runtimeExecution")
                    if re_val is not None and re_val != 0:
                        runtime_exec_ms = str(int(re_val * 1000))

        # ── Tool result / answer ─────────────────────────────────────
        answer_text = ""
        answer_status = ""
        flags: list[str] = []
        visuals_count = 0

        if tool_result_entry:
            result = tool_result_entry.get("result") or {}
            answer_status = (result.get("status") or {}).get("kind", "")
            content_list = tool_result_entry.get("content") or []
            answer_text = _content_text(content_list)

            vcites = extract_visual_citations(
                content_list, file_name, session_id, copilot_session_id, turn_idx
            )
            visuals_out.extend(vcites)
            visuals_count = len(vcites)

            # v2.1: flag detection scoped to THIS turn's content only
            turn_blob = _content_to_text_blob(content_list)
            flags = _detect_flags_in_text(turn_blob)

        # ── dq_info: positional match (fix for v2.0 bug) ────────────
        # turn_idx is 1-based; dq_list is 0-based
        dq_info: dict = {}
        dq_zero_idx = turn_idx - 1
        if 0 <= dq_zero_idx < len(dq_list):
            dq_info = dq_list[dq_zero_idx]
        elif dq_list:
            # fallback: try utterance match
            utt_lower = user_utterance.lower() or user_question.lower()
            for dq in dq_list:
                if utt_lower and (dq["utterance"].lower() in utt_lower or
                                  utt_lower in dq["utterance"].lower()):
                    dq_info = dq
                    break

        restatement = dq_info.get("restatement", "")
        semantic_score = dq_info.get("semantic_score", "")
        dq_warnings = dq_info.get("warnings", "")
        dq_errors = dq_info.get("errors", "")
        context_turns = dq_info.get("context_turns", 0)

        # ── Answer type classification (NEW v2.1) ────────────────────
        if visuals_count > 0:
            answer_type = "L0_VISUAL"
        elif "NL to DAX" in answer_text or "Q&A responded" in answer_text or "DAX fallback" in answer_text:
            answer_type = "L1_NL_DAX"
        elif dq_errors and visuals_count == 0 and not answer_text:
            answer_type = "ERROR"
        elif answer_text and visuals_count == 0:
            # Plain text answer with no visual — likely L1 fallback
            answer_type = "L1_NL_DAX"
        else:
            answer_type = "UNKNOWN"

        # ── Build turn row ───────────────────────────────────────────
        turn_row = {
            "file_name": file_name,
            "session_id": session_id,
            "copilot_session_id": copilot_session_id,
            "turn_index": turn_idx,
            "request_id": request_id,
            "user_question": user_question,
            "user_utterance": user_utterance,
            "restatement": restatement,
            "semantic_score": semantic_score,
            "user_created_at": user_ts_raw,
            "reasoning_created_at": reasoning_ts_raw,
            "tool_dispatch_created_at": dispatch_ts_raw,
            "user_to_reasoning_ms": user_to_reasoning_ms,
            "reasoning_to_dispatch_ms": reasoning_to_dispatch_ms,
            "total_observed_ms": total_observed_ms,
            "tool_name": tool_name,
            "answer_text": answer_text,
            "answer_status": answer_status,
            "visuals_count": visuals_count,
            "answer_type": answer_type,
            "context_turns": context_turns,
            "warnings": dq_warnings,
            "errors": dq_errors,
            "flags": "; ".join(flags),
        }
        turns_out.append(turn_row)

        # ── Build step rows ──────────────────────────────────────────
        base = {
            "file_name": file_name,
            "session_id": session_id,
            "copilot_session_id": copilot_session_id,
            "turn_index": turn_idx,
        }

        steps_out.append({**base,
            "step_index": 1,
            "step_name": "User Input",
            "step_type": "USER_INPUT",
            "start_time": user_ts_raw,
            "end_time": user_ts_raw,
            "duration_ms": "0",
            "input_summary": user_question,
            "output_summary": "",
            "status": "ok",
            "notes": "",
        })

        steps_out.append({**base,
            "step_index": 2,
            "step_name": "LLM Routing",
            "step_type": "LLM_ROUTING",
            "start_time": user_ts_raw,
            "end_time": reasoning_ts_raw,
            "duration_ms": user_to_reasoning_ms,
            "input_summary": user_question,
            "output_summary": "Reached orchestrator",
            "status": "ok" if user_to_reasoning_ms != "" else "no_timestamp",
            "notes": "Includes network + orchestrator routing latency",
        })

        reasoning_summary = (reasoning_text[:120] + "…") if len(reasoning_text) > 120 else reasoning_text
        steps_out.append({**base,
            "step_index": 3,
            "step_name": "LLM Reasoning",
            "step_type": "LLM_REASONING",
            "start_time": reasoning_ts_raw,
            "end_time": dispatch_ts_raw,
            "duration_ms": reasoning_to_dispatch_ms,
            "input_summary": user_question,
            "output_summary": reasoning_summary or "(no reasoning logged)",
            "status": "ok" if reasoning_to_dispatch_ms != "" else "no_timestamp",
            "notes": "",
        })

        dispatch_notes = []
        if runtime_exec_ms:
            dispatch_notes.append(f"runtimeExecution={runtime_exec_ms}ms")
        steps_out.append({**base,
            "step_index": 4,
            "step_name": "Tool Dispatch",
            "step_type": "TOOL_DISPATCH",
            "start_time": dispatch_ts_raw,
            "end_time": "",
            "duration_ms": runtime_exec_ms,
            "input_summary": f'{tool_name}(userUtterance="{user_utterance}")',
            "output_summary": f"tool_call_id={tool_call_id}",
            "status": "ok" if tool_name else "unknown",
            "notes": "; ".join(dispatch_notes),
        })

        interp_notes = []
        if dq_warnings:
            interp_notes.append(f"warnings={dq_warnings}")
        if dq_errors:
            interp_notes.append(f"errors={dq_errors}")
        score_prefix = f"semantic_score={semantic_score}; " if semantic_score else ""
        steps_out.append({**base,
            "step_index": 5,
            "step_name": "NL Interpretation",
            "step_type": "NL_INTERPRETATION",
            "start_time": "",
            "end_time": "",
            "duration_ms": "",
            "input_summary": user_utterance,
            "output_summary": restatement,
            "status": "ok" if not dq_errors else "error",
            "notes": score_prefix + "; ".join(interp_notes),
        })

        vis_summary = f"{visuals_count} visual(s) cited"
        answer_summary = (answer_text[:120] + "…") if len(answer_text) > 120 else answer_text
        steps_out.append({**base,
            "step_index": 6,
            "step_name": "Answer Delivery",
            "step_type": "ANSWER_DELIVERY",
            "start_time": "",
            "end_time": "",
            "duration_ms": "",
            "input_summary": restatement,
            "output_summary": answer_summary,
            "status": answer_status.lower() if answer_status else "unknown",
            "notes": (vis_summary + f"; answer_type={answer_type}" +
                      (f"; flags={'; '.join(flags)}" if flags else "")),
        })

    return {
        "sessions": [session_row],
        "turns": turns_out,
        "steps": steps_out,
        "visual_citations": visuals_out,
        "visual_timings": visual_timings_out,
    }


# ─────────────────────────────────────────────────────────
# 7. LEGACY .TXT FALLBACK (same as v2.0)
# ─────────────────────────────────────────────────────────

def parse_txt_fallback(filepath: Path) -> dict:
    """Minimal extraction for text-dump files (regex-based, v2.0 compat)."""
    text = filepath.read_text(encoding="utf-8", errors="ignore")
    file_name = filepath.name

    def safe(pattern, t, group=1, flags=re.DOTALL):
        m = re.search(pattern, t, flags)
        return m.group(group).strip() if m else ""

    session_id = safe(r"copilotSessionId\s+(\S+)", text)
    ts = safe(r"timestamp\s+([\d\-T:.]+Z)", text)

    q_raw = safe(r'role\s+user\s+content\s+type\s+text\s+text\s+value\s+(.*?)(?=\s*metadata\s+createdAt|\s*role\s+(?:assistant|tool)|$)', text)
    if not q_raw:
        q_raw = safe(r'"role"\s*:\s*"user"[^}]{0,200}"value"\s*:\s*"(.*?)"', text)

    utterance = safe(r'"userUtterance"\s*:\s*"(.*?)"', text)
    if not utterance:
        utterance = safe(r'utterance\s+(.*?)(?=\s+interpretRequest|\s+tool_id|$)', text)

    restatement = safe(r'"restatements?"\s*:\s*\[\s*"(.*?)"', text)
    answer = safe(r'"textualAnswer"\s*:\s*"(.*?)"', text)
    sem = safe(r'"anonymizedSemantics"\s*:\s*"\[(\d+\.\d+)', text)

    flags_found = "; ".join([f for f in _KNOWN_FLAGS if f in text])

    turn_row = {
        "file_name": file_name, "session_id": session_id, "copilot_session_id": "",
        "turn_index": 1, "request_id": safe(r"orchestratorRequestId\s+(\S+)", text),
        "user_question": q_raw, "user_utterance": utterance,
        "restatement": restatement, "semantic_score": sem,
        "user_created_at": "", "reasoning_created_at": "",
        "tool_dispatch_created_at": "", "user_to_reasoning_ms": "",
        "reasoning_to_dispatch_ms": "", "total_observed_ms": "",
        "tool_name": safe(r"toolName\s+(\S+)", text) or ("answerDataQuestion" if "answerDataQuestion" in text else ""),
        "answer_text": answer, "answer_status": "",
        "visuals_count": 0, "answer_type": "UNKNOWN", "context_turns": 0,
        "warnings": "", "errors": "", "flags": flags_found,
    }
    session_row = {
        "file_name": file_name, "session_id": session_id, "copilot_session_id": "",
        "file_timestamp": ts, "client_version": safe(r"clientVersion\s+(\S+)", text),
        "service_version": safe(r"serviceVersion\s+(\S+)", text),
        "consumption_method": safe(r"consumptionMethod\s+(.+?)(?=clientVersion|$)", text),
        "copilot_agent_id": "", "copilot_model_settings": "",
    }
    return {
        "sessions": [session_row],
        "turns": [turn_row],
        "steps": [],
        "visual_citations": [],
        "visual_timings": [],
    }


# ─────────────────────────────────────────────────────────
# 8. FILE ROUTER
# ─────────────────────────────────────────────────────────

def parse_file(filepath: Path) -> dict:
    if filepath.suffix.lower() == ".json":
        try:
            return parse_json_file(filepath)
        except json.JSONDecodeError as e:
            print(f"  WARNING: {filepath.name} is not valid JSON ({e}); trying text fallback")
            return parse_txt_fallback(filepath)
    else:
        return parse_txt_fallback(filepath)


# ─────────────────────────────────────────────────────────
# 9. CSV WRITERS
# ─────────────────────────────────────────────────────────

SESSIONS_COLS = [
    "file_name", "session_id", "copilot_session_id", "file_timestamp",
    "client_version", "service_version", "consumption_method",
    "copilot_agent_id", "copilot_model_settings",
]
TURNS_COLS = [
    "file_name", "session_id", "copilot_session_id", "turn_index", "request_id",
    "user_question", "user_utterance", "restatement", "semantic_score",
    "user_created_at", "reasoning_created_at", "tool_dispatch_created_at",
    "user_to_reasoning_ms", "reasoning_to_dispatch_ms", "total_observed_ms",
    "tool_name", "answer_text", "answer_status", "visuals_count",
    "answer_type", "context_turns",
    "warnings", "errors", "flags",
]
STEPS_COLS = [
    "file_name", "session_id", "copilot_session_id", "turn_index", "step_index",
    "step_name", "step_type",
    "start_time", "end_time", "duration_ms",
    "input_summary", "output_summary", "status", "notes",
]
VISUALS_COLS = [
    "file_name", "session_id", "copilot_session_id", "turn_index", "cite_ref",
    "visual_id", "visual_title", "icon_type", "page_name", "section_id", "url",
]
VISUAL_TIMINGS_COLS = [
    "file_name", "copilot_session_id", "visual_title", "page_title", "duration_seconds",
]


def write_csv(path: Path, cols: list[str], rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  ✓ {path.name:35s} {len(rows):>4} row(s)")


# ─────────────────────────────────────────────────────────
# 10. MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Parse Power BI Copilot diagnostic JSON exports — v2.1 multi-turn."
    )
    parser.add_argument("--input", "-i", default="./diagnostics/",
                        help="Path to a .json file or directory (default: ./diagnostics/)")
    parser.add_argument("--output-dir", "-o", default=None,
                        help="Directory to write output CSVs (default: same as input)")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    input_path = Path(args.input)

    if input_path.is_file():
        files = [input_path]
        out_dir = Path(args.output_dir) if args.output_dir else input_path.parent
    elif input_path.is_dir():
        files = sorted(input_path.glob("*.json")) + sorted(input_path.glob("*.txt"))
        out_dir = Path(args.output_dir) if args.output_dir else input_path
        if not files:
            print(f"ERROR: No .json or .txt files found in {input_path}")
            sys.exit(1)
    else:
        print(f"ERROR: Path not found: {input_path}")
        sys.exit(1)

    out_dir.mkdir(parents=True, exist_ok=True)

    all_sessions, all_turns, all_steps, all_visuals, all_timings = [], [], [], [], []

    print(f"\nParsing {len(files)} file(s)  [parse_diagnostics_v2.1]...")
    for f in files:
        if args.verbose:
            print(f"  → {f.name}")
        try:
            result = parse_file(f)
            all_sessions.extend(result["sessions"])
            all_turns.extend(result["turns"])
            all_steps.extend(result["steps"])
            all_visuals.extend(result["visual_citations"])
            all_timings.extend(result["visual_timings"])
            if args.verbose:
                print(f"    turns={len(result['turns'])}  steps={len(result['steps'])}  "
                      f"visuals={len(result['visual_citations'])}  "
                      f"timings={len(result['visual_timings'])}")
        except Exception as e:
            print(f"  ERROR {f.name}: {e}")
            import traceback; traceback.print_exc()

    print(f"\nWriting outputs to: {out_dir}")
    write_csv(out_dir / "sessions.csv",         SESSIONS_COLS,       all_sessions)
    write_csv(out_dir / "turns.csv",            TURNS_COLS,          all_turns)
    write_csv(out_dir / "steps.csv",            STEPS_COLS,          all_steps)
    write_csv(out_dir / "visual_citations.csv", VISUALS_COLS,        all_visuals)
    write_csv(out_dir / "visual_timings.csv",   VISUAL_TIMINGS_COLS, all_timings)

    # Quick bottleneck summary
    print("\n── Bottleneck Summary ───────────────────────────────────────")
    for turn in all_turns:
        ms_route = str(turn["user_to_reasoning_ms"]).rjust(6)
        ms_think = str(turn["reasoning_to_dispatch_ms"]).rjust(6)
        ms_total = str(turn["total_observed_ms"]).rjust(6)
        atype = turn.get("answer_type", "")
        q = turn["user_question"]
        if len(q) > 60:
            q = q[:57] + "..."
        print(f"  [{turn['turn_index']:>2}] {q}")
        print(f"       LLM routing : {ms_route} ms | LLM reasoning: {ms_think} ms | total: {ms_total} ms | {atype}")
        if turn["flags"]:
            print(f"       ⚠  flags   : {turn['flags']}")
        if turn["errors"]:
            print(f"       ✗  errors  : {turn['errors']}")
    print()


if __name__ == "__main__":
    main()
