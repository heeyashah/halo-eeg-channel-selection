# HALO EEG Electrode Optimization — Initial Results

## Executive conclusion

The initial public-dataset analysis supports an **8-channel frontal–posterior recording montage** as the strongest preliminary design for HALO:

`F3, F4, FCz, P3, P4, O1, O2, Oz`

This configuration preserves bilateral frontal/frontocentral coverage for theta activity and bilateral/midline parietal–occipital coverage for alpha activity. In participant-independent evaluation, it achieved a mean three-class balanced accuracy of **46.4%** (participant-bootstrap 95% CI: **43.5–49.5%**), compared with **45.2%** for a data-selected 16-channel comparator and **47.3%** for all 61 recorded channels.

This result supports feasibility, not final validation. The analysis used laboratory MATB-II recordings, a fixed minimal preprocessing pipeline, and no surgical-motion testing. HALO's actual 16-channel electrode labels and reference/ground architecture are still required before making the final design decision.

## Data and experimental scope

The analysis used the public Hinss/COG-BCI MATB-II dataset (NEMAR `nm000343`, version `v1.0.3`):

- 15 participants;
- two sessions per participant;
- easy, medium, and difficult MATB-II workload conditions;
- 61 recorded EEG channels at 500 Hz;
- 3,330 accepted, non-overlapping 4-second workload epochs after a fixed gross-artifact rule;
- theta (4–8 Hz), alpha (8–13 Hz), and beta (13–30 Hz) log-relative-power features.

Fpz was the acquisition reference and is not present as a recording channel in the distributed signals. A product implementation therefore needs more physical electrodes than the number of recording channels reported below.

## Validation method

The primary analysis used five-fold participant-grouped outer validation. Every held-out fold contained participants absent from model fitting, scaling, mutual-information screening, backward selection, and hyperparameter selection. Four-fold participant-grouped validation was used inside each training fold.

The model was deliberately simple: standardized band-power features and regularized multinomial logistic regression. Balanced accuracy was the primary metric because it weights the three workload levels equally.

Candidate groups were:

- `Full-61`: all distributed recording channels;
- `Chu-overlap-24`: the 24 electrodes shared with the 26-channel montage reported by Chu et al.; PO5 and PO6 were unavailable;
- `Selected-*`: training-fold-only mutual-information screening followed by coverage-constrained sequential backward selection;
- `Prior-balanced-*`: anatomically balanced frontal–posterior configurations declared before final test-fold results were examined.

## Main results

| Configuration | Recording channels | Mean balanced accuracy | Participant-bootstrap 95% CI | Mean macro F1 |
|---|---:|---:|---:|---:|
| Full dense montage | 61 | 47.3% | 45.1–49.5% | 45.9% |
| Chu et al. overlap | 24 | 43.8% | 41.8–45.9% | 41.6% |
| Data-selected | 16 | 45.2% | 43.0–47.4% | 43.8% |
| Balanced prior | 10 | 46.0% | 43.6–48.7% | 43.1% |
| Data-selected | 10 | 44.8% | 42.6–47.1% | 43.1% |
| **Balanced prior** | **8** | **46.4%** | **43.5–49.5%** | **44.9%** |
| Data-selected | 8 | 43.9% | 41.7–46.5% | 42.6% |
| Balanced prior | 6 | 45.3% | 42.9–47.5% | 42.6% |
| Data-selected | 6 | 42.6% | 40.8–44.4% | 41.0% |

Chance balanced accuracy is 33.3% for three equally weighted classes.

### Paired comparison with the 16-channel comparator

The protocol defined a provisional non-inferiority margin of 3 percentage points relative to a 16-channel comparator. Participant-paired mean accuracy differences were:

| Candidate | Difference from selected 16 | Bootstrap 95% CI |
|---|---:|---:|
| Balanced 10 | +0.8 percentage points | −2.6 to +4.2 |
| **Balanced 8** | **+1.2 percentage points** | **−2.3 to +5.0** |
| Balanced 6 | +0.1 percentage points | −2.0 to +2.4 |
| Data-selected 10 | −0.4 percentage points | −2.0 to +1.1 |
| Data-selected 8 | −1.3 percentage points | −3.4 to +0.8 |
| Data-selected 6 | −2.6 percentage points | −4.5 to −0.7 |

