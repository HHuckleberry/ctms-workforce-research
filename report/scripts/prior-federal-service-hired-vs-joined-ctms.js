// ---------- Prior federal service (hired vs. joined CTMS) ----------
(function priorService(){
  const s = DATA.prior_service_summary || {};
  document.getElementById('prior-median').textContent = (s.median_years!=null ? s.median_years+' yrs' : '—');
  document.getElementById('prior-new-pct').textContent = (s.pct_new_to_federal!=null ? s.pct_new_to_federal+'%' : '—');
  document.getElementById('prior-max').textContent = (s.max_years!=null ? s.max_years+' yrs' : '—');

  const list = document.getElementById('prior-service-list');
  const buckets = DATA.prior_service || [];
  const max = Math.max(...buckets.map(b=>b.count), 1);
  buckets.forEach((b,i)=>{
    const row = document.createElement('div'); row.className='bar-row';
    row.innerHTML = '<span class="bl-label" title="'+b.bucket+'">'+b.bucket+'</span>'+
      '<span class="bl-track"><span class="bl-fill" style="width:'+(b.count/max*100)+'%; background:'+(i===0?colorDL:colorDC)+'"></span></span>'+
      '<span class="bl-val">'+b.count+'</span>';
    list.appendChild(row);
  });
})();

