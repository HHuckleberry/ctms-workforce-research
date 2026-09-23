// ---------- Cohort table ----------
(function cohortTable(){
  const tbody = document.getElementById('cohort-tbody');
  const cohorts = DATA.cohorts || [];
  function milestoneCell(result){
    if (!result || !result.eligible) return '<span style="color:var(--text-muted);">Not mature</span>';
    return result.retained+'/'+result.eligible+' ('+result.pct.toFixed(1)+'%)';
  }
  cohorts.forEach(c=>{
    const tr = document.createElement('tr'); tr.className = 'drillable';
    tr.innerHTML =
      '<td>'+c.quarter+(c.left_censored?' <span class="reason-pill" style="margin-left:4px;">at inception</span>':'')+'</td>'+
      '<td class="num">'+c.joined+'</td>'+
      '<td class="num">'+c.still_present+'</td>'+
      '<td class="num">'+milestoneCell(c.retention_12m)+'</td>'+
      '<td class="num">'+milestoneCell(c.retention_24m)+'</td>'+
      '<td class="num">'+c.median_tenure_months+' mo</td>'+
      '<td class="num">'+(c.promoted||'–')+'</td>';
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
    'First-observed cohort: ' + first.quarter + ' — the start of this dataset, ' + first.joined + ' people across ' + first.components.join(', ') + ', and left-censored. ' +
    totalJoined + ' people were first observed across ' + cohorts.length + ' quarterly cohorts through ' + fmtMonth(DATA.coverage.last) + '.' + howJoinedNote;
  document.getElementById('cohort-sub').textContent =
    'Retention is measured only among people whose first-observed month is at least 12 or 24 months before '+fmtMonth(DATA.coverage.last)+'. Recent cohorts remain “Not mature” instead of being credited with retention before reaching the milestone.';
})();