The three balanced prior configurations met the provisional 3-point non-inferiority rule against the selected 16-channel comparator. The unconstrained data-selected 6-channel configuration did not.

This comparison is not yet against HALO's actual 16-channel design because its electrode labels have not been supplied.

## Interpretation

### 1. The Chu montage should not be HALO's direct baseline

The Chu-overlap configuration performed 3.6 percentage points below the full montage, with a participant-paired 95% CI of −6.4 to −0.8 points. This does not invalidate the source paper. It shows that a posterior-heavy ranking learned in one MATB experiment did not transfer optimally to a different MATB dataset and participant-independent model.

The source paper also reported its headline 76.25% accuracy for fused EEG–fNIRS features. Its EEG-only accuracy was approximately 52–54%, so that headline should not be used as HALO's EEG-only target.

### 2. Eight channels are the best current engineering compromise

The balanced 8-channel montage had the highest mean balanced accuracy among all reduced configurations and was only 0.9 percentage points below the full 61-channel baseline. Its bootstrap interval overlapped the full baseline. It retains:

- left/right frontal sites: F3, F4;
- a midline frontocentral site: FCz;
- left/right parietal sites: P3, P4;
- left/right occipital sites: O1, O2;
- a midline occipital site: Oz.

This is a more physiologically interpretable layout than the all-data-selected 8-channel set, which was asymmetric and contained several far-anterior/lateral electrodes.

### 3. Six channels remain a credible minimum-feasibility option

The balanced 6-channel montage was:

`Fz, FCz, P3, P4, O1, O2`

Its mean performance was effectively equal to the selected 16-channel comparator, and its paired lower confidence limit remained within the provisional 3-point margin. It removes bilateral frontal sampling and posterior midline redundancy, however. The 6-channel option is therefore best treated as a cost/space fallback to be verified experimentally, not the primary recommendation.

### 4. Purely data-driven selection was unstable

AF7 appeared in all five outer-fold selected configurations, while Fz and P1 appeared in three of five folds at the 6-channel target. Most other electrodes appeared in only one or two folds. The final all-data selected montage was also markedly asymmetric.

This instability may reflect the small participant sample, genuine subject variability, task-specific visual/motor demands, correlated channels, and residual ocular or muscle activity. Because the minimal preprocessing did not include ICA, the high importance of far-anterior sites such as AF7/Fp1/Fp2 must not be interpreted as purely neural. This is one reason to combine quantitative selection with physiological and mechanical constraints.

## Preliminary design recommendation

Use the following design hierarchy for the MDR:

1. **Recommended concept: 8 recording channels** — `F3, F4, FCz, P3, P4, O1, O2, Oz`.
2. **Higher-redundancy option: 10 recording channels** — `AF3, AF4, F3, F4, FCz, P3, P4, POz, O1, O2`.
3. **Minimum-feasibility option: 6 recording channels** — `Fz, FCz, P3, P4, O1, O2`.

The count must be presented as recording channels. The hardware bill and cap layout must add the reference and ground/bias electrodes required by the selected amplifier.

The eight-channel result should be phrased as:

> In a participant-independent analysis of a public MATB-II workload dataset, an anatomically balanced eight-channel frontal–posterior montage retained performance comparable to a 16-channel data-selected comparator while reducing the number of recording channels by 50%. This supports an eight-channel HALO concept for prototype testing, subject to validation of the actual reference arrangement, electrode contact, motion artifacts, and surgical-task transfer.

Do not claim that eight electrodes are proven sufficient for clinical or surgical workload monitoring.

## Required next checks

1. Compare these candidates with HALO's actual 16-channel electrode list.
2. Repeat the analysis using the final preprocessing team's artifact-removal pipeline, especially ocular-artifact handling.
3. Perform a cross-session analysis to quantify repeatability.
4. Add binary low-versus-high workload as a sensitivity analysis if HALO's intended output is a change/alarm indicator rather than three-level classification.
5. Score mechanical access through hair, wire routing, amplifier inputs, reference/ground needs, and per-channel cost.
6. Validate the 8- and 6-channel montages in a small surgical-simulation pilot before freezing the scrub-cap layout.

## Source links

- Chu et al. paper: <https://doi.org/10.1186/s12938-022-00980-1>
- Hinss/COG-BCI data descriptor: <https://doi.org/10.1038/s41597-022-01898-y>
- NEMAR dataset record: <https://www.nemar.org/dataset/nm000343>

