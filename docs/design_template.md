# Design Template

## Problem

Hệ thống cần xử lý các truy vấn nghiên cứu phức tạp — tìm kiếm nguồn, phân tích và tổng hợp kết quả thành báo cáo hoàn chỉnh có citations. Một single agent phải thực hiện tất cả các bước: search, analyze, write trong một prompt duy nhất, dẫn đến output chất lượng thấp, thiếu depth, và khó debug.

## Why multi-agent?

Single-agent gặp các hạn chế sau:
- **Context window overload**: Một prompt phải chứa cả hướng dẫn search, analyze, write → dễ "quên" instruction.
- **Không thể tách biệt failure**: Nếu search fail, không rõ analyst hay writer bị ảnh hưởng.
- **Thiếu specialization**: Mỗi task (research, analysis, writing) cần system prompt và temperature khác nhau.
- **Khó trace**: Không biết agent đang ở bước nào, không thể retry riêng từng bước.
- **Không mở rộng được**: Thêm critic hoặc fact-checker phải rewrite toàn bộ prompt.

Multi-agent cho phép:
- Mỗi agent chuyên một responsibility → output chất lượng hơn.
- Supervisor kiểm soát luồng → có thể retry/fallback từng bước.
- Shared state rõ ràng → dễ debug và benchmark.

## Agent roles

| Agent | Responsibility | Input | Output | Failure mode |
|---|---|---|---|---|
| Supervisor | Routing decision: chọn agent tiếp theo | Full ResearchState | Route (researcher/analyst/writer/done) | Loop vô hạn → max_iterations guard |
| Researcher | Tìm nguồn, tạo research notes | Query + search results | sources[], research_notes | Search API fail → mock fallback |
| Analyst | Phân tích, trích key claims, đánh giá evidence | research_notes + sources | analysis_notes | LLM fail → pass raw notes |
| Writer | Tổng hợp thành final response với citations | research_notes + analysis_notes | final_answer | LLM fail → compile raw notes |
| Critic (optional) | Fact-check, citation coverage, hallucination check | final_answer + sources | review report in agent_results | LLM fail → skip review |

## Shared state

| Field | Type | Lý do cần |
|---|---|---|
| `request` | ResearchQuery | Query gốc + audience + max_sources config |
| `iteration` | int | Đếm số vòng lặp để enforce max_iterations |
| `route_history` | list[str] | Trace routing decisions cho debug |
| `sources` | list[SourceDocument] | Sources từ Researcher cho Analyst và Writer dùng |
| `research_notes` | str \| None | Output của Researcher → input cho Analyst |
| `analysis_notes` | str \| None | Output của Analyst → input cho Writer |
| `final_answer` | str \| None | Output cuối cùng từ Writer |
| `agent_results` | list[AgentResult] | Chi tiết output + metadata (tokens, cost) mỗi agent |
| `trace` | list[dict] | Event trace cho observability |
| `errors` | list[str] | Accumulated errors cho error rate tracking |

## Routing policy

```text
START → Supervisor
         ↓
    [Check state]
         ↓
    ┌─────────────────────────────────────────┐
    │ No research_notes? → Route: researcher  │
    │ No analysis_notes? → Route: analyst     │
    │ No final_answer?   → Route: writer      │
    │ Has final_answer?  → Route: done → END  │
    │ Max iterations?    → Force done → END   │
    └─────────────────────────────────────────┘
         ↓
    Worker executes → updates state → back to Supervisor
```

Supervisor dùng rule-based routing (fast path). Nếu state không rõ ràng, fallback sang LLM call để quyết định route.

## Guardrails

- **Max iterations**: 6 (cấu hình qua `MAX_ITERATIONS` env var)
- **Timeout**: 60 seconds per agent (cấu hình qua `TIMEOUT_SECONDS`)
- **Retry**: LLM calls sử dụng `tenacity` với 3 attempts, exponential backoff
- **Fallback**: Mỗi agent có fallback khi LLM fail (raw notes, mock search, etc.)
- **Validation**: Pydantic schemas validate tất cả input/output. State immutable checks.

## Benchmark plan

| Query | Metric | Expected Outcome |
|---|---|---|
| "Research GraphRAG state-of-the-art and write a 500-word summary" | Latency, Quality, Cost | Multi-agent chậm hơn 2-4x nhưng quality cao hơn 2-3 điểm |
| "Compare single-agent and multi-agent workflows for customer support" | Citation coverage | Multi-agent có nhiều sources hơn |
| "Summarize production guardrails for LLM agents" | Error rate | Cả hai approach đều 0% error rate |
