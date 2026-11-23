// ---------- Decrease table ----------
(function decreaseTable(){
  const rows = DATA.pay_decreases || [];
  const tbody = document.getElementById('decrease-tbody');
  rows.forEach(r => {
    const tr = document.createElement('tr'); tr.className = 'drillable';
    tr.innerHTML =
      '<td>' + fmtMonth(r.month) + '</td>' +
      '<td>' + r.location + '</td>' +
      '<td class="num">' + fmtDollar(r.from_salary) + '</td><td class="num">' + fmtDollar(r.to_salary) + '</td>' +
      '<td class="num" style="color:var(--accent-out)">' + fmtPct(r.pct) + '</td>' +
      '<td class="num" title="Pay before ÷ pay after">' + (r.ratio != null ? r.ratio.toFixed(4) : '–') + '</td>' +
      '<td><span class="reason-pill"' + (r.explained ? '' : ' style="color:var(--accent-out);border-color:var(--accent-out);"') + '>' + r.reason + '</span>' +
        (r.detail ? '<div class="chart-foot" style="margin-top:3px;">' + r.detail + '</div>' : '') + '</td>';
    tr.addEventListener('click', () => PersonModal.open(r.id));
    tbody.appendChild(tr);
  });

  const n = rows.length;
  const s = DATA.summary;
  const changes = s.pay_increase_events + s.pay_decrease_events;
  const relocated = rows.filter(r => r.reason_code === 'relocation_lower_locality' || r.reason_code === 'relocation_lagged').length;
  const spikes = rows.filter(r => r.reason_code === 'reverses_prior_spike').length;
  const unaccounted = rows.filter(r => !r.explained).length;
  const parts = [];
  if (relocated) parts.push(relocated + ' followed a move to a different locality pay area');
  if (spikes) parts.push(spikes + ' only reverse' + (spikes === 1 ? 's' : '') + ' a one-month spike and ' + (spikes === 1 ? 'is' : 'are') + ' not a net cut');
  const tier = rows.filter(r => r.reason_code === 'rate_tier_change').length;
  if (tier) parts.push(tier + ' coincide' + (tier === 1 ? 's' : '') + ' with a same-locality rate-tier change');

  document.getElementById('decrease-heading').textContent = 'Every pay decrease (' + n + ' found)';
  document.getElementById('decrease-sub').textContent =
    'Out of ' + changes.toLocaleString() + ' month-to-month pay changes across ' + s.total_tracked_individuals +
    ' tracked people, ' + n + ' were decreases. ' + (parts.length ? 'Of those, ' + parts.join('; ') + '. ' : '') +
    (unaccounted
      ? unaccounted + ' cannot be accounted for from OPM data alone (highlighted). '
      : 'Each one is accounted for by the OPM records. ') +
    'Ratio is pay before ÷ pay after; relocation cuts land on exact repeating values (1.1000, 1.0476), which points to fixed locality pay levels rather than individual pay reductions.';
})();
