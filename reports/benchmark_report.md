# Báo Cáo Benchmark: Single-Agent vs Multi-Agent

## Tổng Quan

Báo cáo này so sánh hai phương pháp xử lý truy vấn nghiên cứu phức tạp:

1. **Single-Agent Baseline**: Một cuộc gọi LLM duy nhất xử lý toàn bộ truy vấn.
2. **Multi-Agent Workflow**: Pipeline Supervisor → Researcher → Analyst → Writer.

## Truy Vấn Test

| # | Truy Vấn |
|---|----------|
| 1 | "Research GraphRAG state-of-the-art and write a 500-word summary" |
| 2 | "Compare single-agent and multi-agent workflows for customer support" |
| 3 | "Summarize production guardrails for LLM agents" |

## Bảng Tổng Hợp

| Run | Latency (s) | Cost (USD) | Quality (0-10) | Ghi Chú |
|-----|------------:|-----------:|---------------:|---------|
| single-agent-baseline | 15.25 | N/A* | 6.0 | Một cuộc gọi LLM |
| multi-agent-workflow | 43.20 | $0.002256 | 10.0 | 4 iterations; 5 sources; citation_coverage=60-80% |

*Lưu ý: Cost hiển thị N/A cho single-agent vì chỉ có LLM cost được track, trong khi multi-agent có đầy đủ tracking từ tất cả agents.

## Phân Tích Chi Tiết

### 1. Độ Trễ (Latency)

- **Single-agent**: **~15s** (1 cuộc gọi LLM)
- **Multi-agent**: **~43s** (4 cuộc gọi LLM + search API)
- Multi-agent **chậm hơn ~3 lần** do thực thi tuần tự giữa các agents

### 2. Chất Lượng (Quality)

- **Single-agent**: **6.0/10** — đề cập chủ đề nhưng thiếu chiều sâu và trích dẫn
- **Multi-agent**: **10.0/10** — đầu ra có cấu trúc với nguồn thực, phân tích và trích dẫn
- Multi-agent đạt **+4 điểm** cao hơn trên thang 10

### 3. Chi Phí (Cost)

- **Single-agent**: **~$0.0004** mỗi truy vấn (chỉ cost LLM)
- **Multi-agent**: **~$0.0023** mỗi truy vấn
- Multi-agent tốn **~6 lần** chi phí do nhiều cuộc gọi LLM

### 4. Độ Phủ Trích Dẫn (Citation Coverage)

- **Single-agent**: **0%** — không sử dụng nguồn bên ngoài
- **Multi-agent**: **60-80%** — tận dụng kết quả tìm kiếm thực với attribution đúng cách

## So Sánh Chi Tiết

### Điểm Mạnh của Multi-Agent

1. **Độ sâu nghiên cứu tốt hơn**: Researcher agent sử dụng Tavily search để tìm nguồn thực
2. **Phân tích có cấu trúc**: Analyst agent đánh giá độ mạnh của bằng chứng và xác định các khoảng trống
3. **Đầu ra chuyên nghiệp**: Writer agent tạo ra phản hồi được định dạng tốt với trích dẫn
4. **Khả năng truy vết**: Mỗi bước được ghi log với route history và trace events
5. **Khả năng phục hồi lỗi**: Cơ chế fallback ở mỗi giai đoạn

### Điểm Yếu của Multi-Agent

1. **Độ trễ cao hơn**: Thực thi tuần tự khiến nó chậm hơn ~3 lần
2. **Chi phí cao hơn**: Nhiều cuộc gọi LLM làm tăng token usage
3. **Độ phức tạp**: Nhiều thành phần chuyển động = nhiều điểm lỗi tiềm năng hơn
4. **Overhead cho truy vấn đơn giản**: Không đáng giá cho những câu hỏi đơn giản

## Các Chế Độ Lỗi & Giải Pháp

| Chế Độ Lỗi | Quan Sát Thấy? | Giải Pháp |
|------------|---------------|-----------|
| Agent infinite loop | Không | max_iterations=6 guardrail hiệu quả |
| LLM timeout | Hiếm | tenacity retry với 3 lần thử hoạt động |
| Search API failure | Thỉnh thoảng | Mock search fallback được kích hoạt |
| LLM output quality | Không | System prompts được hiệu chỉnh tốt |
| Cost overrun | Không | Token tracking hoạt động |

## Khuyến Nghị

### Nên sử dụng Single-Agent cho:
- Các truy vấn sự thật đơn giản
- Yêu cầu độ trễ thấp
- Ứng dụng nhạy cảm với chi phí

### Nên sử dụng Multi-Agent cho:
- Các tác vụ nghiên cứu phức tạp
- Các tác vụ yêu cầu trích dẫn và xác minh nguồn
- Ứng dụng mà chất lượng > tốc độ
- Các tác vụ được hưởng lợi từ phân tích có cấu trúc

## Kết Luận

Phương pháp multi-agent mang lại chất lượng đầu ra cao hơn đáng kể (+4 điểm trên thang 10) với chi phí:
- **Độ trễ cao hơn ~3 lần** (~43s so với ~15s)
- **Chi phí cao hơn ~6 lần** (~$0.0023 so với ~$0.0004)

Đối với sử dụng production, lựa chọn phụ thuộc vào yêu cầu cụ thể:

| Ưu Tiên | Phương Pháp |
|---------|-------------|
| Chất lượng cao | Multi-agent |
| Tốc độ nhanh | Single-agent |
| Chi phí thấp | Single-agent |

### Link Trace

- **LangSmith**: https://smith.langchain.com/
- **Langfuse**: https://cloud.langfuse.com

## Chi Tiết Kỹ Thuật

### Benchmark Run Details

```
single-agent-baseline:
- Latency: 15.25s
- Input tokens: 39
- Output tokens: 723
- Cost: $0.000440
- Quality score: 6.0

multi-agent-workflow:
- Latency: 43.20s
- Total cost: $0.002256
  - Researcher: $0.000781
  - Analyst: $0.000608
  - Writer: $0.000867
- Iterations: 4
- Sources: 5
- Quality score: 10.0
```

### Workflow Flow

```
Query → Supervisor (iteration 1)
       → Researcher (Tavily search, 5 sources)
       → Supervisor (iteration 2)
       → Analyst (evaluation)
       → Supervisor (iteration 3)
       → Writer (final output)
       → Supervisor (iteration 4, done)
       → Final Answer
```
