# Issue tracker: GitHub

Issues and PRDs for this repository live in GitHub Issues at `venkateshbr/aethos-ps`. Use the `gh` CLI from the repository root so it infers the canonical remote.

## Conventions

- Create an issue with `gh issue create --title "..." --body-file -` and a heredoc for multiline Markdown.
- Read the issue and discussion with `gh issue view <number> --comments`.
- List work with `gh issue list --state open` and the applicable `status:*`, `agent:*`, `area:*`, and `priority:*` filters.
- Comment with `gh issue comment <number> --body-file -`.
- Move work through the lifecycle with `gh issue edit <number> --add-label ... --remove-label ...`.
- Only Vishwa closes issues, after the QA and review gates in `docs/team/SDLC_PROTOCOL.md` are satisfied.

When a skill says to publish a finding, plan, PRD, or implementation ticket, create or update a GitHub issue and link its parent when one exists.
