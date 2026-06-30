# Atlas Conversation Persistence Production Check

Run: 2026-06-30T09-15-19-767Z
URL: https://aethos.ishirock.tech

| Check | Status | Notes | Screenshot |
| --- | --- | --- | --- |
| login | PASS | Tenant Meridian Demo v2 20260630063630<br>User prod-demo-v2-20260630063630@aethos-qa.dev | docs/qa/atlas-conversation-persistence-2026-06-30T09-15-19-767Z/screenshots/login-copilot.png |
| new-chat-draft-only | PASS | thread create POSTs before send: 0<br>draft title visible: true | docs/qa/atlas-conversation-persistence-2026-06-30T09-15-19-767Z/screenshots/new-chat-draft-only.png |
| first-prompt-response | PASS | response chars: 466<br>contains Nexus/business signal: true<br>visible tool cards: 0<br>conversation title shown: true | docs/qa/atlas-conversation-persistence-2026-06-30T09-15-19-767Z/screenshots/first-prompt-final.png |
| same-thread-follow-up | PASS | response chars: 84<br>follow-up business-valid: true<br>visible tool cards: 0 | docs/qa/atlas-conversation-persistence-2026-06-30T09-15-19-767Z/screenshots/follow-up-final.png |
| reload-history | PASS | first prompt visible after reload: true<br>follow-up visible after reload: true | docs/qa/atlas-conversation-persistence-2026-06-30T09-15-19-767Z/screenshots/reload-history.png |
