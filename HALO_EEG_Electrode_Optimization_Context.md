# HALO Capstone — EEG Electrode Optimization & Feasibility Analysis

## 1. Project Background

Our biomedical engineering capstone project at the University of Waterloo (BME 461/462) is called **HALO — Sensor-Integrated Surgical Scrub Cap**.

HALO is a wearable scrub cap designed to monitor and characterize the cognitive and physical demands experienced by surgical residents during surgical training tasks.

Currently, surgical training assessments primarily rely on observable technical performance, supervisor evaluation, and post-task questionnaires such as NASA-TLX or SURG-TLX. These assessments provide limited insight into how cognitive workload fluctuates throughout a procedure, especially when trainees perform successfully despite experiencing high mental demands.

HALO aims to address this gap by integrating multiple physiological sensing modalities:

- **EEG (electroencephalography):** Measures electrical brain activity to extract features associated with cognitive workload and mental fatigue, particularly frontal theta and posterior alpha activity.
- **PPG (photoplethysmography):** Measures cardiovascular signals to derive heart rate and pulse-rate variability metrics related to physiological arousal and autonomic responses.
- **IMUs (inertial measurement units):** Measure head and upper-trunk movement to characterize neck posture and ergonomic strain.

The objective is to integrate these measurements into a wearable system that identifies relative changes in physiological demand during surgical training, allowing residents and educators to better understand particularly demanding phases of procedures.

HALO is currently in the concept selection and preliminary engineering analysis stage. The initial intended validation environment is simulated surgical training rather than live patient procedures.

## 2. Current Engineering Design Decision

One major challenge with integrating EEG into a surgical scrub cap is determining how many electrodes are actually necessary.

Traditional EEG systems may use 16, 32, or more recording channels, but large electrode arrays increase:

- Hardware and amplifier costs
- Wiring and mechanical integration complexity
- Setup and electrode placement time
- Potential discomfort during extended wear
- Difficulty maintaining reliable electrode-scalp contact, particularly through hair
- Potential interference with normal surgical preparation and other wearable equipment

Our team is considering a **simplified EEG configuration with approximately 6–10 recording channels**, rather than incorporating a full EEG cap.

This is part of our simplified concept (Concept 1.2) from our initial design walk.

The central engineering question is:

> **Can HALO reduce the number of EEG channels while retaining sufficient neurophysiological information to characterize changes in cognitive workload?**

We want to justify this decision quantitatively, rather than arbitrarily selecting electrodes based on convenience or cost.

## 3. My Specific Responsibility

My responsibility is the **EEG electrode placement, channel selection, and feasibility analysis**, which will contribute to the Engineering Analysis & Methods (Modelling and Simulation) section of our Midterm Design Review (MDR).

The MDR requires:

> Design and analysis methods and tools used or planned, including modelling, simulation, or FEA. State your assumptions, simplifications, and approximations. Present initial results and relate them to future design decisions.

Another team member is responsible for signal preprocessing, including filtering, artifact removal, signal quality assessment, and feature extraction pipelines.

**I do NOT want to primarily focus on signal preprocessing.**

Instead, my responsibilities are:

1. Investigate what different EEG electrode locations measure and their relevance to cognitive workload.
2. Identify which EEG frequency bands and workload-related features are most informative at different scalp regions.
3. Assess redundancy and complementary information between electrode locations.
4. Quantitatively evaluate which electrodes can be removed with minimal information loss.
5. Compare the feasibility of full-channel and reduced-channel EEG configurations.
6. Determine an evidence-based recommendation for approximately 6–10 EEG channels.
7. Produce engineering plots, quantitative results, and analysis that justify the selection.

I am open to using existing EEG datasets, Python simulations, channel-selection algorithms, statistical methods, spatial analysis, and published literature.

The end goal is a defensible engineering design decision, not simply a literature review.

## 4. Relevant EEG Physiology

The main EEG features HALO is interested in are:

### Frontal theta (4–8 Hz)

- Often associated with cognitive control, working memory, and mental effort.
- Frontal theta power frequently increases with increasing cognitive workload.
- Particularly relevant around frontal and frontocentral recording locations.

### Posterior alpha (approximately 8–13 Hz)

- Associated with attention, cortical engagement, and visual information processing.
- Posterior alpha power often decreases during increased task engagement, although its relationship with workload depends on experimental conditions.
- Particularly relevant around parietal, parieto-occipital, and occipital regions.

Other frequency bands such as beta may offer complementary information, but frontal theta and posterior alpha are the initial priorities.

An important consideration is that EEG electrodes do not exclusively measure particular frequency bands. Different scalp locations record mixtures of neural activity, and their usefulness depends on the task, electrode reference, feature extraction, and spatial distribution of the underlying activity.

