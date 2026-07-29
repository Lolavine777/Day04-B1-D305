# Day 04 Lab v2 Report — Research Agent

> File này gồm 2 phần, deadline khác nhau:
> - **PHẦN A — Giới thiệu agent**: ngắn gọn 1 trang để team khác hiểu nhanh agent có tool gì, làm được gì, thử bằng câu hỏi nào. Xong trước 11:30 để làm tài liệu phụ trợ khi demo.
> - **PHẦN B — Chi tiết / Bằng chứng**: bảng đầy đủ (v0–v3, failure, eval, chat) dựa trên log thật. Có thể hoàn thiện sau buổi debate để nộp bài.

## Team

- Team: Team B1
- Members:
  - Nguyễn Đăng Long - 2A202601934
  - Lê Đăng Tấn - 2A202601916
  - Đào Minh Chiến - 2A202601184
  - Vũ Hữu An - 2A202601078
  - Nguyễn Trần Nghĩa - 2A202601664
- Provider/model: (Chờ xác nhận từ người dùng)

---

# PHẦN A — Giới thiệu agent

## A1. Agent này làm được gì

Research Agent đa năng của nhóm B1: Hỗ trợ tìm kiếm tin tức trên Web, tra cứu bài đăng Twitter/X, đọc & tóm tắt trang web, tra cứu tài liệu nội bộ, tự động lọc trùng dữ liệu research (`dedupe`), và yêu cầu xác nhận trước khi thực hiện các hành động nhạy cảm.

**Link dùng thử (truy cập được trong showdown):**

> URL: (Chờ cấu hình deployment / Cloudflare Tunnel)

## A2. Tool agent có

| Tên tool | Làm được gì | Tool mới nhóm thêm? |
|---|---|---|
| clarify | Hỏi lại người dùng khi thiếu thông tin hoặc cần xác nhận yes/no | không |
| timeline | Lấy các bài đăng gần đây của một tài khoản Twitter | không |
| social_search | Tìm kiếm bài đăng Twitter theo từ khóa | không |
| lookup | Tìm kiếm tin tức trên Web | không |
| fetch | Đọc nội dung chi tiết của trang web từ URL | không |
| format | Định dạng danh sách kết quả thành markdown digest | không |
| dedupe | Lọc các kết quả research bị lặp (theo URL / Title) | có (Team B1) |

## A3. Câu hỏi mẫu để thử

1. "Tin tức mới nhất về công nghệ AI tuần này là gì?"
2. "Tóm tắt bài viết tại link: https://openai.com/index/gpt-4o-mini/"
3. "Tóm tắt 5 tweet mới nhất giúp mình" (Kiểm tra phản hồi khi thiếu tên tài khoản)
4. "Đăng bản tin này lên Telegram giúp mình" (Kiểm tra xác nhận trước khi gửi)

## A4. Kịch bản demo đã rehearse

| Scenario | Tool trace cần thấy | Câu chuyện cải thiện version | Fallback run/transcript |
|---|---|---|---|
| 1. Tra cứu tin tức & Đọc URL | `lookup` -> `fetch` -> `dedupe` -> `format` | v0 chọn tool chưa chuẩn; v1+ gọi đúng luồng và tự lọc lặp kết quả | `transcripts/demo_research.transcript.json` |
| 2. Thiếu thông tin bắt buộc | `clarify` (response_type="text") | v0 tự đoán bừa người dùng; v1+ dừng lại hỏi xin thông tin còn thiếu | `transcripts/demo_clarify.transcript.json` |
| 3. Xác nhận hành động nhạy cảm | `clarify` (response_type="yes_no") | v0 kích hoạt tự gửi; v1+ buộc phải xin xác nhận Đồng ý/Không trước khi gửi | `transcripts/demo_confirm.transcript.json` |

---

# PHẦN B — Chi tiết / Bằng chứng

> Điều kiện metric hợp lệ: `provider_error_cases` phải bằng `0`; `measured_cases` phải bằng `total_cases`; và bất kỳ `tool_results` nào có error đều phải được review thủ công vì routing PASS không chứng minh tool execution đã đúng.

## B1. Version evidence

Fill from `artifacts/version_log.csv` and `runs/*.json`.

| Version | Prompt/tool change | Hypothesis | Metric name | Before | After | Run File |
|---|---|---|---|---:|---:|---|
| v0 | baseline |  |  |  |  |  |
| v1 |  |  |  |  |  |  |
| v2 |  |  |  |  |  |  |
| v3 |  |  |  |  |  |  |

## B2. Failure analysis

Use actual failures from `results[*].result.failures`.

| Case ID | Failure Type | Actual Tool Calls | What Failed | Fix |
|---|---|---|---|---|
|  |  |  |  |  |

## B3. Team eval cases

List the 10 cases added to `data/eval_group.json`:

- 5 single-turn
- 5 multi-turn

This section is for the mandatory team-authored eval set. Optional built-ins do
not belong here.

File template để trống có chủ đích; nhóm phải tự thiết kế đủ 10 case.

| Case ID | What It Tests | Expected Tool/Behavior | Result |
|---|---|---|---|
|  |  |  |  |

## B4. Live chat evidence

Use `transcripts/*.transcript.json`.

| Scenario/Turn | Version | Tool Calls + Args | Transcript/Run | Outcome |
|---|---|---|---|---|
|  |  |  |  |  |

## B5. Tool capability evidence

Phân loại rõ tool mới bắt buộc, optional built-in và tool đủ điều kiện bonus. Chỉ ghi Telegram/PDF nếu nhóm thực sự dùng; base report không cần chúng.

UI is core deliverable, not bonus. Do not list it here.

| Category | Evidence File | What Worked | Risk / Guardrail |
|---|---|---|---|
| Must-have: tool mới đầu tiên |  |  |  |
| Optional built-in |  |  |  |
| Bonus: tool mới thứ 4 trở đi |  |  |  |

## B6. Reflection

- Which fixes belonged in `system_prompt.md`?
- Which fixes belonged in `tools.yaml`?
- Which failure needed manual review instead of automatic grading?
- What would you improve next?
