// ---------- Data-derived accountability context ----------
(function accountabilityDynamic(){
  const metrics = DATA.accountability_metrics || {};
  const peak = document.getElementById('acct-peak-context');
  if (peak) peak.textContent = 'The OPM series in this report peaks at '+metrics.peak_headcount+' people in '+fmtMonth(metrics.peak_month)+'.';

  const testimony = document.getElementById('acct-testimony-context');
  if (testimony) {
    const elapsed = metrics.months_from_june_2024_to_peak;
    const timing = elapsed >= 0 ? elapsed+' months later' : Math.abs(elapsed)+' months earlier';
    testimony.textContent = 'The OPM series peaks '+timing+', then changes '+fmtPct(metrics.peak_to_latest_pct)+' from that peak through '+fmtMonth(DATA.coverage.last)+'.';
  }

  const retention = document.getElementById('acct-retention-context');
  const r24 = metrics.retention_24m;
  if (retention && r24 && r24.eligible) {
    retention.innerHTML = 'Using a consistent 24-month milestone, this reconstruction retains <b>'+r24.retained+' of '+r24.eligible+' eligible people ('+r24.pct.toFixed(1)+'%)</b>. Differences from the public claim may reflect cohort, date, and definition differences; the figures should not be treated as directly equivalent without matching those definitions.';
  } else if (retention) {
    retention.textContent = 'The current dataset does not yet contain a maturity-eligible 24-month group for a comparable calculation.';
  }
})();
