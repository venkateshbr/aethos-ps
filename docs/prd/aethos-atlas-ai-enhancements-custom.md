# Aethos Atlas AI Enhancements - Custom Implementation Plan

Date: 2026-06-26
Status: Planning
Scope: Aethos-native implementation path for Atlas conversation history, document-linked retries, memory, and long-running finance workflows.

Assessment note: this document intentionally evaluates the Aethos-native path independent of any previously documented PydanticAI/Pydantic Graph architecture assumptions.

## Decision Frame

This plan assumes Aethos builds the Atlas conversation, memory, and workflow layer directly inside the existing FastAPI/Supabase product. It does not depend on any specific third-party agent framework.

The goal is to fix the current Atlas weakness first: a user can upload an engagement letter, get an unclear extraction, return to chat, and ask Atlas to retry using the prior document and prior conversation. Today that does not work reliably because visible history, model context, and document linkage are incomplete.

## Current Implementation Reality

Current Atlas already has the beginning of the required system:

- `chat_threads` and `chat_messages` persist conversations.
- `agent_runs`, `agent_tool_invocations`, `agent_workflow_runs`, and `agent_memory_items` exist as agent operating-model tables.
- Atlas streams responses over SSE.
- Agent tool invocations are routed through Aethos policy/HITL patterns for finance actions.
- Document extraction creates Inbox work for engagement letters, vendor bills, expenses, and related workflows.

The gaps are implementation gaps, not missing product concepts:

- The frontend does not load historical threads/messages on page load.
- Selecting a thread clears the message list instead of fetching persisted messages.
- Backend has repository support for listing messages but no message-history route exposed to the UI.
- The model request is rebuilt from the current user message only, so prior turns are not used as context.
- Attachments are not durably linked to chat messages/threads in a way that supports follow-up instructions.
- `agent_memory_items` is not actively used as an agent memory product surface.

## Target Product Behavior

Atlas should behave like an AI finance operations manager:

1. The user can leave and return to a conversation without losing context.
2. Atlas can continue work from a prior upload, prior Inbox task, prior extraction, or prior approval.
3. Atlas can retry extraction using new instructions without overwriting audit evidence.
4. Atlas remembers approved corrections and tenant policies when useful.
5. Atlas never uses memory as a substitute for live finance data.
6. High-risk actions still route through Inbox and existing approval policy.
7. Every material agent action remains traceable through Aethos agent ledgers and domain audit events.

## Architecture

### Module: Conversation Store

Interface:

- Create/list/update chat threads.
- Append immutable messages.
- Fetch messages by thread.
- Maintain thread title, last activity, summary, and archive/deletion state.
- Link messages to source documents, Inbox tasks, suggestions, agent runs, and domain records.

Implementation:

- Extend existing `chat_threads` and `chat_messages`.
- Add a link table when needed instead of overloading text content:
  - `chat_message_documents`
  - `chat_message_tasks`
  - `chat_message_agent_runs`
  - or JSONB metadata if a lighter slice is preferred.

Leverage:

- UI reload, model context reconstruction, audit replay, and support/debugging all cross the same interface.

### Module: Context Builder

Interface:

- Given `tenant_id`, `user_id`, `thread_id`, and current input, return model-ready messages and references.
- Apply tenant scoping, PII masking, token limits, memory retrieval, and document/task summaries.

Implementation:

- Load thread summary plus recent messages.
- Preserve tool-call/tool-result pair integrity.
- Include safe references to linked documents and Inbox tasks.
- Add summary compaction when history exceeds budget.
- Never inject raw unrestricted document text by default.

Leverage:

- Every agent turn becomes history-aware without each tool or frontend caller understanding token windows, summaries, or memory policy.

### Module: Document Retry And Correction

Interface:

- Rerun extraction for a prior document with new user instructions.
- Create a new extraction attempt/version.
- Compare old vs new extracted payload.
- Route material changes to Inbox for review.

Implementation:

- Add extraction attempt versioning if not already sufficient.
- Store correction prompt and source thread/message.
- Supersede prior open Inbox task only through explicit state transition, not deletion.
- Store approved corrections as memory candidates where appropriate.

Leverage:

- Engagement-letter, vendor-bill, receipt, and future document workflows reuse the same correction loop.

### Module: Durable Memory

Interface:

- Promote approved facts/corrections/preferences into tenant-scoped memory.
- Retrieve only memories relevant to the current task.
- Expire or invalidate stale memories.

Implementation:

- Use existing `agent_memory_items` as the first backend.
- Memory types:
  - `tenant_policy`
  - `user_preference`
  - `client_fact`
  - `document_correction`
  - `workflow_state`
  - `extraction_feedback`
- Store provenance: source thread, message, document, Inbox decision, and approving user where available.
- Keep memory structured and reviewable; do not store large transcripts as memory.

Leverage:

- The finance operations manager becomes better over time without letting stale chat history become hidden business truth.

### Module: Workflow Continuity

Interface:

