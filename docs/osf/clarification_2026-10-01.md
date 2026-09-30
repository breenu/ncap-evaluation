**Clarification of decision rules, 1 October 2026** (registration https://osf.io/jksne/; plan at commit `6e24eca`)

No hypothesis, threshold or estimator has changed. Some registered rules call effects "changes" that can be read with either sign. I record how I read them; each reading was committed to the public repository before the quantity it governs was computed.

H4 says "raw all-station change minus deweathered balanced-panel change … supported if positive". Measured as concentration changes, a larger reported fall makes this negative: the opposite of the hypothesis that reported improvements exceed corrected improvements. I read "change" as improvement: H4 = corrected change − reported change (commit `29874cf`, before H4 was first computed).

H3's "the PM10 effect exceeds the PM2.5 effect" is read as a larger PM10 reduction (a more negative log effect), with PM10 actually falling.

Throughout, negative means reduction. I also fixed an order for the layer-disagreement categories, because they overlap: uninformative, conflict, consistent, different magnitude; any remaining case is reported as unclassified. These readings are in commit `ba397a2`, made before any Phase 7 estimate.
