---
name: send
track: bonus
kind: action
provider: Telegram Bot API
requires_env: [TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]
inputs: [text, confirmed]
outputs: [status, error, message, message_id]
side_effect: true
requires_confirmation: true
---
# send

Posts plain text to the Telegram destination configured by
`TELEGRAM_CHAT_ID`.

This is an external side-effect tool, not a research or formatting tool. The
agent must first call `clarify(response_type="yes_no")` with the exact message
and destination. It may call `send` with `confirmed=true` only after the user
explicitly confirms in the current conversation.

When `confirmed` is false, credentials are missing, the text is empty, or
Telegram rejects the request, no successful send is reported. Error results do
not include the bot token.
