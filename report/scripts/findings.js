// ---------- Career-path findings, rendered from DATA.trajectory_insights ----------
(function findingsSection(){
  const T = DATA.trajectory_insights;
  if (!T) return;
  const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const num = (v, d) => v == null ? '&mdash;' : Number(v).toFixed(d == null ? 0 : d);

  document.getElementById('findings-sub').textContent =
    'Generated from the reconstructed timelines each time the report is built. A comparison appears only when every group has at least '
    + T.min_n + ' people. These are associations in a small public dataset, not causes.';

  document.getElementById('findings-cards').innerHTML = T.findings.map(f =>
    '<div class="chart-card"><p style="font-size:14px; line-height:1.5; margin:0 0 8px;"><b>'+esc(f.headline)+'</b></p>'
    + '<p style="font-size:12.5px; line-height:1.55; margin:0; color:var(--text-muted);">'+esc(f.detail)+'</p></div>'
  ).join('');

  document.getElementById('findings-archetype-tbody').innerHTML = T.archetypes.map(a =>
    '<tr><td>'+esc(a.archetype)+'</td><td style="text-align:right">'+a.n+'</td><td style="text-align:right">'+num(a.share_pct,1)+'%</td>'
    + '<td style="text-align:right">'+num(a.median_months_tracked)+'</td><td style="text-align:right">'+(a.median_salary_change_pct == null ? '&mdash;' : num(a.median_salary_change_pct,1)+'%')+'</td>'
    + '<td style="text-align:right">'+num(a.still_present_pct,1)+'%</td></tr>'
  ).join('');
  document.getElementById('findings-archetype-foot').textContent = T.archetype_caveat;

  const names = {first_raise:'First pay increase', tier_change:'Rate-tier change', supervisor:'Became supervisor', dc_to_dl:'Promoted DC to DL'};
  document.getElementById('findings-tte-tbody').innerHTML = Object.keys(names).map(k => {
    const t = T.time_to_event[k];
    const thin = t.n < T.min_n;
    return '<tr><td>'+names[k]+(thin ? ' <span style="color:var(--text-muted)">(too few to summarize)</span>' : '')+'</td><td style="text-align:right">'+t.n+'</td>'
      + (thin ? '<td colspan="3"></td>' : '<td style="text-align:right">'+num(t.p25)+'</td><td style="text-align:right">'+num(t.median_months)+'</td><td style="text-align:right">'+num(t.p75)+'</td>')
      + '</tr>';
  }).join('');
})();
