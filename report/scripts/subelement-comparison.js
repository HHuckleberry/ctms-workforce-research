// ---------- Subelement comparison ----------
(function subelementTable(){
  const tbody = document.getElementById('subelement-tbody');
  (DATA.subelement_stats || []).forEach(s => {
    const tr = document.createElement('tr'); tr.className = 'drillable';
    tr.innerHTML =
      '<td>'+s.code+'</td>' +
      '<td class="num">'+s.n+'</td>' +
      '<td class="num">'+(s.median_salary!=null ? fmtDollar(s.median_salary) : '–')+'</td>' +
      '<td class="num">'+s.pct_dl+'%</td>' +
      '<td class="num">'+s.pct_supervisor+'%</td>' +
      '<td class="num">'+s.pct_still_present+'%</td>' +
      '<td class="num">'+(s.median_prior_years!=null ? s.median_prior_years+'y' : '–')+'</td>';
    tr.addEventListener('click', () => PeopleTable.applyFilter('subelement', s.code, 'Component: ' + s.code));
    tbody.appendChild(tr);
  });
})();

