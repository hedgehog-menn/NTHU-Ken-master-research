# Project summary

## The pivot

You started Track A (continuing your existing work: swap Karin's Phase II for Lindsey's 12-D features, run her five classifiers on Karin's Pantip data, F1 ≈ 0.69–0.71 with SVM). You pivoted to **Track B: cross-platform transferability study** — does sockpuppet/amplifier detection transfer across platforms and languages?

## What we built, in order

**1. Feature audit (`feature_audit.xlsx`)** — Catalogued Lindsey's 62 user-level features against Pantip's schema. Result: 22 Yes, 16 Partial, 24 No. Cleanly viable for transfer study.

**2. Recommendation phase** — Decided to use Yes-only as primary, drop engagement features (construct mismatch between TikTok algorithmic likes and Pantip member reactions).

**3. First common features extraction (`06_common_features.ipynb` v1, user-level)** — Hit a wall in the diagnostic: **93.7% of TikTok users posted exactly once.** Lindsey's user-level features are meaningless when most users have one observation. Confirmed against raw Lindsey data (`gpt_label.csv` + `blank.csv`) — not a preprocessing artifact, it's the data shape.

**4. Pivoted to post-level analysis.** Verified labels exist via `labeling.ipynb` (Lindsey's rule-based labeler).

**5. Label disaggregation (`04_relabel_behavioral.ipynb`)** — Found that **56% of Lindsey's positive labels were triggered by Filipino-specific phrases** (`lugaw`, `pinklawan`, etc.) — a confound that would conflate "cross-platform" with "cross-language" failure. Split labels into:
- `amp_prob_full`: 4,498 positives (original)
- `amp_prob_behavioral`: 1,972 positives (Filipino-lexicon triggers demoted)

**6. Patched merge (`05b_patch_behavioral_label.ipynb`)** — Carried both labels through the merge.

**7. Post-level common features (`06_common_features.ipynb` v2)** — 14 language-agnostic features computed by one shared function. Diagnostics showed:
- 9 of 14 features fail distribution-similarity check
- 4 features sign-flip across platforms (length features mean opposite things)
- 5 emoji features show no Pantip discrimination

**8. Zero-shot transfer experiment (`07_zero_shot_transfer.ipynb`)** — Five blocks, five classifiers each.

## The headline finding

| Block | F1 (best classifier) |
|---|---|
| TikTok within-domain (behavioral label) | **0.895** (RF) |
| Pantip within-domain (sockpuppet) | **0.601** (NB) |
| Zero-shot transfer (behavioral) | **0.000** (all classifiers) |
| Zero-shot transfer (full label, ablation) | 0.375 (DT, mostly false positives) |

**Transfer completely collapsed.** Every classifier predicted "not a sockpuppet" for nearly all Pantip posts. The TikTok-trained model learned emoji-density as its dominant signal; Pantip sockpuppets don't use emoji as a signature.

## What this means

The result is not a feature-engineering failure — it's a substantive finding. **TikTok amplifiers and Pantip sockpuppets are behaviorally distinct phenomena:**
- TikTok amplifiers signal through emoji and brevity
- Pantip sockpuppets signal through length and timing
- Length features actively flip direction (amplifiers shorter, sockpuppets longer)

The literature's implicit assumption that "inauthentic behavior" is a unified construct is unsupported under controlled conditions.

## Where you are now

You have everything needed to write a thesis chapter on negative transfer. Open questions:
- Frame as Path 1 (negative-result finding, lock it in with within-platform feature importance comparison) — or
- Pivot to Path 2 (few-shot adaptation, convert to a positive result by characterizing how much target-domain data closes the gap)