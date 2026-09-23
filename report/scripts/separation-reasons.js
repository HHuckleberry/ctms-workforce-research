// ---------- Separation reasons ----------
(function reasonsList(){
  const entries = Object.entries(DATA.separation_reasons).sort((a,b)=>b[1]-a[1]);
  const total = entries.reduce((s,e)=>s+e[1],0);
  const max = entries[0][1];
  const list = document.getElementById('reasons-list');
  entries.forEach(([label,val],i)=>{
    const row = document.createElement('div'); row.className='bar-row drillable';
    const displayLabel = titleCase(label);
    row.innerHTML = '<span class="bl-label" title="'+label+'">'+displayLabel+'</span>'+
      '<span class="bl-track"><span class="bl-fill" style="width:'+(val/max*100)+'%; background:'+(i===0?colorOut:colorMuted)+'"></span></span>'+
      '<span class="bl-val">'+val+'</span>';
    row.addEventListener('click', () => PeopleTable.applyFilter('how_left', label, 'Left: ' + displayLabel));
    list.appendChild(row);
  });
  const quitPct = Math.round((DATA.separation_reasons['QUIT']||0)/total*100);
  document.getElementById('reasons-sub').textContent = quitPct+'% of the '+total+' people who left did so voluntarily — this is attrition, not a reduction in force.';
  function titleCase(s){ return s.split(' ').map(w=>w.length>2? w[0]+w.slice(1).toLowerCase(): w).join(' '); }
})();

