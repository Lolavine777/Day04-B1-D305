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

Research Agent của Team B1 nhận yêu cầu research, chọn tool phù hợp, và giữ boundary hỏi lại/xác nhận. Contract cố định gồm tra cứu Web và Twitter/X, đọc URL, định dạng kết quả, tra cứu policy/paper khi dùng, gửi Telegram có xác nhận, và `dedupe` để loại kết quả research trùng lặp mà vẫn giữ thứ tự đầu tiên.

**Link dùng thử (truy cập được trong showdown):**

> URL: Chưa có URL công khai được xác minh. Không ghi URL cho đến khi người dùng cung cấp và xác nhận truy cập từ thiết bị khác.

## A2. Tool agent có

| Tên tool | Làm được gì | Tool mới nhóm thêm? |
|---|---|---|
| clarify | Hỏi lại người dùng khi thiếu thông tin hoặc cần xác nhận yes/no | không |
| timeline | Lấy các bài đăng gần đây của một tài khoản Twitter | không |
| social_search | Tìm kiếm bài đăng Twitter theo từ khóa | không |
| lookup | Tìm kiếm tin tức trên Web | không |
| fetch | Đọc nội dung chi tiết của trang web từ URL | không |
| format | Định dạng danh sách kết quả thành markdown digest | không |
| send | Gửi nội dung Telegram sau boundary xác nhận | không (optional built-in) |
| policy | Tra cứu tài liệu policy nội bộ | không (optional built-in) |
| papers | Tìm paper arXiv | không (optional built-in) |
| paper_text | Đọc text của paper arXiv | không (optional built-in) |
| dedupe | Lọc các kết quả research bị lặp (theo URL / Title) | có (Team B1) |

## A3. Câu hỏi mẫu để thử

1. "Tin AI hôm nay có gì nổi bật?"
2. "Tóm tắt bài này giúp mình: https://example.com"
3. "Tìm các tweet phổ biến về OpenAI."
4. "Tóm tắt 5 tweet mới nhất giúp mình." (kiểm tra hỏi lại khi thiếu tài khoản)
5. "Đăng bản tin này lên Telegram giúp mình." (kiểm tra boundary xác nhận; không gửi khi chưa xác nhận)

## A4. Kịch bản demo

| Scenario | Tool trace cần thấy | Điều cần chứng minh | Evidence |
|---|---|---|---|
| 1. Research | `lookup` -> `dedupe` -> `format` khi phù hợp | Research dùng tool đúng và `dedupe` không phải tool tìm kiếm ban đầu | Chờ run/transcript thật |
| 2. Clarification | `clarify` với `response_type="text"` | Thiếu handle hoặc URL thì hỏi lại, không tự đoán | Chờ transcript thật |
| 3. Confirmation | `clarify` với `response_type="yes_no"` | Hành động gửi yêu cầu xác nhận trước; không thực hiện live-send trong eval | Chờ transcript hoặc dry-run thật |

---

# PHẦN B — Chi tiết / Bằng chứng

> Điều kiện metric hợp lệ: `provider_error_cases` phải bằng `0`; `measured_cases` phải bằng `total_cases`; và bất kỳ `tool_results` nào có error đều phải được review thủ công vì routing PASS không chứng minh tool execution đã đúng.

## B1. Version evidence

Fill from `artifacts/version_log.csv` and `runs/*.json`.

| Version | Prompt/tool change | Hypothesis | Metric name | Before | After | Run File |
|---|---|---|---|---:|---:|---|
| v0 | baseline (no artifact change) | The baseline's guess-and-act policy causes missing-information and confirmation-boundary failures | case_accuracy | N/A | 0.65 | `runs/v0_B_base_openrouter_20260729T153950029531.json` |
| v1 | artifacts/system_prompt.md | Explicit scope checks and confirmation boundaries will prevent guessing missing identifiers and unsafe send calls | case_accuracy | 0.65 | 0.90 | `runs/v1_B_base_openrouter_20260729T160816126255.json` |
| v2 | artifacts/tools.yaml | Explicit clarify response types and route-specific argument conventions will fix missing URL and news carryover failures | case_accuracy | 0.90 | 1.00 | `runs/v2_B_base_openrouter_20260729T161541190510.json` |
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
