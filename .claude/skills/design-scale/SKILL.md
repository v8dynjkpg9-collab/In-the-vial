---
name: design-scale
description: Measure design-system discipline on the In The Vial site — how many distinct font sizes, letter-spacings, line-heights, spacing values and radii exist, and which are near-duplicates. Use when the site looks unpolished but nothing is visibly broken, or before/after a styling change.
---

# design-scale

"Looks alright but not quite sophisticated" is usually not a taste problem. It is **scale sprawl**:
too many near-identical values. A viewer registers 13px next to 14px, or `.12em` next to `.13em`,
as sloppiness without being able to name it. This makes that measurable so it can be tracked
rather than argued about.

## Run it

```bash
python3 .claude/skills/design-scale/audit_scale.py index.html
```

Flags: `--json` for machine-readable output, `--strict` to exit 1 when any category is over budget
(useful in a pre-commit check).

## Reading the output

Each category reports distinct values against a deliberately generous budget. The important line is
**near-duplicates** — pairs within 12% of each other, above an 8px floor. Those are the ones doing
visible damage. The floor matters: 1px vs 2px is a hairline versus a border and obviously
deliberate, so flagging it would bury the real signal.

`grid discipline` is the share of spacing values landing on a 4px grid. Higher is tidier.

## Baseline (2026-08-05)

| Category | Distinct | Budget |
|---|---|---|
| font-size | 25 | 10 |
| letter-spacing | 17 | 8 |
| line-height | 11 | 6 |
| spacing | 34 | 14 |
| border-radius | 5 | 4 |

Spacing on a 4px grid: **40%**. Every category is over budget, which is the measurable reason the
site reads as slightly less polished than its concept and palette deserve.

## Fixing sprawl

Consolidate near-duplicates onto one scale — this is the highest-leverage change for perceived
polish and carries no behavioural risk.

Do it **incrementally and verify visually each time**. Collapsing values changes rendered
appearance everywhere the value was used, so a careless sweep can break vertical rhythm in places
you were not looking. Pair it with the [design-critic](../../agents/design-critic.md) agent, which
renders the site at real breakpoints and can confirm nothing regressed.

Anything touching visible English copy also needs its `ES` key updated in the same change — see
[i18n-check](../i18n-check/SKILL.md).
