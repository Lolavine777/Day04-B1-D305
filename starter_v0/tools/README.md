# Research Agent Tools

Thư mục này chứa toàn bộ tool mà Research Agent có thể gọi. Hiện dự án có
**14 tool**; tên trong thư mục, `TOOL_FUNCTIONS` và
`artifacts/tools.yaml` phải luôn đồng bộ.

## Danh sách tool

| Tool | Track | Chức năng | Env/side effect |
|---|---|---|---|
| `clarify` | core | Hỏi lại khi thiếu dữ liệu hoặc cần xác nhận | Không |
| `timeline` | core | Tìm bài đăng gần đây của một tài khoản X/Twitter | `TAVILY_API_KEY` |
| `social_search` | core | Tìm bài đăng X/Twitter theo chủ đề | `TAVILY_API_KEY` |
| `lookup` | core | Tìm kiếm web/news | `TAVILY_API_KEY` |
| `fetch` | core | Đọc một URL cụ thể qua Firecrawl | `FIRECRAWL_API_KEY` |
| `format` | core | Format items thành digest, bullets hoặc thread | Không |
| `dedupe` | core, team-authored | Loại item trùng URL/title, giữ thứ tự đầu tiên | Không |
| `send` | bonus built-in | Gửi plain text lên Telegram sau xác nhận | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, external write |
| `policy` | bonus built-in | Tìm trong company policy cục bộ | Không |
| `papers` | bonus built-in | Tìm paper qua arXiv | `ARXIV_USER_AGENT` |
| `paper_text` | bonus built-in | Tải PDF arXiv và trích text | `ARXIV_USER_AGENT`, local file write |
| `compare_sources` | bonus, team-authored | So sánh structured claims giữa nhiều nguồn | Không |
| `citation_audit` | bonus, team-authored | Kiểm tra claim có URL và tên nguồn hợp lệ | Không |
| `export_report` | bonus, team-authored | Render báo cáo hoàn chỉnh thành Markdown/JSON | Không |

Bốn tool do team tự viết là `dedupe`, `compare_sources`, `citation_audit` và
`export_report`. Bốn optional tool có sẵn (`send`, `policy`, `papers`,
`paper_text`) không được tính là tool mới của team.

## Workflow khuyến nghị

```text
lookup / timeline / social_search / fetch / papers
                         |
                       dedupe
                         |
                  compare_sources
                         |
                   citation_audit
                         |
                format / export_report
                         |
              clarify -> send (nếu cần)
```

- Tool research thu thập items trước.
- `dedupe` chỉ xử lý items đã có, không dùng thay search.
- `compare_sources` cần claims đã được cấu trúc; tool chỉ chỉ ra agreement hoặc
  conflict, không quyết định nguồn nào đúng.
- `citation_audit` kiểm tra cấu trúc citation, không mở URL và không chứng minh
  citation thực sự hỗ trợ claim.
- `format` phù hợp digest/thread; `export_report` phù hợp báo cáo cuối cùng cần
  Markdown hoặc JSON.
- `send` là external action. Agent phải gọi
  `clarify(response_type="yes_no")` trước và chỉ gửi sau khi người dùng xác nhận
  chính xác nội dung và đích đến.

## Ba tool phân tích/xuất báo cáo

### `compare_sources`

Interface:

```python
compare_sources(items: list[dict] | None = None) -> dict
```

Mỗi item nên có `source`, `url` và `claims`. `claims` là object ánh xạ tên claim
sang giá trị mà nguồn đó công bố.

```python
from tools import TOOL_FUNCTIONS

result = TOOL_FUNCTIONS["compare_sources"]([
    {
        "source": "Source A",
        "url": "https://a.example/report",
        "claims": {"Launch date": "June 1", "Price": 20},
    },
    {
        "source": "Source B",
        "url": "https://b.example/report",
        "claims": {"Launch date": "June 2", "Price": 20},
    },
])
```

Kết quả có `comparisons`, `conflicts`, `conflict_count`,
`agreement_count` và `skipped_item_count`. Một claim chỉ được đánh dấu
`agreement`/`conflict` khi xuất hiện ở ít nhất hai source item khác nhau.

### `citation_audit`

Interface:

```python
citation_audit(claims: list[dict] | None = None) -> dict
```

```python
result = TOOL_FUNCTIONS["citation_audit"]([
    {
        "text": "The product launched in June.",
        "url": "https://example.com/announcement",
        "source": "Example",
    }
])
```

Một claim hợp lệ khi có:

- `text` không rỗng;
- URL dùng `http` hoặc `https` và có hostname hợp lệ;
- `source` không rỗng.

Kết quả trả `audited_claims`, các issue code như `missing_url`,
`invalid_url`, `missing_source`, cùng `coverage_percent`.

### `export_report`

Interface:

```python
export_report(
    title: str = "",
    items: list[dict] | None = None,
    format: str = "markdown",
) -> dict
```

```python
result = TOOL_FUNCTIONS["export_report"](
    title="Daily AI Research",
    items=[
        {
            "section": "Research",
            "title": "New evaluation paper",
            "summary": "A short summary.",
            "source": "arXiv",
            "url": "https://arxiv.org/abs/...",
        }
    ],
    format="markdown",  # hoặc "json"
)
```

Tool trả nội dung qua `content`, kèm `content_type` và `item_count`. Nó không tự
ghi file; caller quyết định hiển thị, lưu hoặc gửi nội dung sau đó.

## Tool folder contract

Mỗi tool nằm trong một thư mục riêng:

```text
tools/<tool_name>/
  TOOL.md   # frontmatter + tài liệu cho người duy trì
  tool.py   # implementation độc lập
```

`tools/__init__.py` là registry chuẩn. `agent.py`, `chat.py`, `app.py` và
`run_eval.py` dùng `TOOL_FUNCTIONS` từ registry này. Product guardrail cũng tra
cứu registry chuẩn, vì vậy không duy trì thêm whitelist tool riêng.

Mỗi `TOOL.md` dùng cùng frontmatter:

```yaml
---
name: tool_name
track: core | bonus
kind: live_api | local_formatter | local_knowledge | action | control
provider: Provider name if any
requires_env: [ENV_VAR]
inputs: [arg_name]
outputs: [field_name]
side_effect: false | true | local_file_write
requires_confirmation: true   # chỉ dùng cho write/action tool
---
```

Khi thêm tool mới, cần hoàn thành đủ:

1. `tools/<tool_name>/tool.py`;
2. `tools/<tool_name>/TOOL.md`;
3. import và entry trong `TOOL_FUNCTIONS`;
4. declaration trong `artifacts/tools.yaml`;
5. routing rule trong `artifacts/system_prompt.md` nếu model cần gọi tool;
6. unit test qua public interface.

## Kiểm thử

Từ thư mục `starter_v0`:

```powershell
.\.venv\Scripts\python.exe -m unittest `
  tests.test_compare_sources `
  tests.test_citation_audit `
  tests.test_export_report `
  tests.test_new_tools_registry -v

.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts\validate_submission.py
```

`track: bonus` chỉ có nghĩa tool là optional/extension. Declaration của bonus
tool vẫn được gửi cho model và có thể ảnh hưởng routing core, nên mọi mô tả phải
nêu rõ tool được dùng ở bước nào và khi nào không được gọi.