We want to determine whether a subset of electrodes can preserve the most informative workload-related spatial features.

## 5. New Paper — 26-Channel EEG Configuration

I recently identified a research paper that used **26 EEG recording channels**, with the following electrode locations:

`P4, PO6, O1, P6, PO5, P8, PO8, P7, PO7, PO4, P5, P1, O2, CP2, P2, AF3, C1, P3, Pz, C2, PO3, TP8, Oz, CP4, TP7, CP6`

This is the new electrode configuration I would like to investigate.

The montage is heavily concentrated in posterior scalp regions, including parietal, parieto-occipital, and occipital locations, with some central, centroparietal, and temporoparietal coverage. AF3 is the only explicitly frontal/anterior electrode in this list.

**Important:** I have not yet provided the paper title, its experimental task, its exact EEG reference montage, or its study results. We should not assume the researchers selected these electrodes specifically to optimize cognitive workload classification until the paper's methodology is examined.

I want to use this paper as a starting point for investigating channel reduction.

My initial target is to reduce the configuration from 26 channels toward 16, 10, 8, and potentially 6 channels.

However, I also want to critically examine whether this particular 26-channel configuration is suitable for HALO's cognitive-workload objectives, given its heavy posterior coverage.

We should distinguish between:

- Optimizing a subset of the paper's 26 electrodes.
- Identifying the best possible 6–10 electrodes for HALO overall.

These are not necessarily the same problem.

## 6. Proposed Engineering Analyses

### Analysis A — Anatomical and Functional Electrode Mapping

Map all 26 electrodes onto a standardized EEG scalp layout, using the international 10–20 / 10–10 electrode positioning system.

For each electrode, investigate:

- Anatomical scalp region
- Relevant physiological activity
- Workload-related frequency-domain features
- Evidence from published EEG studies
- Potentially redundant neighboring locations
- Practical feasibility within a wearable scrub cap

**Desired output:**

- A scalp topography diagram showing all 26 electrode locations, categorized or color-coded by their expected relevance to HALO.
- A table summarizing electrode location, expected features, physiological rationale, and preliminary retention/removal priority.

Where possible, distinguish established findings from hypotheses requiring experimental validation.

### Analysis B — Quantitative Electrode Importance

Use real multichannel EEG recordings from an appropriate cognitive-workload dataset.

Evaluate electrode importance using methods such as:

- Leave-one-channel-out ablation
- Sequential backward feature/channel selection
- Mutual information with workload labels
- Permutation importance at the channel level
- Comparison of workload classification performance after channel removal

For example, define electrode contribution using the change in balanced classification accuracy:

\[
\Delta A_i = A_{\mathrm{full}} - A_{\mathrm{without}\ i}
\]

Where:

- \(A_{\mathrm{full}}\) = model performance using all available EEG channels
- \(A_{\mathrm{without}\ i}\) = performance after removing electrode \(i\)
- \(\Delta A_i\) = estimated performance reduction attributable to electrode removal

The selection method should account for redundancy and feature interactions, since a single-electrode ablation score does not necessarily predict what happens when multiple electrodes are removed.

Channel selection, model fitting, and hyperparameter tuning should occur within training folds, with independent participant-level evaluation where possible to avoid data leakage.

**Desired output:**

- Electrode importance ranking or bar chart
- Performance versus number of channels plot
- Recommended 6-, 8-, and 10-channel configurations
- Performance comparison relative to full-channel EEG

We should report uncertainty or variability across held-out participants instead of relying on one accuracy figure.

### Analysis C — Spatial Redundancy and Information Coverage

Investigate whether nearby electrodes provide highly correlated or overlapping information.

Potential methods include:

- Correlation matrices of channel-specific theta and alpha features
- Mutual information between electrode features
- Pairwise redundancy analysis
- Spatial coverage analysis
- Clustering electrodes based on feature similarity

For example:

\[
R_{ij} = \operatorname{corr}(P_{\theta,i}, P_{\theta,j})
\]

Where \(P_{\theta,i}\) is the theta-band power from channel \(i\), measured across defined epochs or experimental conditions.

Correlations should be computed separately for relevant frequency bands where useful.

High correlation can suggest redundancy, but it does not automatically mean an electrode is dispensable. Its unique predictive contribution and physical feasibility also matter.

**Desired output:**

- Electrode correlation heatmap
- Identification of potentially redundant electrode groups
- Evidence explaining why certain channels can be eliminated

### Analysis D — Engineering Trade-Off Evaluation

Evaluate the feasibility of different EEG channel counts for HALO.

Compare configurations based on:

