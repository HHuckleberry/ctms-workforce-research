// ---------- Cohort table ----------
(function cohortTable(){
  const tbody = document.getElementById('cohort-tbody');
  const cohorts = DATA.cohorts || [];
  cohorts.forEach(c=>{
    const tr = document.createElement('tr'); tr.className = 'drillable';
    const retColor = c.retention_pct >= 70 ? 'var(--good)' : c.retention_pct >= 40 ? 'var(--text-primary)' : 'var(--accent-out)';
    tr.innerHTML =
      '<td>'+c.quarter+(c.left_censored?' <span class="reason-pill" style="margin-left:4px;">at inception</span>':'')+'</td>'+
      '<td class="num">'+c.joined+'</td>'+
      '<td class="num">'+c.still_present+'</td>'+
      '<td class="num" style="color:'+retColor+'">'+c.retention_pct+'%</td>'+
      '<td class="num">'+c.median_tenure_months+' mo</td>'+
      '<td class="num">'+(c.promoted||'–')+'</td>'+
      '<td class="num">'+c.got_raise+'</td>';
    tr.addEventListener('click', () => PeopleTable.applyFilter('cohort', c.quarter, 'Cohort: ' + c.quarter));
    tbody.appendChild(tr);
  });
  const first = cohorts[0];
  const totalJoined = cohorts.reduce((s,c)=>s+c.joined,0);
  const howJoined = Object.entries(DATA.how_joined_counts || {}).sort((a,b)=>b[1]-a[1]);
  const howJoinedNote = howJoined.length
    ? ' How they came aboard: ' + howJoined.map(([k,v])=>v+' via '+k.toLowerCase().replace(/^new hire - /,'new-hire ')).join(', ') + '.'
    : '';
  document.getElementById('cohort-foot').textContent =
    'First-observed cohort: ' + first.quarter + ' — the start of this dataset, ' + first.joined + ' people, both at CISA and left-censored. ' +
    totalJoined + ' people were first observed across ' + cohorts.length + ' quarterly cohorts through ' + fmtMonth(DATA.coverage.last) + '.' + howJoinedNote;
  document.getElementById('cohort-sub').textContent =
    'Everyone grouped by the quarter they first appear in CTMS, tracked forward to see who’s still here. ' +
    'Read retention across cohorts carefully: older cohorts have simply had more time to lose people, so lower retention there isn’t necessarily worse management — it’s more elapsed exposure.';
})();

