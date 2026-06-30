# Atlas Conversation Persistence Production Check

Run: 2026-06-30T09-05-54-744Z
URL: https://aethos.ishirock.tech

| Check | Status | Notes | Screenshot |
| --- | --- | --- | --- |
| login | PASS | Tenant Meridian Demo v2 20260630063630<br>User prod-demo-v2-20260630063630@aethos-qa.dev | docs/qa/atlas-conversation-persistence-2026-06-30T09-05-54-744Z/screenshots/login-copilot.png |
| new-chat-draft-only | FAIL | thread create POSTs before send: 0<br>draft title visible: false | docs/qa/atlas-conversation-persistence-2026-06-30T09-05-54-744Z/screenshots/new-chat-draft-only.png |
| first-prompt-response | FAIL | response chars: 322<br>contains Nexus/business signal: false<br>visible tool cards: 0<br>conversation title shown: true | docs/qa/atlas-conversation-persistence-2026-06-30T09-05-54-744Z/screenshots/first-prompt-final.png |
| same-thread-follow-up | FAIL | response chars: 0<br>follow-up business-valid: false<br>visible tool cards: 0 | docs/qa/atlas-conversation-persistence-2026-06-30T09-05-54-744Z/screenshots/follow-up-final.png |
| reload-history | PASS | first prompt visible after reload: true<br>follow-up visible after reload: true | docs/qa/atlas-conversation-persistence-2026-06-30T09-05-54-744Z/screenshots/reload-history.png |
