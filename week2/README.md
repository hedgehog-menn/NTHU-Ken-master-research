Concrete next steps, ordered by what gives you the most leverage soonest.

## Step 1 — Verify the register hypothesis (1–2 days)

Before anything else, **confirm the L-structural / register link is real**, not coincidence. The whole sharpened story depends on it.

Quick experiment: compute correlation between L-structural feature values and presence of politeness markers (`ค่ะ`, `ครับ`, `ผม`, `ดิฉัน`) per user in the same Pantip dataset. If `length_mean` or `punctuation_mean` correlates with politeness-marker count, the bridge holds. If not, you walk back the claim and the L-structural finding stays as-is (still valid, just less unified with 5/12).

This is one notebook cell, maybe 30 lines. Do this first — it costs almost nothing and either strengthens or saves you from a wrong claim.

## Step 2 — Within-coordination per-feature drop (2–3 days)

This is the Stage 3 follow-up already promised in the report. The goal: isolate which specific features inside L-coordination poison the tree/margin classifiers.

The coordination family has 22 features grouped as:
- Coordination dim aggregates (4)
- Algorithmic dim aggregates (4)
- Composite scores (4)
- Engagement (7)
- Temporal (3)

Run leave-one-subgroup-out within L-coordination, on Exp 3, for DT/SVM/RF. Five configs × three classifiers = 15 runs. Look for the subgroup whose removal recovers F1.

Hypothesis to test: the **temporal** subgroup (`delta_mean_s`, `delta_std_s`, `delta_min_s`) is doing most of the damage. Posting-interval features have huge dynamic range and skewed distributions, which is exactly what creates spurious tree splits on small data.

If confirmed: your contribution sharpens from "the coordination family is harmful" to "**three temporal features** are responsible for the tree/margin collapse, and removing them stabilizes the whole pipeline." That's a much tighter, more defensible claim.

## Step 3 — Send your advisor the report (immediately, in parallel)

Don't wait for Steps 1–2 to finish. Send the structured report now with a short note:

> Two follow-ups in progress: (a) verifying the L-structural/register link with the 5/12 finding, (b) isolating which coordination subgroup damages tree/margin classifiers. Expected by [date]. Before going further, I want to confirm the contribution framing is acceptable: "behavioral-feature sockpuppet detection on Pantip should be configured at the (family × classifier) level, with the previously-reported tree/margin failures explained by feature-space pathology in the coordination family." Does this clear the bar for a master's thesis chapter?

This is the single highest-leverage thing you can do this week. The 1–2 week writing path only works if your advisor confirms the framing before you write. If they push back, you learn it now instead of after Day 5 of writing.

## Step 4 — Start drafting Ch 5 (parallel with Step 2)

You have enough material to start writing the methodology and results sections of the family-contribution chapter while Step 2 runs. Don't wait for "everything to be done" — Step 2's outcome only adds one subsection.

Suggested structure:
- 5.1 Motivation (the baseline puzzle from Phase III)
- 5.2 Method (family partition, configurations, classifiers)
- 5.3 Central finding (family-classifier interaction table)
- 5.4 Best per-classifier configurations
- 5.5 Connection to register/politeness (Step 1 result goes here)
- 5.6 Within-family drill-down (Step 2 result goes here)
- 5.7 Discussion

## Step 5 — Decide if you need a comparative baseline (after Steps 1–2)

This is the question your committee may ask: "How does your best (family × classifier) configuration compare to Karin's original full pipeline on the same splits?"

You probably already have Karin's numbers from her thesis. If not, this is a half-day's work: run Karin's original Phase II features through her Phase III classifiers on the same three splits, report side-by-side. This makes the contribution defensible against "but Karin's framework is better" pushback.

## Timeline if you commit today

- **Today**: send advisor email (Step 3)
- **Day 1–2**: register correlation check (Step 1)
- **Day 3–5**: within-coordination drop (Step 2)
- **Day 3 onward, in parallel**: Ch 5 draft (Step 4)
- **Day 6–7**: comparative baseline if needed (Step 5)
- **Week 2**: Ch 4 (baseline framing) + Ch 6 (discussion), revision

The single most important action: **Step 3, today**. Everything else is execution.


---
## SUMMARY RESULT

The verdict is clean. SVM-primary rescue. The auto-decision is right this time — but the heatmap shows one detail worth catching that the rescue-fraction logic missed.