- Preserved workload-related information
- Workload discrimination performance
- Spatial coverage
- Estimated hardware cost
- Required acquisition channels
- Number and location of physical electrodes
- Difficulty of electrode contact through hair
- Wiring complexity
- Integration into the surgical scrub cap
- Potential donning and doffing complexity

Consider the difference between recording channels and physical electrodes: reference and bias/ground electrodes may be required in addition to the recording electrodes.

The ideal configuration should balance sufficient neurophysiological information with practical wearability and implementation constraints.

**Desired output:** A quantitative comparison table or Pareto plot showing the trade-off between EEG information retention and engineering complexity.

## 7. Intended Engineering Plots

I would like to generate actual quantitative figures, including:

1. **Figure 1 — EEG Electrode Location Map.** A scalp diagram identifying all 26 electrodes and potentially highlighting the electrodes retained in the optimized 6–10-channel configuration.
2. **Figure 2 — Electrode Importance Ranking.** A bar chart showing estimated electrode importance for workload discrimination, ideally with uncertainty estimates.
3. **Figure 3 — Electrode Redundancy Heatmap.** A correlation or mutual-information matrix showing overlap between different EEG channels.
4. **Figure 4 — Performance Versus Channel Count.** A plot showing workload classification performance for multiple reduced-channel configurations, such as 26, 16, 10, 8, and 6 channels. This is one of the most important outputs, since it directly informs how many channels HALO should use.
5. **Figure 5 — Engineering Trade-Off / Pareto Analysis.** A comparison of information retention versus electrode count, expected cost, or physical integration complexity.

I want these plots to be generated from defensible data or clearly defined quantitative models. We should not present synthetic illustrative plots as actual empirical findings.

## 8. Important Assumptions and Limitations

The analysis should explicitly address:

1. **Dataset relevance:** EEG datasets collected during laboratory cognitive tasks may not perfectly represent cognitive workload during surgical simulation.
2. **Montage differences:** Not every publicly available EEG dataset contains all 26 electrodes used in the identified paper.
3. **Information versus signal quality:** Offline removal of EEG channels assesses the information retained by a reduced-channel configuration, but does not directly establish actual hardware signal quality.
4. **Reference selection:** Re-referencing and electrode montage can influence comparisons. The impact of changing the physical reference arrangement should be considered.
5. **Volume conduction:** Neighboring scalp electrodes may record overlapping activity originating from the same neural sources.
6. **Subject variability:** Workload-related EEG features may differ substantially across individuals and experimental conditions.
7. **Hardware feasibility:** Electrode-skin impedance, hair coverage, movement artifacts, and mechanical integration cannot be fully validated using an existing EEG dataset.
8. **Reduced spatial information:** A small EEG montage limits spatial analysis and may reduce the effectiveness of methods that depend on many electrodes.

## 9. What I Want You to Help Me Do

Please help me develop and execute a rigorous but manageable engineering analysis that is appropriate for an undergraduate biomedical engineering capstone MDR.

Start by assessing the 26-electrode configuration and explaining what it can reasonably measure for HALO's cognitive workload application.

Then help me:

1. Identify the most suitable dataset or data source for evaluating these electrodes.
2. Determine whether the published paper's 26-channel setup is an appropriate baseline or whether another montage would make more sense.
3. Develop a quantitative electrode-selection methodology.
4. Implement the necessary Python analysis using suitable libraries.
5. Produce meaningful plots and interpretable numerical results.
6. Identify which electrodes should be eliminated first, supported by analysis rather than intuition.
7. Recommend a defensible 6–10-channel EEG configuration for HALO.
8. Translate the results into engineering conclusions suitable for the MDR, including assumptions, simplifications, limitations, and future design implications.

Please prioritize methods that genuinely inform electrode placement and channel count. Avoid spending too much time on generic EEG preprocessing, as another team member is responsible for that.

**The ultimate engineering design question is:**

> How many EEG recording channels, and at which scalp locations, are necessary to retain the workload-related information HALO needs, while minimizing electrode count and improving feasibility for scrub cap integration?

I want to approach this quantitatively, using real research evidence and engineering analysis rather than relying solely on a literature-based electrode ranking.

## 10. Critical Follow-Up for the New Chat

**Provide the actual paper PDF, title, or DOI** for the 26-channel configuration. Its experimental task, montage reference, and electrode-selection rationale matter. If the electrodes were selected for visual attention or posterior alpha rather than general cognitive workload, their suitability for HALO needs to be reconsidered.

Because the listed montage has only one anterior electrode (AF3), explicitly investigate whether reducing that montage could preserve posterior alpha information while sacrificing frontal theta information. This may be an important design consideration before committing to the locations.