- Start, resume, inspect, and cancel long-running finance workflows.
- Tie workflow state to chat, Inbox, documents, and agent ledger evidence.

Implementation:

- Continue using Aethos workflow tables and Procrastinate for background work.
- Add conversation references to `agent_workflow_runs`.
- Expose workflow status in Atlas responses and Settings run ledger.

Leverage:

- Bill pay, month-end close, statement generation, document extraction, and collections all share one durable workflow model.

## Implementation Plan

### Phase 1 - Restore Visible Conversation History

Changes:

- Add `GET /api/v1/chat/threads/{thread_id}/messages`.
- Add response model for chat messages.
- Load thread list in Atlas on page mount.
- Fetch messages when selecting a thread.
- Keep current thread selected after refresh.
- Update thread title after first meaningful user message or uploaded document.
- Update thread last activity when messages are appended.

Acceptance:

- Refreshing `/app/copilot` shows prior conversations.
- Selecting a prior conversation renders previous user and Atlas messages.
- Cross-tenant users cannot fetch another tenant's messages.

Tests:

- Backend API contract: list messages uses tenant-scoped read path.
- Backend repository test: chronological ordering and limit.
- Frontend E2E: send message, refresh, reopen thread, verify content remains.
- Security test: tenant B cannot read tenant A thread/message.

### Phase 2 - Make Model Runs History-Aware

Changes:

- Add `AtlasContextBuilder`.
- Load recent thread messages before every model call.
- Add compact thread summary field.
- Summarize older conversation once token budget is exceeded.
- Include prior document/task references as structured context.

Acceptance:

- User can say "try that again" or "use the same engagement letter" in the same thread after refresh.
- Atlas answers from prior context without requiring the document id.
- Tool-call/tool-result pairs remain valid after trimming.

Tests:

- Unit test: context builder includes prior user/assistant turns.
- Unit test: PII masking is applied to loaded history before model call.
- Unit test: summarization preserves current document/task references.
- E2E: upload engagement letter, refresh, ask Atlas to retry extraction.

### Phase 3 - Add Document-Linked Retry And Versioned Extraction

Changes:

- Link uploaded documents to chat messages.
- Add "rerun extraction" flow with prompt override.
- Persist extraction attempt versions.
- Create an Inbox review task for changed extraction results.
- Preserve old extraction and old Inbox decision evidence.

Acceptance:

- User can correct "billing arrangement should be mixed, not fixed".
- New extraction attempt shows changed fields and confidence.
- Engagement creation uses reviewed client name, value, billing terms, and source document.

Tests:

- Backend unit: extraction correction creates a new attempt, not overwrite.
- API/E2E: corrected engagement-letter extraction generates updated Inbox payload.
- Audit test: old and new extracted payloads remain inspectable.

### Phase 4 - Activate Curated Memory

Changes:

- Add memory write path from approved corrections and explicit user preferences.
- Add memory retrieval to context builder.
- Add memory list/review UI later under Settings or Admin.
- Add expiry and confidence rules.

Acceptance:

- Approved correction can be recalled in later threads when relevant.
- Memory never crosses tenant boundaries.
- Memory does not override live database facts.

Tests:

- Unit: same-tenant retrieval only.
- Unit: expired memory excluded.
- E2E: approved extraction correction influences later similar extraction prompt.

### Phase 5 - Long-Running Workflow Continuity

Changes:

- Connect workflow runs to threads/messages.
- Show "waiting for Inbox approval" and "workflow completed" statuses in Atlas.
- Let Atlas resume after a long-running worker finishes.

Acceptance:

- User can ask "what happened with the close package?" and Atlas finds the relevant workflow.
- Atlas distinguishes proposed, approved, posted, rejected, and failed states.

Tests:

- E2E: month-end close prompt -> Inbox approval -> return to Atlas -> explain final status.
- Unit: workflow references are tenant-scoped and audit-safe.

## Product Impact

Benefits:

- Fastest path to fixing the current broken user journey.
- Minimal new operational surface.
- Keeps Aethos as the single source of truth for tenant data, audit, approvals, and finance policy.
- Avoids external session/memory stores before governance is fully designed.

Costs:

- Aethos must build its own channel adapters later if Slack/Teams/Telegram become first-class.
- Aethos must build its own session search, handoff, and memory-management UX.
- More custom agent runtime logic accumulates in the backend unless wrapped behind deep modules.

## Open Questions

1. Should `chat_threads.summary` and `last_message_at` be added as first-class columns now?
2. Should document/message links be normalized tables or JSONB on `chat_messages` for the first slice?
3. Should memory writes require human approval initially, or can approved Inbox corrections auto-promote?
4. Should Atlas expose a visible "retry extraction" action, or rely on natural language only?

## Recommended First Issue

Title: Atlas conversation history and document retry foundation

Scope:

- Message history API.
- Frontend history reload.
- Model context builder with recent history.
- Document-message linkage for uploaded files.
- First engagement-letter retry test.

Out of scope:

- External channels.
- Semantic/vector memory.
- Full workflow orchestration replacement.
- New agent framework adoption.
