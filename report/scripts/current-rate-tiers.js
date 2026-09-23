// ---------- Current rate tiers ----------
(function rateTiers(){
  const tiers = DATA.rate_tiers || [];
  const tbody = document.getElementById('rate-tier-tbody');
  tbody.innerHTML = tiers.map(t =>
    '<tr data-tier="'+t.tier+'">' +
      '<td><b>'+t.tier+'</b></td>' +
      '<td class="num drillable" data-plan="DC">'+t.dc+'</td>' +
      '<td class="num">'+(t.dc_median==null?'–':fmtDollar(t.dc_median))+'</td>' +
      '<td class="num drillable" data-plan="DL">'+t.dl+'</td>' +
      '<td class="num">'+(t.dl_median==null?'–':fmtDollar(t.dl_median))+'</td>' +
      '<td class="num drillable" data-plan="ALL"><b>'+t.total+'</b></td>' +
    '</tr>'
  ).join('');
  tbody.querySelectorAll('td.drillable').forEach(cell => {
    cell.addEventListener('click', () => {
      const t = tiers.find(x => x.tier === cell.closest('tr').dataset.tier);
      const plan = cell.dataset.plan;
      const ids = plan === 'DC' ? t.dc_ids : (plan === 'DL' ? t.dl_ids : t.ids);
      PeopleTable.applyIdFilter(ids, t.tier + (plan === 'ALL' ? '' : ' · ' + plan));
    });
  });
  const changes = DATA.rate_change_summary || {events:0, people:0};
  document.getElementById('rate-tier-foot').textContent =
    'As of ' + fmtMonth(DATA.coverage.last) + '. Across the observed history, OPM records ' +
    changes.events + ' rate-tier changes involving ' + changes.people + ' people. ' +
    'Within DC, tiers generally rise with pay; DL uses the same field but does not populate every tier.';
})();

