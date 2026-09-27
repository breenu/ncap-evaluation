# What the analysis plan commits to (one-page summary)

*A plain-language summary of [`analysis_plan.md`](analysis_plan.md). Numbers are filled from the pipeline (`python -m src.causal.pregate_report sync-plan`). If this page and the plan disagree, the plan wins.*

**The one question I promise to answer (H1).** Did PM2.5 fall more in NCAP cities than it would have without NCAP?
- **Data:** satellite PM2.5, 2010–2024, averaged over where people live in each city.
- **Sample:** <!--g:n_treated-->113<!--/g--> NCAP urban centres against <!--g:n_controls-->923<!--/g--> non-NCAP centres of 100,000+ people.
- **Method:** synthetic difference-in-differences. It builds each group's "what would have happened" from a weighted mix of control cities that tracked it before 2019.
- **2020:** left out of the headline number (COVID lockdown, BS-VI fuel), but shown separately.

**What counts as "yes".** All four must hold:
1. The estimated effect is a reduction and its 95% interval excludes zero.
2. NCAP and synthetic cities moved together before 2019: the event-study pre-years are jointly insignificant (p > 0.10).
3. A fake start in 2016 shows no effect.
4. The sign survives the other estimator (Callaway & Sant'Anna), the unweighted city average, and the other satellite version.

If 2 or 3 fails, I say the design cannot identify the effect, and if 2 fails I also report Rambachan & Roth (HonestDiD) bounds: how large a pre-trend violation the estimate could survive. If the interval includes zero, I say "no detectable effect", never "no effect". Then comes an equivalence test against a **smallest effect that matters of ±<!--g:equiv_margin-->5<!--/g-->%**: one quarter of NCAP's smallest target (20%, set for PM10). If the 90% interval sits inside ±<!--g:equiv_margin-->5<!--/g-->%, effects that large are ruled out; otherwise the result is inconclusive. I also say which effect sizes are ruled out, against NCAP's own 20–40% targets.

**How small an effect I could see.** A fake NCAP start in 2014 or 2015, on pre-2019 data only, with 500 random groups of 113 control cities, gives a minimum detectable effect of about a **<!--g:mde_pct-->1.2<!--/g-->% fall** (about <!--g:mde_ugm3_implied-->0.6<!--/g--> µg/m³ at the NCAP cities' pre-2019 average of <!--g:level_treated-->51.7<!--/g--> µg/m³).
- Read it as a *best case*: the real analysis is noisier. I report it, but it is not the equivalence margin (that is ±<!--g:equiv_margin-->5<!--/g-->%, above).
- The real NCAP cities, given the same fake starts, show no pre-2019 divergence: <!--g:placebo_2014_pct-->+0.47%<!--/g--> and <!--g:placebo_2015_pct-->-0.41%<!--/g-->, both with intervals spanning zero.

**Second question (H2), asked only if H1 is "yes".** Is the drop bigger in winter (Oct–Feb)? Asking it only after a "yes" keeps the overall false-positive risk at 5% without halving the threshold.

**Ground monitors are supporting evidence only.** Before 2018, non-NCAP cities have <!--g:pm10_2017_non-->0<!--/g--> valid PM10 station-years, and only <!--g:pm10_pair_stations-->6<!--/g--> stations (<!--g:pm10_pair_units-->5<!--/g--> cities) have two pre-NCAP years. So with one baseline year:
- I cannot check that NCAP and non-NCAP cities were on parallel paths, and I claim no minimum detectable effect;
- every ground and PM10 result carries that warning;
- the dust test (H3: PM10 falling more than PM2.5) can at best be "consistent with dust control", never "confirmed".

**Secondary questions.** H4: how much of the *reported* improvement is weather plus new monitors. H5: whether effects are smaller in the Indo-Gangetic Plain. Both come from my original proposal of 25 September 2026, written before any data were downloaded.

**Could the satellite be echoing the new monitors?** The satellite product is calibrated to ground monitors, and NCAP added monitors mostly in NCAP cities. So I also estimate H1 separately for NCAP cities that gained a monitor in <!--g:leak_from-->2019<!--/g-->–<!--g:leak_to-->2024<!--/g--> (<!--g:leak_gain-->74<!--/g-->) and those that did not (<!--g:leak_nogain-->39<!--/g-->): <!--g:leak_estimable-->both groups are large enough to estimate<!--/g-->. An effect found only where monitors were added is reported as a warning sign. Raw satellite aerosol data (MAIAC AOD), which use no monitors, are a further check if time allows.

**If satellite and ground disagree.** I report both side by side and never average them. The pair is labelled consistent, different in size, conflicting, or uninformative. Then come four fixed checks, reported whether or not they explain the gap: which monitors exist, satellite calibration, where monitors sit, and deweathering.

**Many cities, many tests.** City rankings come only from the shrunken (hierarchical) estimates; any raw city claim needs FDR control at 5%. I report every robustness check, including those that weaken the result.

**Main choices, each with its check** (every one is run and reported):

| Primary | Sensitivity |
|---|---|
| Population-weighted city average | Plain area average |
| Satellite V5.GL.06 | V6.GL.03; V6.GL.02.04 |
| 10 towns without a GHSL centre left out | Included as small circles |
| Patancheruvu kept (intention to treat) | Dropped |
| Raniganj inside the Asansol unit | Asansol alone |
| Hour valid with any 15-minute value | Needs 3 of 4 |
| Calendar 2025 is the last ground year | Add Jan–Mar 2026 (provisional) |
| The 5 stations placed by judgement | All 5 dropped |
| Treated from first listing | From first funding (the next calendar year), sensitivity only because funding is partly performance-linked; 2018 for the 94 cities already on the 2017 list |
| No spillover buffer | Controls within 25 km dropped (<!--g:n_buffered-->754<!--/g--> left) |

**Decided on 2026-09-27, before registration.**
1. First listing is the primary treatment date; first funding is a sensitivity check only.
2. H4, H5 and the Asansol-alone check are in.
3. The equivalence margin is ±<!--g:equiv_margin-->5<!--/g-->%, not the MDE; I added the monitor-gain (calibration-leakage) check and HonestDiD bounds. Rules 1–4 above are unchanged.

**What happens next.** I register this plan on OSF. Only after that does the code allow any post-2019 effect to be estimated: the gate is opened in its own commit, citing this plan's commit.