## The clean per-classifier reading

| Classifier | Pattern | Mechanism |
|---|---|---|
| **NB** | Flat across full / drop_temp / full_logtmp (~0.65–0.71). Collapses only on drop_coord_all. | Needs the engagement features. Temporal features are irrelevant to it. |
| **RF** | Flat at ~0.20–0.30 except drop_coord_all (~0.65). | Tree-based, not scale-sensitive. Damage comes from correlated coord features collectively, not temporal scale. |
| **SVM** | Full=0.14–0.34 → full_logtmp=**0.65–0.76** → matches/beats drop_coord_all. | Heavy-tailed temporal features destabilize linear margin. Scale fix is sufficient. |
| **DNN** | Full=0.59–0.73, log neutral, all configs similar. | Already handles scale via internal StandardScaler. Temporal features don't help or hurt. |
| **DT** | Full=0.15–0.24 → drop_coord_all=0.64–0.68 only. | Same as RF — needs full removal. |

## The thing the verdict text missed

Look at Exp 3 specifically:

- DNN `full_logtmp` = **0.76** — **highest cell in the entire grid** (matches SVM)
- SVM `full_logtmp` = **0.76**
- Both beat `drop_coord_all` by +0.07 to +0.11

The aggregate `log_gain` for DNN is +0.009 because it averages a +0.03 gain on Exp 3 with neutral effects on Exp 1–2. The mean hides the fact that on the hardest split, `full_logtmp` is the best DNN configuration too. The verdict logic is too coarse — it averages over experiments where there's no rescue gap to begin with (DNN-full is already 0.59–0.73, no collapse, no opportunity for log to help).

That said, this is a minor refinement. The headline finding is still:

**`log1p(temporal)` rescues SVM completely, doesn't hurt anything else, and ties for the best overall configuration on the hardest split.**

## Final Ch 5 story (locked)

Three findings, each with concrete evidence:

**Finding 1 (Week 1)**: Detection performance is governed by (family × classifier) interaction, not feature richness. The "all 62 features + tuned classifier" recipe is wrong for this problem.

**Finding 2 (Step 2 + 2C)**: Within the L-coordination family, the three temporal features (`delta_mean_s`, `delta_std_s`, `delta_min_s`) are the specific cause of SVM collapse. Their distributions are extremely heavy-tailed (kurtosis up to 123, max/median ratio up to 10,000). Removing them alone recovers ~90–110% of the rescue from removing the whole coordination family.

**Finding 3 (Step 2B + 2C)**: The temporal signal is *valuable*, not noise. A simple `log1p` transformation of these three features rescues SVM (F1 0.14 → 0.76 on Exp 3) without removing any features. SVM with `full_logtmp` ties for the best F1 across the whole experimental grid. Tree-based methods (DT, RF) are not rescued by `log1p` — their failure is mechanistically different and requires full coordination removal.

## Updated thesis-claim paragraph

> "Behavioral-feature sockpuppet detection on Pantip is bottlenecked by feature-classifier interaction, not feature richness. We isolate the mechanism to three temporal features whose heavy-tailed distributions destabilize linear margin classifiers, and show that a simple `log1p` transformation of these features rescues SVM from F1 ≈ 0.14 to F1 ≈ 0.76 on the hardest split — outperforming both the original full-feature configuration and any feature-removal alternative. Tree-based methods exhibit a distinct, scale-invariant failure mode that the same transformation does not address, supporting a classifier-family-specific intervention strategy: scale-aware preprocessing for margin learners, family-level feature removal for tree learners."

## What to do now

**Stop running experiments.** You have enough — three converging findings, mechanistic explanation, quantitative effect sizes, classifier-family-specific recommendations.

Next step is drafting. Two priorities:

1. **Send your advisor the updated story today.** Three findings, three numbers, one paragraph. If they approve the framing, the rest is execution.
2. **Start Ch 5 draft.** I'd suggest sections: 5.1 motivation (Phase III baseline puzzle), 5.2 method (family partition), 5.3 Finding 1 (interaction), 5.4 Finding 2 (temporal culprit), 5.5 Finding 3 (log1p rescue), 5.6 discussion (classifier-family-specific recommendations).

Want me to draft the advisor message or start the Ch 5 outline?