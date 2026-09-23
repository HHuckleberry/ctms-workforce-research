// ---------- Component adoption and occupational-series monitoring ----------
(function componentSeriesMonitor(){
  const componentBody = document.getElementById('component-adoption-tbody');
  if (componentBody) {
    componentBody.innerHTML = (DATA.component_adoption || []).map(row => {
      const first = row.left_censored
        ? 'Present in '+fmtMonth(row.first_observed)+' (left-censored)'
        : 'After '+fmtMonth(row.previous_snapshot)+'; by '+fmtMonth(row.first_observed);
      return '<tr>' +
        '<td><b>'+row.name+'</b><br><span style="color:var(--text-muted);font-family:IBM Plex Mono,monospace;font-size:11px;">'+row.code+'</span></td>' +
        '<td>'+first+'</td>' +
        '<td class="num">'+row.starting_headcount+'</td>' +
        '<td class="num"><b>'+row.current_headcount+'</b></td>' +
        '<td class="num">'+row.current_dc+' / '+row.current_dl+'</td>' +
        '<td>'+row.peak_headcount+' · '+fmtMonth(row.peak_month)+'</td>' +
        '<td>'+row.series.join(', ')+'</td>' +
        '<td>'+row.status+'</td>' +
      '</tr>';
    }).join('') || '<tr><td colspan="8" style="color:var(--text-muted);">No component data.</td></tr>';
  }
  const componentFoot = document.getElementById('component-adoption-foot');
  if (componentFoot) {
    const settings = DATA.methodology_settings || {};
    componentFoot.textContent = 'Status rules: “Near peak” means current headcount is at least '+Math.round((settings.component_near_peak_ratio || 0.9)*100)+'% of the component peak; “Contracted” means no more than '+Math.round((settings.component_contracted_ratio || 0.6)*100)+'%.';
  }

  const seriesBody = document.getElementById('series-monitor-tbody');
  if (seriesBody) {
    seriesBody.innerHTML = (DATA.series_monitor || []).map(row =>
      '<tr'+(!row.in_current_rule?' style="background:color-mix(in srgb, var(--accent-out) 8%, transparent);"':'')+'>' +
        '<td><b>'+row.series+'</b></td>' +
        '<td>'+fmtMonth(row.first_observed)+'</td>' +
        '<td class="num">'+row.current_headcount+'</td>' +
        '<td>'+row.peak_headcount+' · '+fmtMonth(row.peak_month)+'</td>' +
        '<td>'+row.components.join(', ')+'</td>' +
        '<td>'+(row.in_current_rule?'Included':'Not included')+'</td>' +
        '<td>'+(row.in_current_rule?row.status:'Review for inclusion')+'</td>' +
      '</tr>'
    ).join('') || '<tr><td colspan="7" style="color:var(--text-muted);">Run a full refresh to build the series audit.</td></tr>';
  }
  const foot = document.getElementById('series-monitor-foot');
  if (foot) {
    const outside = (DATA.series_monitor || []).filter(row => !row.in_current_rule);
    foot.textContent = outside.length
      ? outside.length+' DC/DL series '+(outside.length===1?'is':'are')+' outside the current population rule and require review.'
      : 'Every observed DHS DC/DL series is currently accounted for by the population rule.';
  }
})();
