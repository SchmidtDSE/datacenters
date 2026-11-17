---
title: Scoring review for the Data Center Explorer
date: 2026-11-17
geometry: margin=2.2cm
fontsize: 10pt
mainfont: DejaVu Sans
---

# Purpose

The explorer scores every data center on five pillars, and every page says that the variables and weights have not been reviewed. This note sets out what each variable contributes, so that the review can decide what to keep, merge, drop or reweight. Every number below comes from `analysis.py`, which reads the explorer's precomputed results; `make` rebuilds this note.

The figures use the default setting: FracTracker, all statuses, a {{radius}} mile radius, {{n_facilities}} facilities and {{n_variables}} variables. The other sources are summarised at the end.

# Variables

Each variable is ranked as a mid-rank percentile among the facilities in view, and a pillar score is the mean of its variables' percentiles. A variable helps only when it separates facilities. Two things stop it doing so: missing values, which leave a facility out of that variable's ranking, and ties, which give every tied facility the same percentile. The last column gives the share of facilities that share the most common value.

{{table:variables}}

# Weak variables

{{n_weak}} variables have values for fewer than half the facilities or tie for at least half of them.

{{table:weak}}

Cooling energy demand and cooling water consumption exist only for PNNL projected sites, so they are blank for the other sources and do no harm there. Critical habitat, proposed critical habitat, the river distance and the distance to tribal land are mostly ties because few facilities have any within {{radius}} miles; they still mark the facilities that do. Redlining and dedicated fossil power already have weight 0. Power capacity is reported for {{power_coverage}} of FracTracker records, and the facilities that report it are ranked against each other alone.

# Overlap between variables

{{n_pairs}} pairs of variables have a Spearman correlation of 0.6 or more in magnitude, {{n_pairs_cross}} of them across pillars. Correlations are computed with each variable's direction applied, so a positive value means two variables push a facility's score the same way, and a negative value means they pull it in opposite directions.

{{table:pairs}}

![Spearman correlation between variables, direction applied, grouped by pillar.](build/correlations.png){width=90%}

Three of these matter for the review.

1. The critical habitat share of the radius and the distance to final critical habitat carry the same information (ρ = {{rho_crit}}). One of them should go; the share belongs in biodiversity and the distance in the regulatory screen.
2. Landscape intactness and residents within the radius pull in opposite directions (ρ = {{rho_intact}}). A rural site scores high on biodiversity and low on justice, an urban site the reverse, and much of each cancels in the overall score. This is a real trade-off rather than an error, but the overall score hides it, so the review should decide whether the overall score is shown at all or only the pillars.
3. Floor area and power capacity both measure size (ρ = {{rho_size}}), so size counts twice in the climate pillar. Median income, poverty and the social vulnerability index overlap within justice, as the index already includes income and poverty.

# Pillars

The pillar scores are only weakly related to each other, so each adds its own information.

{{table:pillars}}

The regulatory screen starts with weight 0 because its wetlands, floodplains and critical habitat also feed the water and biodiversity pillars. Giving it weight 1 changes the overall ranking modestly (rank correlation {{rho_overall_regulatory}} with the default) but replaces {{top100_overlap_complement}} of the 100 highest-scoring facilities.

Pillars at weight 0: {{pillar_weight_zero}}. Variables at weight 0: {{variable_weight_zero}}.

# Other sources

The same checks on the other sources at the same radius:

{{table:sources}}

PNNL projected sites tie on more variables because the model gives every site the same 36 MW, and many sites share a county and a subbasin.

# Decisions for the review

1. Drop the critical habitat share from biodiversity, or the distance from the regulatory screen.
2. Merge floor area and power capacity into one size variable, or keep power capacity alone.
3. Keep the social vulnerability index and drop income and poverty from the justice score, or keep all three and accept that economic status counts more than once.
4. Decide whether the leaderboard shows an overall score, given that justice and biodiversity pull against each other.
5. Keep the regulatory screen at weight 0, or count it once the duplicated variables are removed.
6. Add EPA eGRID grid emissions and WRI Aqueduct water stress, the largest gaps in the climate and water pillars.
