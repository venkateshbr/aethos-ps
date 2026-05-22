# Test Fixtures

## Structure
- engagement_letters/ — PDF fixtures for engagement_letter_agent eval
- receipts/ — Image/PDF fixtures for expense_extractor_agent eval
- vendor_invoices/ — PDF fixtures for vendor_invoice_agent eval
- */red_team/ — adversarial inputs for red-team eval cases
- */hitl/ — low-confidence inputs that should route to HITL

## How to populate
1. Obtain real (anonymised) or synthetic documents
2. Name them using the IDs in docs/test/agent_evals/*.yaml
3. Run: uv run pytest tests/evals/ -v (requires ANTHROPIC_API_KEY)

## Synthetic document creation
For now, create .txt placeholder files with the content structure the agent expects.
