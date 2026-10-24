# TraceBench

**Catch the failure. Check the fix.**

A dependency-free CLI for checking recorded agent traces before and after a workflow change. It detects repeated non-idempotent operations, delayed handoffs, and missing handoffs, then compares matching scenarios.

## Try it in one minute

Python 3.11+; no installation, API key, model calls, or network required.

```sh
python tracebench.py check examples/baseline.jsonl
python tracebench.py check examples/candidate.jsonl --fail-on-findings
python tracebench.py compare examples/baseline.jsonl examples/candidate.jsonl --html demo.html
```

Open `demo.html` in your browser. The checked-in [demo](demo.html) is generated from the same fixtures. Expand each run to inspect findings. GitHub displays HTML source; download it or open the local file to interact.

The synthetic baseline has three findings across three runs: one unsafe retry, one late handoff, and one missing handoff. The candidate eliminates those configured policy violations. This is an illustrative fixture change, not measured production improvement.

## Why this exists

A payment call times out. Retrying may duplicate the charge; answering confidently may hide the uncertainty. This tool makes those failure paths inspectable without paying for live model runs. Its audience is an engineer reviewing an agent workflow change and deciding which failures should block deployment.

## Trace contract

Each JSONL line represents one run with a unique string `id` and a nonempty `events` array. Events have nonnegative, chronological integer `at_ms` values and a `type`: `tool`, `handoff`, or `answer`.

Tool events require `name`, `operation_id`, explicit boolean `idempotent`, and `status` (`ok`, `timeout`, or `error`). Operation IDs must identify the same logical action across retries. An `answer` is only a timeline marker in this version; its text is not evaluated. Handoff and answer events need no additional fields.

```json
{"id":"demo","events":[{"type":"tool","at_ms":0,"name":"charge","operation_id":"invoice-1","idempotent":false,"status":"timeout"},{"type":"handoff","at_ms":2000}]}
```

## Rules and tradeoffs

| Rule | Trigger | Limitation |
| --- | --- | --- |
| unsafe-retry | A repeated `(tool name, operation_id)` with `idempotent: false` | Trusts supplied metadata; cannot determine real-world side effects |
| late-handoff | First handoff after the first failed tool exceeds the threshold | One handoff policy per run, not per recovery episode |
| missing-handoff | A failed tool has no subsequent handoff | Strict policy: even a successful automatic recovery still requires handoff |

Default handoff threshold is 5,000ms; change it with `--handoff-ms`. These policies suit high-risk workflows; not every lookup failure needs human escalation. Configure the threshold or exclude unsuitable scenarios. Additional recovery policies are planned.

This is **recorded-trace evaluation**, not re-execution of an agent. It does not judge answer correctness, citation grounding, privacy, or whether a human actually took over. No untrusted trace code is executed. HTML reports escape supplied text. Reports can still contain your tool names and IDs: use sanitized traces before sharing them.

## CI gates

```sh
python tracebench.py check traces.jsonl --format json --fail-on-findings
python tracebench.py compare baseline.jsonl candidate.jsonl --fail-on-regression
python -m unittest discover -s tests -v
```

Exit codes: `0` success, `1` configured gate failed, `2` invalid input or file error. Comparison requires identical run IDs and detects newly introduced rule counts per scenario, even when total findings fall. It cannot distinguish different causes within one rule at the same count.

## Next

- Per-workflow policies and explicit recovered-failure events.
- Evidence-grounding checks and labeled evaluation sets.
- Trace adapters for agent frameworks.

Built with AI assistance. Design choices, examples, checks, and limitations are included for inspection. All bundled data is synthetic; no customer or employer data is used.
