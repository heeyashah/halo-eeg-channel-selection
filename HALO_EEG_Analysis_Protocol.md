# HALO EEG Electrode Optimization — Analysis Protocol

## Decision to be supported

Select the smallest practical EEG recording montage (target: 6–10 channels) that retains useful information for distinguishing cognitive-workload levels, while preserving frontal and posterior coverage and reducing scrub-cap integration complexity.

This analysis is a **preliminary design study**, not hardware validation. It estimates information loss when channels are removed from a dense, laboratory EEG recording. It cannot establish dry-electrode contact quality, motion robustness, donning time, or surgical-simulation performance.

## 1. Assessment of the Chu et al. 26-channel montage

The source paper is:

> Chu H, Cao Y, Jiang J, et al. *Optimized electroencephalogram and functional near-infrared spectroscopy-based mental workload detection method for practical applications.* BioMedical Engineering OnLine. 2022;21:9. DOI: 10.1186/s12938-022-00980-1.

The authors recorded 62 scalp channels during a four-level Multi-Attribute Task Battery (MATB) experiment and ranked channel-band features using recursive feature elimination. Their retained channels, in rank order, were:

`P4, PO6, O1, P6, PO5, P8, PO8, P7, PO7, PO4, P5, P1, O2, CP2, P2, AF3, C1, P3, Pz, C2, PO3, TP8, Oz, CP4, TP7, CP6`

This is evidence that the montage captured information useful for that particular visually demanding MATB protocol. It is not evidence that these are the universally optimal workload electrodes.

Important qualifications:

- The montage is strongly weighted toward parietal, parieto-occipital, and occipital regions. It is well suited to posterior alpha and visually mediated workload effects.
- AF3 is its only clearly anterior channel. Reducing only within this set could remove frontal theta coverage almost entirely.
- The paper's headline accuracy of `76.25 ± 5.21%` was for combined EEG–fNIRS features, not EEG alone. The reported EEG-only mean accuracy was much lower (approximately 52–54%, depending on classifier).
- The authors selected channel-band features within each participant and then summarized their frequency across participants. Their reported train/test procedure was not a participant-independent nested channel-selection evaluation. HALO should use participant-grouped validation to make a stronger generalization claim.
- EEG was acquired with CPz as the online reference and re-referenced to averaged mastoids (M1/M2). A reduced physical system still needs separate reference and ground/bias electrodes unless the acquisition hardware implements another arrangement.

Conclusion: use the paper's montage as a **published comparator and hypothesis source**, not as HALO's default design.

## 2. Primary dataset

Use the public Hinss/COG-BCI MATB-II EEG dataset (NEMAR `nm000343`; Scientific Data DOI `10.1038/s41597-022-01898-y`). The NEMAR release used for the analysis should be pinned by version.

Why it is the primary choice:

- MATB-II is a multitask workload paradigm similar to the source paper's task and more representative of a complex procedural environment than a simple arithmetic task.
- It includes easy, medium, and difficult workload conditions.
- It contains 15 participants measured in two sessions, enabling participant-independent and cross-session checks.
- It contains 62 10–10 EEG channels sampled at 500 Hz, including frontal, central, parietal, and occipital coverage.
- It is distributed as raw BIDS-compatible data, so channel reduction can be evaluated consistently from the same underlying recordings.

Dataset limitations:

- The current public subset has 15 participants and two sessions rather than the full 29-participant, three-session COG-BCI study.
- It is a laboratory MATB task, not surgical simulation.
- The montage contains 24 of the Chu et al. electrodes. `PO5` and `PO6` are absent, so the exact published 26-channel montage cannot be tested. Do not silently replace them; report a 24-channel overlap comparator separately.
- The acquisition reference was Fpz. Analysis re-referencing does not prove that an equivalent reduced physical reference arrangement will perform identically.

STEW can be used as a secondary sensitivity dataset, but it should not be the primary dataset: its 14-channel consumer montage cannot test the dense 26-channel comparator or broad spatial alternatives.

## 3. Questions and comparisons

The analysis will answer four separate questions:

1. How well does the 24-channel overlap with the published Chu montage perform on an independent MATB dataset?
2. What 16-, 10-, 8-, and 6-channel sets are selected when all available Hinss channels are eligible?
3. How much participant-independent balanced accuracy is lost at each channel count relative to the 62-channel dataset baseline?
4. Which montage lies on the best information-versus-complexity trade-off frontier?

The following configurations must remain distinct in all tables and figures:

- `Full-62`: dataset baseline, not a proposed product configuration.
- `Chu-overlap-24`: published montage comparator with PO5/PO6 unavailable.
- `HALO-current-16`: the team's actual proposed 16-channel montage. Electrode labels are still required.
- `Selected-16`, `Selected-10`, `Selected-8`, `Selected-6`: data-driven configurations selected within training data.
- `Prior-balanced-*`: literature-motivated frontal–posterior configurations registered before viewing test-fold results.

## 4. Minimal signal representation

Preprocessing is deliberately limited because a separate team member owns the final signal-processing design. Apply one fixed pipeline to every channel configuration so that channel count is the variable under study:

1. Keep EEG channels and verify channel names/locations.
2. Apply the team's agreed bad-channel and artifact policy without using workload labels.
3. Re-reference consistently (primary analysis: common average on the dense recording before virtual channel removal; sensitivity analysis: reference schemes feasible on reduced hardware).
4. Band-pass to a range that preserves theta, alpha, and beta (for example 1–40 Hz).
5. Divide each workload block into non-overlapping 4-second epochs.
6. Compute Welch power for theta (4–8 Hz), alpha (8–13 Hz), and beta (13–30 Hz).
7. Use log relative band power per channel as the primary features. Absolute log power and theta/alpha ratio may be sensitivity features.

