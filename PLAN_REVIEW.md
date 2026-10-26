# Review — Claude

Reviewing as an independent critic, not editing the pipeline (Codex is doing
that concurrently). Findings below are grounded in the current working tree
(`git log`: `d411e77` → `ff704e6`, plus uncommitted changes as of this
review) and in report artifacts I generated earlier in this same working
session, not assumptions about what the code probably does.

## 1. Highest-priority finding: person identifiers are not just "risky," they're the literal display key

Phase 2.1 undersells this. I traced it end to end:

- `pull/ctms_track_individuals.py:108` builds `raw_key` as the literal
  concatenation `service_computation_date_leave|duty_station_city|
  age_bracket|education_level_code`.
- `person_id` (`ctms_track_individuals.py:159`) is that same string (or a
  union-find canonical representative of one — still the same format).
- `ctms_report_data.py` writes it straight into the public JSON as `"id"`
  (lines 113, 389, 402, 447) and as the literal object keys for
  `person_history[pid]` / `person_events[pid]`.
- It is not hashed, salted, or truncated anywhere between the raw OPM pull
  and the HTML the browser renders.

Concretely: a report I built earlier this session contains rows like
`1988-12-19|MARY ESTHER|55-59|13` and `2013-12-01|ARLINGTON|40-44|13` sitting
in the page's own `DATA` object, visible to anyone who opens dev tools or
view-source. That's a service-computation date (close to, though not
identical to, hire date), duty station, age bracket, and education level, in
plaintext, for every one of the 289 reconstructed people — cross-referenced
against a report that *also* shows component headcounts as low as 2 (ICE)
and 10 (FEMA), and duty stations that are frequently 1–4 people. Someone with
outside knowledge of roughly when a specific person joined DHS (a LinkedIn
post, a press release, a resume) plus their duty station and approximate age
has enough to find that exact person's full salary trajectory, every pay
decrease, and their separation reason.

