// ---------- Raise-year explorer ----------
(function raiseYears(){
  const years = DATA.raise_years || [];
  const wrap = document.getElementById('raise-year-cards');
  years.forEach(ry => {
    const tiers = ry.tiers;
    const maxCount = Math.max(...tiers.map(t=>t.count));
    const bars = tiers.map(t => {
      const color = t.pct > 0 ? colorDC : t.pct < 0 ? colorOut : colorMuted;
      const h = Math.max(2, t.count/maxCount*100);
      return '<div class="raise-bar" style="height:'+h+'%; background:'+color+';" ' +
        'title="'+fmtPct(t.pct,1)+' — '+t.count+' '+(t.count===1?'person':'people')+'" ' +
        'data-pct="'+t.pct+'"></div>';
    }).join('');

    const card = document.createElement('div');
    card.className = 'raise-year-card';
    card.innerHTML =
      '<div class="raise-year-top">' +
        '<span class="raise-year-title">Jan '+ry.year+'</span>' +
        '<span class="raise-year-transition">'+ry.transition+' · '+fmtMonth(ry.from_month)+' → '+fmtMonth(ry.to_month)+'</span>' +
      '</div>' +
      '<div class="raise-stat-row">' +
        '<div class="raise-stat"><span class="raise-stat-label">People</span><span class="raise-stat-value">'+ry.n+'</span></div>' +
        '<div class="raise-stat"><span class="raise-stat-label">Mean</span><span class="raise-stat-value">'+fmtPct(ry.mean_pct)+'</span></div>' +
        '<div class="raise-stat"><span class="raise-stat-label">Median</span><span class="raise-stat-value">'+fmtPct(ry.median_pct)+'</span></div>' +
        '<div class="raise-stat"><span class="raise-stat-label">Major groupings</span><span class="raise-stat-value">'+ry.n_groupings+'</span></div>' +
        '<div class="raise-stat"><span class="raise-stat-label">Distinct amounts</span><span class="raise-stat-value">'+ry.n_distinct_values+'</span></div>' +
      '</div>' +
      '<div class="raise-histogram">'+bars+'</div>' +
      '<div class="raise-axis-labels"><span>'+fmtPct(tiers[0].pct,1)+'</span><span>0%</span><span>'+fmtPct(tiers[tiers.length-1].pct,1)+'</span></div>';

    card.querySelectorAll('.raise-bar').forEach((barEl, i) => {
      barEl.addEventListener('click', () => {
        const t = tiers[i];
        PeopleTable.applyIdFilter(t.ids, 'Jan '+ry.year+': '+fmtPct(t.pct,1)+' raise');
      });
    });
    wrap.appendChild(card);
  });
  if (!years.length) {
    wrap.innerHTML = '<div style="font-size:13px;color:var(--text-muted);">No raise-tier data available for this pull.</div>';
  }
})();

// expose for inline-ish handlers built as strings elsewhere in this file
window.PeopleTable = PeopleTable;
window.PersonModal = PersonModal;
