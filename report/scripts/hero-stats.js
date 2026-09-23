// ---------- Hero stats ----------
(function heroStats(){
  document.getElementById('coverage-text').textContent =
    fmtMonth(DATA.coverage.first) + ' → ' + fmtMonth(DATA.coverage.last) + ' · ' + DATA.coverage.n_months + ' monthly snapshots';

  const declinePct = ((DATA.latest_headcount - DATA.peak_headcount) / DATA.peak_headcount * 100);
  const s = DATA.summary;
  const estimatedSalaryCost = DATA.estimated_salary_cost ?? DATA.total_payroll_disbursed;
  const stats = [
    { label: 'Estimated salary during observed CTMS tenure', value: '$' + (estimatedSalaryCost/1e6).toFixed(1) + 'M', delta: null },
    { label: 'Current headcount (' + fmtMonth(DATA.coverage.last) + ')', value: DATA.latest_headcount, delta: null },
    { label: 'Peak headcount (' + fmtMonth(DATA.peak_month) + ')', value: DATA.peak_headcount, delta: fmtPct(declinePct,0) + ' since peak', down: true },
    { label: 'Individuals tracked across ' + DATA.coverage.n_months + ' months', value: s.total_tracked_individuals, delta: null },
    { label: 'Got at least one raise', value: s.got_any_raise + ' / ' + s.total_tracked_individuals, delta: Math.round(s.got_any_raise/s.total_tracked_individuals*100) + '%', up: true },
    { label: 'Promoted, DC → DL', value: s.promoted_dc_to_dl, delta: null },
    { label: 'Became a supervisor/manager', value: s.became_supervisor, delta: null },
  ];
  const grid = document.getElementById('stat-grid');
  stats.forEach(st => {
    const tile = document.createElement('div');
    tile.className = 'stat-tile';
    tile.innerHTML = '<div class="stat-value">' + st.value + '</div>' +
      '<div class="stat-label">' + st.label + '</div>' +
      (st.delta ? '<div class="stat-delta ' + (st.down?'down':st.up?'up':'') + '">' + st.delta + '</div>' : '');
    grid.appendChild(tile);
  });
})();
