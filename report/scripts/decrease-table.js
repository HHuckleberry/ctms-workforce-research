// ---------- Decrease table ----------
(function decreaseTable(){
  const tbody = document.getElementById('decrease-tbody');
  (DATA.pay_decreases || []).forEach(r=>{
    const tr = document.createElement('tr'); tr.className = 'drillable';
    tr.innerHTML = '<td>'+r.location+'</td><td class="num">'+fmtDollar(r.from_salary)+'</td><td class="num">'+fmtDollar(r.to_salary)+'</td>'+
      '<td class="num" style="color:var(--accent-out)">'+fmtPct(r.pct)+'</td>'+
      '<td><span class="reason-pill">'+r.reason+'</span></td>';
    tr.addEventListener('click', () => PersonModal.open(r.id));
    tbody.appendChild(tr);
  });
  const n = (DATA.pay_decreases || []).length;
  document.getElementById('decrease-heading').textContent = 'Every pay decrease, explained (' + n + ' found)';
  document.getElementById('decrease-sub').textContent =
    'Federal pay doesn’t drop for people who stay in place. Out of ' + DATA.summary.pay_increase_events + ' pay-change events across ' +
    DATA.summary.total_tracked_individuals + ' tracked people, all ' + n + ' decreases trace to a specific, ordinary cause — never an unexplained cut.';
})();