**Recommendation:** treat this as blocking *report generation*, not just
*public repo publication*. Phase 9 ("audit Git history and generated files
for identifiers") is necessary but scoped too late and too narrowly — it
implies the risk is about what ends up in source control, when the actual
risk is any HTML file this pipeline has already produced and that anyone
might already have (including artifacts published from this chat earlier in
the session). I'd move opaque report-facing IDs to the very top of the
implementation order, ahead of the full refresh, and I'd explicitly note
that already-generated report files should not be shared further until this
lands. Raw composite keys can and should stay in an ignored analytical file
for reconstruction QA — the fix is entirely about what gets serialized into
`ctms_report_data.json`.

## 2. Retention: the plan's Phase 3 diagnosis is correct, and I can point to the exact artifact where it shows up

`still_present_jul_2026` is the sole retention signal feeding the cohort
table, the veteran comparison, the prior-federal-service comparison, the
relocation comparison, and the subelement comparison
(`ctms_report_data.py` lines 124, 211, 244, 259, 265, 303, 414, 420, 469) —
one binary flag, asked to carry five different comparisons.

The concrete failure mode is already visible in the report: the cohort table
shows **2026 Q3 at 100% retention (2 people, 1 month elapsed)** in the same
visual register as **2022 Q4 at 48.9% (43 months elapsed)**. A reader
skimming that table left-to-right sees retention "improving" toward the
present; it's actually pure censoring — recent cohorts haven't had time to
lose anyone yet. This is the single highest-impact accuracy fix available in
the report, not a nice-to-have — endorse Phase 3 as written, and I'd add:
apply the *same* fix to the "pooled survival, cohorts that reached 24
months" figure already used in the report's callout comparing CTMS's 94%
claim against an internally-computed 61.9%. That card is exactly as exposed
to definitional mismatch (what counts as "retained," how censoring is
handled, whether the window matches) as anything Phase 3 is trying to fix
elsewhere, but it's framed as a clean rebuttal of an external claim. If the
methodology changes under Phase 3, that number needs to be recomputed and
re-justified with the same rigor, not grandfathered in because it already
shipped.

## 3. Person-linkage confidence (Phase 2.2): endorse, with a scoped acceptance test

The report already flags gapped timelines (22 of 289, per the methodology
section) but doesn't let a reader — or the report itself — see whether
headline numbers move if those 22 are excluded. 22/289 is ~7.6% of the
population, which sounds small, but small-proportion doesn't imply
small-effect on a median or on an 8-person subgroup like FEMA. This should
be demonstrated, not assumed.

**Concrete acceptance test:** recompute at minimum (a) overall retention %,
(b) DC→DL promotion rate, (c) median time-to-promotion with
gapped/lower-confidence individuals excluded, and show both numbers side by
side. Pass condition: either they're within a stated tolerance, or the
report explicitly flags where they diverge and by how much. This is cheap —
it's the same aggregation functions already written, run twice with a filter
applied.

## 4. CTMS vs. series 2210 (Phase 5): the hard part is done; the narrative text is now the weak point

The fixed-component-scope restructuring described as "already implemented"
checks out — `opm_ctms_pull.py`'s `aggregate_comparison()` restricts both
sides to the union of components that ever have CTMS presence, consistently
across months. That's the right fix and I have no methodology objection to
it.

What I'd flag now is a fairness-of-narrative issue, not a data issue: the
report's existing text reads *"CTMS's total contraction from its own peak
runs meaningfully steeper than 2210's — that gap, not the shared shock, is
where CTMS underperforms the conventional track."* That's a causal claim
sitting right next to a chart, and it doesn't mention — at that point in the
page — that the report's own accountability section, several scrolls later,
independently cites DOGE-driven contract cancellations and CISA-specific
mass departures (Axios, "a third of CISA's top cyber talent gone by Jun
2025") as context for the same Sep–Oct 2025 window. CTMS is concentrated in
CISA; a CISA-specific shock hitting a CISA-concentrated track harder than a
DHS-wide comparison series is a plausible alternative explanation to "CTMS
underperforms as a track design," and the report has the sourcing to say so
right there but doesn't. Recommend either softening "underperforms" to a
descriptive "contracted faster than" or pulling the DOGE/CISA-cut context
up to sit next to this specific claim instead of only appearing later. This
is a text-only change, cheap to make, and it directly addresses "does a
chart communicate the intended conclusion fairly."

## 5. Salary estimate framing: already correctly fixed, no new finding

Checked `hero-stats.js`'s diff — the "Total payroll disbursed" label was
changed to "Estimated salary during observed CTMS tenure," consistent with
the plan's own tracking under Phase 1/6. No action needed here; flagging
only so this doesn't get re-litigated as if it were still open.

## 6. Locality ("Work Locations," Phase 7): the rewrite is the right call, and here's the methodological reason why

I built the locality analysis this rewrite replaced, across two iterations
in this session — first citing an outside supplement schedule, then (at the
user's correction) a version with no external schedule referenced at all,
just an "observed premium" computed as each locality's median pay expressed
as a ratio to that month's pay-plan median.

Even that second, schedule-free version doesn't clear the bar Phase 7 sets,
and I think Phase 7 is right to have gone further than I did. The ratio
normalization only controlled for snapshot month and pay-plan (DC/DL) — not
rate tier, not seniority, not component. A locality showing "+58% premium"
on 7 people (New York, in my version) is fully explained by those 7 people
happening to skew toward higher rate tiers; nothing in that calculation
isolates a location effect from a composition effect. Labeling that
difference a "premium" — even without naming an external schedule — still
implicitly asserts the gap is about *place*, which the data as computed
cannot support. The current "Work Locations" version (headcount, share,
DC/DL mix, descriptive median pay, explicitly not inferring a supplement) is
the defensible version of this section.

**If a real locality-effect estimate is wanted later**, the acceptance test
should be: the estimate must be computed within rate-tier (or at minimum
show the tier-by-tier breakdown honestly, the way the "Current rate tiers"
table already does, without collapsing to a single premium number), because
tier is the confound that made both of my earlier attempts unreliable at
the sample sizes this population actually has outside DC-metro.

## Proposed reordering (responds to "recommend a better order of work")

1. **Opaque report-facing identifiers (2.1)** — moved ahead of the full
   refresh. Governs whether any interim report artifact is safe to share;
   everything downstream inherits this either way, and it's cheap relative
   to what it protects against.
2. Full refresh + validation (Phase 1) — as planned.
3. **Linkage confidence + sensitivity re-run (2.2)** — moved ahead of
   retention work. Phase 3's new maturity-matched metrics will just inherit
   today's linkage uncertainty if this isn't done first; better to know the
   sensitivity bounds before building more analysis on the same foundation.
4. Maturity-matched retention (Phase 3), explicitly including a recompute of
   the existing 94%-vs-61.9% comparison card under the same methodology.
5. Everything else roughly as the plan already proposes.

## High-value vs. attractive-but-low-confidence (responds to "separate high-value from low-confidence")

**Do first:** de-identification, retention maturity-matching, linkage
sensitivity check, vs-2210 narrative softening (all cheap, several are
text-only).

**Defer or scope down:**
- Any revival of locality-effect inference beyond what "Work Locations" now
  shows — resist scope creep back toward a premium/supplement number; the
  sample sizes outside DC-metro (1–17 people per locality) don't support it
  even tier-controlled, most likely.
- Phase 6's time-to-DC→DL and time-between-rate-tier-change broken out by
  cohort × component × prior-service simultaneously. The component table
  alone already shows cells as small as FEMA=10 and ICE=2 for the *whole*
  population; slicing further on two more dimensions will produce mostly
  single-digit or empty cells. Recommend keeping the population-level
  version of these breakdowns and dropping the multi-way cross-tab, or
  explicitly suppressing any cell under a stated minimum (see below).

## Suggested concrete thresholds (responds to "propose acceptance tests for underspecified items")

- **Minimum group size for any retention/pay breakdown:** the locality work
  in this session ended up using n≥5 distinct people *and* n≥12
  person-months as a "reliable" gate, calibrated against this exact
  population's actual sample sizes. That's a reasonable starting point for
  Phase 3's "small groups suppressed or clearly marked" requirement rather
  than inventing a new threshold from scratch — cite it as precedent, adjust
  if a phase's specific denominator (people vs. person-months vs. events)
  differs.
- **"Work Locations" regression test:** since `tests/` already exists, add
  a cheap assertion that the rendered locality output contains no
  "premium," "supplement," or implied-percentage-differential language —
  trivial to write, and it directly encodes the Phase 7 decision so a future
  edit can't silently reintroduce the thing that was just removed.

## Answering the six review questions directly

1. **Claims the data can't support:** any locality-specific supplement
   percentage (Phase 7, already addressed); the 94%-vs-61.9% retention
   comparison as currently framed, pending Phase 3's methodology; "CTMS
   underperforms the conventional track" as a design claim rather than a
   descriptive one, given the CISA-specific confound the report itself has
   sourcing for.
2. **Cohort/retention/linkage/pay/comparison methods challenged:** see §2,
   §3, §4 above.
3. **Privacy/re-identification risk:** see §1 — confirmed and more severe
   than the plan's current wording suggests.
4. **Work ordering:** see "Proposed reordering" above.
5. **High-value vs. low-confidence:** see that section above.
6. **Acceptance tests for underspecified items:** see "Suggested concrete
   thresholds" above, plus the specific tests proposed in §3 and §6.

— Claude, 2026-09-22
