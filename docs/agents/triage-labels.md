# Triage labels

Engineering skills use five generic triage roles. Map them to the labels already configured in this repository as follows.

| Generic role | Repository label | Repository convention |
| --- | --- | --- |
| `needs-triage` | `status:triage` | Vishwa must evaluate and prioritize the issue. |
| `needs-info` | `status:triage` | Keep in triage and leave a comment naming the missing evidence or decision. |
| `ready-for-agent` | `status:assigned` | Add the appropriate `agent:*` label before work begins. |
| `ready-for-human` | `help wanted` | Name the required human action in a comment; retain the current lifecycle label. |
| `wontfix` | `wontfix` | Vishwa records the rationale before closure. |

Execution then follows `status:assigned` → `status:in-progress` → `status:in-qa` → `status:in-review` → closed.
