# What the analysis plan commits to (one page, for Reenu)

*Plain-language summary of [`analysis_plan.md`](analysis_plan.md). Numbers are filled from the pipeline (`python -m src.causal.pregate_report sync-plan`). If this page and the plan disagree, the plan wins.*

**The one question we promise to answer (H1).** Did PM2.5 fall more in NCAP cities than it would have without NCAP?
- **Data:** satellite PM2.5, 2010–2024, averaged over where people live in each city.
- **Sample:** <!--g:n_treated-->113<!--/g--> NCAP urban centres against <!--g:n_controls-->923<!--/g--> non-NCAP centres of 100,000+ people.
- **Method:** synthetic difference-in-differences. It builds each group's "what would have happened" from a weighted mix of control cities that tracked it before 2019.
- **2020:** left out of the headline number (COVID lockdown, BS-VI fuel), but shown separately.

**What counts as "yes".** All four must hold:
1. The estimated effect is a reduction and its 95% interval excludes zero.
2. NCAP and synthetic cities moved together before 2019: the event-study pre-years are jointly insignificant (p > 0.10).
3. A fake start in 2016 shows no effect.
4. The sign survives the other estimator (Callaway & Sant'Anna), the unweighted city average, and the other satellite version.

If 2 or 3 fails, we say the design cannot identify the effect. If the interval includes zero, we say "no detectable effect", never "no effect". We also say which effect sizes are ruled out, against NCAP's own 20–40% targets.

**How small an effect we could see.** A fake NCAP start in 2014 or 2015, on pre-2019 data only, with 500 random groups of 113 control cities, gives a minimum detectable effect of about **<!--g:mde_pct-->1.2<!--/g-->%** (<!--g:mde_ugm3-->0.9<!--/g--> µg/m³).
- Read it as a *best case*: the real analysis is noisier.
- The real NCAP cities, given the same fake starts, show no pre-2019 divergence: <!--g:placebo_2014_logpts-->0.47<!--/g--> and <!--g:placebo_2015_logpts-->-0.41<!--/g--> log points, both with intervals spanning zero.

**Second question (H2), asked only if H1 is "yes".** Is the drop bigger in winter (Oct–Feb)? Asking it only after a "yes" keeps the overall false-positive risk at 5% without halving the threshold.

**Ground monitors are supporting evidence only.** Before 2018, non-NCAP cities have <!--g:pm10_2017_non-->0<!--/g--> valid PM10 station-years, and only <!--g:pm10_pair_stations-->6<!--/g--> stations (<!--g:pm10_pair_units-->5<!--/g--> cities) have two pre-NCAP years. So with one baseline year:
- we cannot check that NCAP and non-NCAP cities were on parallel paths, and no minimum detectable effect is claimed;
- every ground and PM10 result carries that warning;
- the dust test (H3: PM10 falling more than PM2.5) can at best be "consistent with dust control", never "confirmed".

**Secondary questions.** H4: how much of the *reported* improvement is weather plus new monitors. H5: whether effects are smaller in the Indo-Gangetic Plain. Both are the proposal's own hypotheses, now written down.

**If satellite and ground disagree.** We report both side by side and never average them. The pair is labelled consistent, different in size, conflicting, or uninformative. Then four fixed checks, reported whether or not they explain the gap: which monitors exist, satellite calibration, where monitors sit, and deweathering.

**Many cities, many tests.** City rankings come only from the shrunken (hierarchical) estimates; any raw city claim needs FDR control at 5%. Robustness checks are all reported, including those that weaken the result.

**Your choices, each with its check** (every one is run and reported):

| Primary | Sensitivity |
|---|---|
| Population-weighted city average | Plain area average |
| Satellite V5.GL.06 | V6.GL.03; V6.GL.02.04 |
| 10 towns without a GHSL centre left out | Included as small circles |
| Patancheruvu kept (intention to treat) | Dropped |
| Raniganj inside the Asansol unit | Asansol alone (**new; please confirm**) |
| Hour valid with any 15-minute value | Needs 3 of 4 |
| Calendar 2025 is the last ground year | Add Jan–Mar 2026 (provisional) |
| The 5 stations placed by your decision | All 5 dropped |
| Treated from first listing | From first funding (the next calendar year); 2018 for the 94 cities already on the 2017 list |
| No spillover buffer | Controls within 25 km dropped (<!--g:n_buffered-->754<!--/g--> left) |

**Decisions for you at approval.**
1. Listing date vs funding date as primary (the plan says listing).
2. Adding H4, H5 and the Asansol-alone check.
3. Whether to register on OSF before the gate opens.
