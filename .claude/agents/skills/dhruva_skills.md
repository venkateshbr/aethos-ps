# Dhruva — Data & Analytics Skills

## Skill: Weekly Agent Quality Review

Run every Monday. Query correction rates, flag degrading agents, deliver SLO health summary.

```sql
-- 1. Correction rate per agent (last 7 days)
SELECT
  al.agent_id,
  count(DISTINCT al.id)                                                          AS total_runs,
  count(DISTINCT ac.id)                                                          AS corrections,
  round(count(DISTINCT ac.id)::numeric / nullif(count(DISTINCT al.id), 0) * 100, 1)
                                                                                  AS correction_rate_pct,
  round(avg(al.confidence)::numeric, 3)                                          AS avg_confidence,
  round(percentile_cont(0.5)  WITHIN GROUP (ORDER BY al.latency_ms))             AS p50_latency_ms,
  round(percentile_cont(0.95) WITHIN GROUP (ORDER BY al.latency_ms))             AS p95_latency_ms
FROM agent_audit_log al
LEFT JOIN agent_corrections ac ON ac.audit_log_id = al.id
WHERE al.created_at > now() - interval '7 days'
  AND al.tenant_id = '<tenant_id>'   -- run per-tenant or remove for cross-tenant
GROUP BY al.agent_id
ORDER BY correction_rate_pct DESC NULLS LAST;

-- 2. HITL queue age (items waiting > 30 min — SLO breach)
SELECT
  agent_id,
  count(*) AS overdue_hitl_items,
  max(created_at) AS oldest_pending
FROM agent_audit_log
WHERE requires_review = true
  AND human_action IS NULL
  AND created_at < now() - interval '30 minutes'
GROUP BY agent_id
ORDER BY overdue_hitl_items DESC;

-- 3. Worker queue depth (SLO: < 50 pending)
SELECT status, count(*) FROM procrastinate_jobs GROUP BY status;
```

**Decision rules:**
- Correction rate > 15% → P3 incident + `type:spike` issue for Karya
- Correction rate 10-15% → flag in weekly report, monitor closely
- P95 latency > 10,000 ms → flag to Sthira for alert tuning
- HITL queue items > 60 min old → flag to Vishwa (SLO breach)

---

## Skill: Prompt Refinement Dataset Curation

When an agent's correction rate is high, export a correction dataset to Langfuse for prompt iteration.

```python
from langfuse import Langfuse

lf = Langfuse(
    public_key=settings.langfuse_public_key,
    secret_key=settings.langfuse_secret_key,
    host=settings.langfuse_host,
)

# Step 1: Pull corrections from DB for the target agent
corrections = supabase.table("agent_corrections") \
    .select("*, agent_audit_log(input_summary, output_summary, prompt)") \
    .eq("agent_id", "gl_classifier_agent") \
    .gte("created_at", "2026-04-01") \
    .order("created_at", desc=True) \
    .limit(100) \
    .execute()

# Step 2: Create or update a Langfuse dataset
dataset = lf.create_dataset(
    name="gl_classifier_corrections_2026_q2",
    description="Human corrections on GL classifier — Q2 2026. Use for prompt iteration."
)

# Step 3: Add each correction as a dataset item
for c in corrections.data:
    lf.create_dataset_item(
        dataset_name=dataset.name,
        input=c["agent_audit_log"]["input_summary"],
        expected_output=c["human_correction"],
        metadata={
            "agent_prediction": c["agent_prediction"],
            "correction_type": c["correction_type"],
            "correction_date": c["created_at"],
        }
    )

print(f"Dataset created: {dataset.name} ({len(corrections.data)} items)")
```

**Next steps after dataset creation:**
1. Share dataset link with Karya for prompt iteration in Langfuse UI
2. Establish baseline: run current prompt against dataset, record accuracy score
3. After prompt change: run new prompt against same dataset, compare scores
4. If improved: Karya updates the agent's `system_prompt` in code and creates a PR

---

## Skill: SLO Health Report Format

Use this template for weekly SLO status delivered as a GitHub issue comment or Vishwa briefing:

```markdown
## Agent Quality & SLO Report — Week of YYYY-MM-DD

### 🔴 Action Required
| Agent | Correction Rate | Trend | Action |
|-------|----------------|-------|--------|
| gl_classifier_agent | 14.2% ▲ | Up 3.1% from last week | type:spike opened #NNN |

### 🟡 Watch List (5-10% correction rate)
| Agent | Correction Rate | Trend |
|-------|----------------|-------|
| ap_invoice_agent | 8.7% → | Stable |

### ✅ Healthy (< 5% correction rate)
duplicate_detector (1.2%), accounting_guardian (0%), reconciliation_agent (3.4%)

### SLO Status
| SLO | Current | Target | Status |
|-----|---------|--------|--------|
| API P99 latency | 1,240 ms | < 2,000 ms | ✅ |
| Agent P95 latency | 6,800 ms | < 8,000 ms | ✅ |
| HITL queue (median) | 18 min | < 30 min | ✅ |
| Agent accuracy (avg) | 92.1% | > 90% | ✅ |

### Langfuse Traces This Week
- Total traces: 1,847
- Total cost: $4.23 (OpenRouter)
- Highest cost agent: ap_invoice_agent ($1.89)
- Agents with zero traces (possible L0 / disabled): budget_generator_agent, workforce_planning_agent
```

---

## Skill: Langfuse Dataset Evaluation Run

After curating a dataset and iterating on a prompt, run an evaluation to measure improvement.

```python
from langfuse import Langfuse
from langfuse.model import CreateScore

lf = Langfuse(...)

# Fetch dataset items
dataset = lf.get_dataset("gl_classifier_corrections_2026_q2")

correct = 0
for item in dataset.items:
    # Run agent against dataset input
    result = await gl_classifier_agent.run(
        item.input["description"],
        deps=AgentDeps(tenant_id="eval-tenant", db=get_service_db(), autonomy_level=1)
    )

    # Score: 1.0 if matches expected output, 0.0 if not
    predicted = result.data.account_code
    expected = item.expected_output.get("account_code")
    score = 1.0 if predicted == expected else 0.0
    correct += score

    lf.create_score(
        trace_id=item.id,
        name="account_code_accuracy",
        value=score,
        data_type="NUMERIC",
        comment=f"predicted={predicted}, expected={expected}"
    )

accuracy = correct / len(dataset.items)
print(f"Dataset accuracy: {accuracy:.1%} ({len(dataset.items)} items)")
# Compare this number to baseline before prompt change
```

---

## Skill: Product Usage Analysis

Identify which features are used, by whom, and how often. Useful for roadmap prioritisation.

```sql
-- Feature usage by module (last 30 days)
-- Proxy: count API calls per endpoint prefix
-- Note: requires request logging to be enabled (currently not implemented)
-- Workaround: use agent_audit_log as a proxy for AI feature usage

SELECT
  agent_id,
  count(*) AS total_runs,
  count(DISTINCT tenant_id) AS tenants_using,
  round(avg(confidence)::numeric, 3) AS avg_confidence,
  round(avg(latency_ms)) AS avg_latency_ms,
  sum(CASE WHEN requires_review THEN 1 ELSE 0 END) AS hitl_required
FROM agent_audit_log
WHERE created_at > now() - interval '30 days'
GROUP BY agent_id
ORDER BY total_runs DESC;

-- Tenants not using any AI agents (may need onboarding)
SELECT DISTINCT t.id, t.name
FROM tenants t
WHERE t.id NOT IN (
  SELECT DISTINCT tenant_id FROM agent_audit_log
  WHERE created_at > now() - interval '30 days'
);
```
