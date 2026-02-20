# Deferred Items — Sprint 25: Claude Code Agent Executor

- Persistent session reuse via ClaudeSDKClient for faster sequential SDK calls (blocked by SDK subprocess limitations within Claude Code sessions)
- File operation tracking for additional tool types beyond Write/Edit (e.g., Bash file creation)
