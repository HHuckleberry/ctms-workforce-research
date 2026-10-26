// ---------- Raise-year explorer ----------
(function raiseYears(){
  const years = DATA.raise_years || [];
  const wrap = document.getElementById('raise-year-cards');
  PlanToggle.mount(document.getElementById('raises-plan-toggle'));

  // DC and DL are separate pay tables. "Both" stacks DC (bottom) and DL (top)
  // in each bar; DC or DL shows only that plan's raises and stats.
  function tiersFor(ry, plan){
    if (plan === 'ALL') return ry.tiers;
    const key = plan === 'DC' ? 'dc' : 'dl';
    return ry.tiers
      .filter(t => t[key + '_count'] > 0)
      .map(t => ({ ...t, count: t[key + '_count'], ids: t[key + '_ids'],
                   dc_count: plan === 'DC' ? t.dc_count : 0, dl_count: plan === 'DL' ? t.dl_count : 0 }));
  }

  function statsFor(ry, plan){
    if (plan === 'ALL') return { n: ry.n, mean_pct: ry.mean_pct, median_pct: ry.median_pct };
    return plan === 'DC' ? ry.dc : ry.dl;
  }

  function stat(label, value){
    return '<div class="raise-stat"><span class="raise-stat-label">'+label+'</span><span class="raise-stat-value">'+value+'</span></div>';
  }

  function render(plan){
    wrap.innerHTML = '';
    years.forEach(ry => {
      const tiers = tiersFor(ry, plan);
      const s = statsFor(ry, plan);
      const card = document.createElement('div');
      card.className = 'raise-year-card';
      if (!tiers.length || !s || !s.n) {
        card.innerHTML = '<div class="raise-year-top"><span class="raise-year-title">Jan '+ry.year+'</span></div>' +
          '<div style="font-size:12.5px;color:var(--text-muted);padding:8px 0;">No '+plan+' raises observed this cycle.</div>';
        wrap.appendChild(card);
        return;
      }
      const maxCount = Math.max(...tiers.map(t => t.count));
      const bars = tiers.map((t, i) => {
        const h = Math.max(2, t.count / maxCount * 100);
        const dimmed = t.pct <= 0 ? 'opacity:0.45;' : '';
        const seg = (p, n, color) => n ? '<div class="raise-seg" data-tier="'+i+'" data-plan="'+p+'" ' +
          'style="flex:'+n+' 1 0; background:'+color+';" ' +
          'title="'+fmtPct(t.pct,1)+' — '+p+': '+n+' '+(n===1?'person':'people')+'"></div>' : '';
        return '<div class="raise-bar" style="height:'+h+'%; display:flex; flex-direction:column-reverse; '+dimmed+'">' +
          seg('DC', t.dc_count, colorDC) + seg('DL', t.dl_count, colorDL) + '</div>';
      }).join('');

      const planBreakdown = plan === 'ALL'
        ? stat('DC (n='+ry.dc.n+')', fmtPct(ry.dc.mean_pct)+' <span class="raise-sub">mean · '+fmtPct(ry.dc.median_pct)+' median</span>') +
          (ry.dl.n ? stat('DL (n='+ry.dl.n+')', fmtPct(ry.dl.mean_pct)+' <span class="raise-sub">mean · '+fmtPct(ry.dl.median_pct)+' median</span>') : '')
        : '';

      card.innerHTML =
        '<div class="raise-year-top">' +
          '<span class="raise-year-title">Jan '+ry.year+(plan === 'ALL' ? '' : ' · '+plan)+'</span>' +
          '<span class="raise-year-transition">'+ry.transition+' · '+fmtMonth(ry.from_month)+' → '+fmtMonth(ry.to_month)+'</span>' +
        '</div>' +
        '<div class="raise-stat-row">' +
          stat('People', s.n) + stat('Mean', fmtPct(s.mean_pct)) + stat('Median', fmtPct(s.median_pct)) +
          stat('Major groupings', tiers.filter(t => t.count >= 2).length) +
          stat('Distinct amounts', tiers.length) +
          planBreakdown +
        '</div>' +
        (plan === 'ALL' ? '<div class="legend" style="margin-bottom:6px;">' +
          '<span class="legend-item"><span class="legend-swatch" style="background:'+colorDC+'"></span>DC</span>' +
          '<span class="legend-item"><span class="legend-swatch" style="background:'+colorDL+'"></span>DL</span></div>' : '') +
        '<div class="raise-histogram">'+bars+'</div>' +
        '<div class="raise-axis-labels"><span>'+fmtPct(tiers[0].pct,1)+'</span><span>'+fmtPct(tiers[tiers.length-1].pct,1)+'</span></div>';

      card.querySelectorAll('.raise-seg').forEach(segEl => {
        segEl.addEventListener('click', () => {
          const t = tiers[+segEl.dataset.tier], p = segEl.dataset.plan;
          const ids = p === 'DC' ? t.dc_ids : t.dl_ids;
          PeopleTable.applyIdFilter(ids, 'Jan '+ry.year+': '+fmtPct(t.pct,1)+' raise · '+p);
        });
      });
      wrap.appendChild(card);
    });
    if (!years.length) {
      wrap.innerHTML = '<div style="font-size:13px;color:var(--text-muted);">No raise-tier data available for this pull.</div>';
    }
  }

  render(PlanToggle.get());
  PlanToggle.subscribe(render);
})();

// expose for inline-ish handlers built as strings elsewhere in this file
window.PeopleTable = PeopleTable;
window.PersonModal = PersonModal;
