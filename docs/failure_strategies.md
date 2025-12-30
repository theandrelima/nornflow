# Failure Handling Strategies

NornFlow provides flexible failure handling strategies that control how the workflow runner responds when tasks fail during execution. These strategies determine whether the workflow should stop when failures are detected, continue with unaffected hosts, or run all tasks before reporting failures.

## Table of Contents
- [Available Strategies](#available-strategies)
  - [skip-failed (Default)](#skip-failed-default)
  - [fail-fast](#fail-fast)
  - [run-all](#run-all)
- [Configuration](#configuration)
- [Behavior Examples](#behavior-examples)
- [Failure Summary](#failure-summary)
- [Understanding Threading Behavior](#understanding-threading-behavior)
- [Best Practices](#best-practices)

## Available Strategies

### `skip-failed` (Default)

When a task fails on a host, NornFlow removes that host from the inventory for subsequent tasks while continuing execution on unaffected hosts. This is Nornir's default behavior and provides the best balance for most automation scenarios.

**Behavior:**
- Failed hosts are automatically removed from subsequent tasks
- Other hosts continue unaffected through the remaining workflow
- Provides partial success across your infrastructure

**Best for:** Most automation scenarios where partial success is acceptable and you want to maximize successful operations across your infrastructure.

### `fail-fast`

When a failure is detected on any host, NornFlow immediately signals all threads to stop execution. This strategy focuses on preventing further changes when any failure is detected.

**Behavior:**
- When a failure is detected, NornFlow adds all hosts to Nornir's `failed_hosts` list
- This effectively signals that no more tasks should run
- 🚨 Already-running threads **will complete** their current task before stopping
- Clear messaging indicates which task triggered the workflow halt

**Best for:** Critical workflows where any failure indicates an issue that should prevent further changes to maintain system consistency.

### `run-all`

The workflow runs all tasks on all hosts regardless of failures. Each task is attempted on every host, even if previous tasks failed on that host. Errors are collected and reported at the end.

**Behavior:**
- Failures are collected but don't affect execution flow
- NornFlow clears Nornir's `failed_hosts` list before each task execution
- At completion, a detailed failure summary is provided

**Best for:** Diagnostic, audit, or reporting workflows where you need comprehensive results from all systems regardless of individual failures.

## Configuration

Failure strategies can be configured at three levels, with the following precedence (highest to lowest):

1. **CLI parameter** (overrides all other settings)
2. **Workflow definition** (overrides global settings)
3. **Global NornFlow settings** (default for all workflows)

> **Note: If no failure strategy is explicitly configured at any of these levels, NornFlow will default to the `skip-failed` strategy.**

### Global Configuration

Set a default failure strategy in your `nornflow.yaml`:

```yaml
# nornflow.yaml
failure_strategy: run-all # Override default "skip-failed" behavior
```

### Workflow-Level Configuration

Specify a failure strategy for a specific workflow:

```yaml
# my_workflow.yaml
workflow:
  name: Critical Infrastructure Update
  description: Update core infrastructure components
  failure_strategy: fail-fast  # Stop on any failure
  tasks:
    - name: backup_config
    - name: apply_critical_update
    - name: verify_update
```

### CLI Override

Override the failure strategy at runtime:

```bash
# Using hyphens (recommended)
nornflow run my_workflow.yaml --failure-strategy fail-fast

# Using underscores (also supported)
nornflow run my_workflow.yaml --failure-strategy fail_fast
```

NornFlow supports both hyphen and underscore formats for failure strategy names, automatically normalizing them internally.

## Behavior Examples

### Example 1: `skip-failed` Strategy (Default)

```yaml
workflow:
  name: Configuration Deployment
  # No failure_strategy specified, defaults to "skip-failed"
  tasks:
    - name: gather_facts
    - name: deploy_config
    - name: verify_deployment
```

**Execution flow:**
1. `gather_facts` runs on hosts A, B, C
2. `deploy_config` fails on host A but succeeds on B and C
3. `verify_deployment` runs only on hosts B and C (A is skipped)
4. Summary shows host A failed at `deploy_config`
5. Workflow completes with partial success

### Example 2: `fail-fast` Strategy

```yaml
workflow:
  name: Database Schema Migration
  failure_strategy: fail-fast
  tasks:
    - name: verify_prerequisites
    - name: backup_database
    - name: apply_migration
    - name: verify_migration
```

**Execution flow:**
1. `verify_prerequisites` runs on all database nodes
2. `backup_database` starts on all nodes
3. If backup fails on any node, workflow signals halt
4. Already-running backup tasks complete their execution
5. `apply_migration` and `verify_migration` do not run at all
6. Clear message indicates workflow halted due to failure
7. Workflow exits with error status

### Example 3: `run-all` Strategy

```yaml
workflow:
  name: Security Compliance Audit
  failure_strategy: run-all
  tasks:
    - name: check_user_accounts
    - name: verify_permissions
    - name: scan_open_ports
    - name: check_patch_level
    - name: generate_report
```

**Execution flow:**
1. All tasks run on all systems, even if earlier tasks failed
2. Failures in `check_user_accounts` don't prevent `verify_permissions` from running on the same host
3. Each system gets fully audited regardless of individual check failures
4. Comprehensive failure report generated at the end
5. Exit with error if any checks failed

## Failure Summary

At workflow completion, if any failures occurred, NornFlow provides a detailed failure summary:

```
━━━ FAILURE SUMMARY ━━━

Task                Host         Error
------------------  -----------  -----------------------------------------
deploy_config       router-01    Configuration syntax error on line 42
verify_deployment   switch-03    Unable to connect: timeout after 30s
```

This summary helps quickly identify which operations need attention. It includes:

- Tasks that failed
- Hosts where failures occurred
- Error messages for each failure

## Understanding Threading Behavior

When working with failure strategies, it's important to understand NornFlow's threading model:

- NornFlow uses Nornir's threading model where tasks run in parallel across hosts
- Each host/task combination typically runs in its own thread
- When a `fail-fast` strategy signals to stop, already-running threads will complete their current task
- The `run-all` strategy forces all tasks to run on all hosts by clearing the failed_hosts collection before each task
- The `skip-failed` strategy lets Nornir's default behavior handle removing failed hosts from subsequent tasks

This threading model explains why, even with `fail-fast`, some tasks might complete after a failure is detected. Only new tasks are prevented from starting.

## Best Practices

1. **Use `skip-failed` (default)** for most automation tasks where partial success is valuable
2. **Use `fail-fast`** for more strict changes where consistency must be maximized. Again, *bear in mind that NornFlow won't be able to stop ongoing threads, so some changes might still happen by the time the workflow halts completely.*
3. **Use `run-all`** for audits, reports, and diagnostics where you need complete information
4. **Always test** your failure strategy choice in a non-production environment first
5. **Monitor the output** - NornFlow provides clear messaging about what's happening during execution

---
<div align="center">

## Navigation

<table width="100%" border="0" style="border-collapse: collapse;">
<tr>
<td width="33%" align="left" style="border: none;">
<a href="./blueprints_guide.md">← Previous: Blueprints Guide</a>
</td>
<td width="33%" align="center" style="border: none;">
</td>
<td width="33%" align="right" style="border: none;">
<a href="./variables_basics.md">Next: Variables Basics →</a>
</td>
</tr>
</table>

</div>