Non-overlapping epochs reduce dependence between samples. Epochs from the same participant must never be split between training and test partitions.

## 5. Validation design

### Primary evaluation

Use nested, participant-grouped cross-validation:

- Outer loop: five participant-grouped folds. Each test fold contains participants never used for fitting, scaling, hyperparameter selection, or channel selection.
- Inner loop: grouped folds using only the outer-training participants.
- Primary metric: macro balanced accuracy for the three workload levels.
- Secondary metrics: macro F1, confusion matrix, and per-class recall.
- Uncertainty: distribution across outer folds plus participant-level bootstrap confidence intervals where practical.

A session-transfer sensitivity analysis should train on one session and test on the other. It answers a different question from participant-independent generalization and must be reported separately.

### Leakage controls

- Fit scaling parameters on training folds only.
- Perform mutual information, permutation importance, and channel selection on training folds only.
- Group all epochs by participant in the outer evaluation.
- Never select a final montage using the held-out outer-test scores.
- After unbiased evaluation is complete, refit selection on the full dataset solely to propose the final engineering montage. Label that montage as a design recommendation, not an independently tested final model.

## 6. Channel-selection sequence

Use a staged method so the computation remains manageable and the result accounts for feature interactions.

### Stage A — Training-only screening

Within each outer-training fold:

- calculate mutual information between each channel's feature block and workload label;
- calculate channel-block permutation importance using a simple regularized classifier;
- aggregate ranks rather than raw importance values;
- retain a broad candidate pool (for example 26–32 channels), subject to coverage constraints.

Coverage constraints prevent a purely predictive search from collapsing into one posterior cluster. At minimum, retain candidates from:

- anterior/frontal;
- frontocentral/central;
- parietal/centroparietal;
- parieto-occipital/occipital;
- left, midline, and right positions where possible.

### Stage B — Sequential backward selection

Starting from the screened candidate pool, remove one channel at a time. At each step, choose the removal that maximizes inner grouped-CV balanced accuracy, subject to the coverage constraints. Save configurations at 16, 10, 8, and 6 channels.

For channel \(i\), also report leave-one-channel-out importance at relevant baselines:

\[
\Delta A_i = A_{\mathrm{baseline}} - A_{\mathrm{baseline}\setminus i}
\]

This score is descriptive. It is not the sole selection rule because correlated channels and interactions make one-at-a-time ablation path-dependent.

### Stability

For every channel, report how often it is selected across outer folds at each target count. A defensible recommendation should consider both mean performance and selection stability.

## 7. Redundancy analysis

Compute redundancy using training data and aggregate within participant before pooling so participants with more accepted epochs do not dominate.

- Spearman correlation between channel-specific theta features.
- Spearman correlation between channel-specific alpha features.
- Optional normalized mutual information between discretized channel features.
- Hierarchical clustering of channels using `1 - |correlation|`.

High correlation does not by itself justify removal. Prefer removing a channel when it is redundant, has low unique predictive contribution, and is less practical to integrate.

## 8. Engineering feasibility score

Do not convert electrode count directly into an unsupported dollar estimate. Until supplier and mechanical data are available, use transparent component scores:

- number of recording channels;
- total physical electrodes, including reference and ground/bias;
- estimated amplifier/input count;
- number of hair-bearing electrode sites;
- estimated wire-routing burden;
- bilateral and anterior/posterior coverage;
- observed workload balanced accuracy;
- worst-participant or lower-confidence-bound performance;
- selection stability.

Any combined complexity score must publish its weights and include a sensitivity analysis. The primary result should be a Pareto plot, because no single weighting is objectively correct.

## 9. Planned figures and tables

1. Scalp map of all available electrodes, the Chu-overlap comparator, and retained 16/10/8/6 sets.
2. Channel importance with outer-fold variability and selection frequency.
3. Theta and alpha redundancy heatmaps with clustered channel order.
4. Participant-independent balanced accuracy versus channel count, with fold/participant uncertainty and a chance level of 1/3.
5. Pareto plot of balanced accuracy (or its lower confidence bound) versus a transparent integration-complexity proxy.
6. Table listing each candidate montage, recording-channel count, added reference/ground electrodes, regional coverage, performance, and limitations.

## 10. Decision rule

Recommend the smallest montage that satisfies all of the following:

- its mean balanced accuracy is within a predeclared non-inferiority margin of the 16-channel comparator (provisional margin: 3 percentage points, to be agreed before examining final test results);
- its lower confidence bound does not show a practically unacceptable loss;
- it retains at least one frontal/frontocentral theta-sensitive site and at least two posterior alpha-sensitive sites;
- it is stable across outer folds rather than depending on one participant split;
- it is mechanically feasible after reference and ground/bias electrodes are counted.

If 6 and 8 channels do not meet these conditions, the correct conclusion is that 10 channels are the minimum supported by this dataset. The target range is not a requirement to force a smaller montage.

## 11. Inputs still needed from the HALO team

- Exact electrode labels in HALO's current 16-channel proposal.
- Intended amplifier/reference/ground or bias architecture.
- Electrode technology (wet, semi-dry, dry, comb, or other) and which sites are expected to be hair constrained.
- A preliminary per-channel hardware cost or, at minimum, component-count assumptions.
- Agreement on the non-inferiority margin and whether three-level or binary workload discrimination is the primary design outcome.

These inputs are not required to begin the public-dataset analysis, but they are required for the final engineering recommendation.

