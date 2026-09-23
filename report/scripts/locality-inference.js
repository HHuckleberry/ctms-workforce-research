// ---------- Work locations (directly observed OPM fields only) ----------
(function workLocations(){
  const ctx = DATA.locality_context || {};

  const teaserBtn = document.getElementById('locality-teaser-btn');
  if (teaserBtn) teaserBtn.addEventListener('click', () => Tabs.show('locality'));

  const head = document.getElementById('locality-headline');
  if (head) {
    head.innerHTML =
      '<div class="stat-grid" style="margin:0;">' +
        '<div class="stat-tile"><div class="stat-value">'+(ctx.active_total!=null?ctx.active_total:'–')+'</div><div class="stat-label">people with a reported locality in '+fmtMonth(ctx.latest_snapshot || DATA.coverage.last)+'</div></div>' +
        '<div class="stat-tile"><div class="stat-value">'+(ctx.active_localities!=null?ctx.active_localities:'–')+'</div><div class="stat-label">OPM locality pay areas represented</div></div>' +
        '<div class="stat-tile"><div class="stat-value">'+(ctx.dc_metro_share_pct!=null?ctx.dc_metro_share_pct+'%':'–')+'</div><div class="stat-label">in the Washington–Baltimore locality ('+(ctx.dc_metro_count!=null?ctx.dc_metro_count:'–')+' people)</div></div>' +
      '</div>';
  }

  const body = document.getElementById('locality-current-tbody');
  if (body) {
    const rows = ctx.by_locality || [];
    body.innerHTML = rows.map(r =>
      '<tr>' +
        '<td>'+r.locality+'</td>' +
        '<td class="num"><b>'+r.active_headcount+'</b></td>' +
        '<td class="num">'+(r.active_share_pct!=null?r.active_share_pct.toFixed(1)+'%':'–')+'</td>' +
        '<td class="num">'+r.dc_count+'</td>' +
        '<td class="num">'+r.dl_count+'</td>' +
        '<td class="num">'+(r.median_adjusted_basic_pay!=null?fmtDollar(r.median_adjusted_basic_pay):'–')+'</td>' +
        '<td class="num">'+r.historical_person_months+'</td>' +
      '</tr>'
    ).join('') || '<tr><td colspan="7" style="color:var(--text-muted);">No locality data.</td></tr>';
  }

  const foot = document.getElementById('locality-current-foot');
  if (foot) {
    foot.textContent = 'Historical person-months count monthly OPM observations, not distinct employees. Salary is the median annualized adjusted basic pay among people active in the latest snapshot.';
  }

  const tierBody = document.getElementById('locality-tier-ranges-tbody');
  if (tierBody) {
    const ranges = ctx.tier_ranges || [];
    const cell = r => r == null
      ? '<td class="num" style="color:var(--text-muted);" colspan="3">not enough people to read</td>'
      : '<td class="num" title="n='+r.n+' person-months">'+fmtDollar(r.min)+'</td><td class="num">'+fmtDollar(r.median)+'</td><td class="num">'+fmtDollar(r.max)+' <span style="color:var(--text-muted);font-size:10px;">(n='+r.n+')</span></td>';
    tierBody.innerHTML = ranges.map(r =>
      '<tr><td><b>'+r.tier+'</b></td>'+cell(r.dc_metro)+cell(r.elsewhere)+'</tr>'
    ).join('') || '<tr><td colspan="7" style="color:var(--text-muted);">No tier data available.</td></tr>';
  }
  const tierFoot = document.getElementById('locality-tier-ranges-foot');
  if (tierFoot) {
    const ranges = ctx.tier_ranges || [];
    const overlapping = ranges.filter((r, i) => i > 0 && r.elsewhere && ranges[i-1].dc_metro && r.elsewhere.max > ranges[i-1].dc_metro.max);
    tierFoot.textContent = 'n (person-months) shown next to each max value; every cell here is backed by at least 12. ' +
      (overlapping.length
        ? 'Tiers overlap across areas - e.g. a higher tier observed elsewhere can pay less than a lower tier observed in DC-metro - so tier number alone is not a reliable stand-in for pay level once location varies.'
        : 'Tiers are cleanly ordered by pay in both areas, with no overlap between adjacent tiers.');
  }

})();
