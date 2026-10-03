*The text below was posted on the OSF registration (https://osf.io/jksne/) on 1 October 2026, appended to the Inference Criteria section. The registered plan is commit `6e24eca`.*

---

CLARIFICATION ADDED 1 OCTOBER 2026 (the text above is unchanged)

No hypothesis, threshold or estimator has changed. Some registered rules describe effects as "changes" that can be read with either sign. Throughout, I read negative as a reduction.

H4 says "raw all-station change minus deweathered balanced-panel change … supported if positive". Read literally as concentration changes, a larger reported fall makes this negative, the opposite of the hypothesis that reported improvements exceed corrected ones. I read "change" as improvement: H4 = corrected change − reported change. I recorded this reading in a git commit (29874cf) before first computing H4; that commit was pushed publicly on 1 October 2026, after H4 had been computed.

H3's "the PM10 effect exceeds the PM2.5 effect" is read as a larger PM10 reduction, with PM10 actually falling.

The layer-disagreement categories overlap, so I apply them in a fixed order: uninformative, conflict, consistent, different magnitude; any remaining case is reported as unclassified.

These readings were committed (ba397a2) and pushed before any Phase 7 estimate was computed. All deviations from the plan are logged with dates in the repository's DECISIONS.md and will be listed in the final report.
