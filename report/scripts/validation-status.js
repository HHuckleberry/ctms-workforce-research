// ---------- Refresh validation status ----------
(function validationStatus(){
  const result = DATA.validation;
  const section = document.getElementById('validation-section');
  if (!result) { if (section) section.style.display='none'; return; }
  const headline = document.getElementById('validation-headline');
  const label = result.status === 'pass' ? 'All checks passed' : result.status === 'warning' ? 'Passed with review items' : 'Validation failed';
  const changes = (result.monitor && result.monitor.pull_changes) || [];
  const changeSummary = changes.length
    ? changes.length+' new or revised dataset-month'+(changes.length===1?'':'s')+' processed in the last pull'
    : 'No new or revised snapshots in the last pull';
  if (headline) headline.innerHTML = '<div class="stat-value" style="font-size:22px;">'+label+'</div>' +
    '<div class="stat-label">'+result.errors.length+' errors · '+result.warnings.length+' warnings · '+changeSummary+' · generated '+new Date(result.generated).toLocaleString()+'</div>';
  const body = document.getElementById('validation-tbody');
  if (body) body.innerHTML = (result.checks || []).map(check =>
    '<tr><td>'+check.name+'</td><td><b>'+check.status.toUpperCase()+'</b></td><td>'+check.detail+'</td></tr>'
  ).join('');
})();
