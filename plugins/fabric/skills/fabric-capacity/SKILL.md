---
name: fabric-capacity
description: Diagnose Microsoft Fabric capacity utilization, throttling, carry-forward, and Capacity Metrics app issues. Use when a user asks why a capacity is busy, near its limit, throttled, or what is consuming CUs; route Warehouse and Lakehouse SQL endpoint CU-spike analysis to sqldw-cli.
---

# Fabric Capacity Diagnostics

Use this skill with [fabric-cli](../fabric-cli/SKILL.md) for Fabric CLI and REST API access. Use [sqldw-cli](../sqldw-cli/SKILL.md) for a Warehouse, Lakehouse SQL endpoint, or per-item SQL query/user CU spike. This skill owns capacity-level state, tenant-wide utilization, and the Capacity Metrics app.

## Safety and authorization

- Start with read-only diagnostics. Confirm the user has Fabric or Power BI administrator access before calling an admin API.
- Do not start, pause, resume, scale, or otherwise change a capacity without explicit user approval immediately before the operation. Explain the expected carry-forward, throttling, and cost impact first.
- Do not automatically upgrade `fab`. Report an unavailable or outdated CLI and offer the documented upgrade command only if the user asks to upgrade it.
- Discover the actual CLI syntax with `fab --help` and the relevant subcommand help before using an unfamiliar command. Use `-f` only after explicit approval for the particular non-interactive, state-changing command.

## Capacity Metrics data

The Microsoft Fabric Capacity Metrics semantic model contains live DirectQuery tables (`CU Detail`, `Timepoint CU Detail`, and Metrics By Item tables) plus imported inventory and history tables. Current status needs DirectQuery data; imported tables refresh on their own schedule.

- Read the second newest `CU Detail` time point: the newest point can attribute a background operation at its start and look artificially high.
- Utilization percent is `(Interactive + Background) / (Base capacity units * 30) * 100` for a 30-second point.
- Discover capacity IDs with the documented `fab` capacity listing or Fabric admin API. Prefer IDs when a display name contains `/`.
- Before a capacity-consuming operation, use [capacity-cost.md](../fabric-cli/references/capacity-cost.md) to estimate CU-hours and capacity impact. Obtain explicit consent when the operation is recurring, material, uncertain, or the capacity is already throttling.

## Diagnostic workflow

1. Verify `fab auth status` and administrator access with a small read-only capacity query. Stop and explain a 401 or 403; never bypass permissions.
2. Collect current utilization, carry-forward, SKU, state, and the relevant time window from the Capacity Metrics app.
3. Identify the highest CU consumers. For SQL endpoint or Warehouse correlation, hand off to `sqldw-cli`; for other item types, use the read-only Fabric CLI discovery flow.
4. Explain whether the result is interactive or background consumption, whether smoothing affects the reading, and the likely operational impact.
5. Discuss remediation options before any state change. Include the implications of pausing or resuming a capacity and make no change without explicit confirmation.

## Capacity Metrics app recovery

The app can become stale after credential expiry or broken DirectQuery credentials. Verify the model is fresh and the configured credential belongs to an administrator for every queried capacity. Updating or reinstalling the app, changing credentials, and moving workspaces are state changes: describe the impact and wait for the user's explicit approval.

## References

- [Fabric CLI capacity-cost guidance](../fabric-cli/references/capacity-cost.md)
- [Fabric Warehouse capacity and query correlation](../sqldw-cli/references/operations/capacity-metrics-correlation.md)
- [Microsoft Fabric Capacity Metrics app](https://learn.microsoft.com/en-us/fabric/enterprise/metrics-app)
