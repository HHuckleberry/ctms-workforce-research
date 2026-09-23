// ---------- Trajectory cards ----------
(function trajCards(){
  const wrap = document.getElementById('traj-cards');
  DATA.top_raises.forEach(r=>{
    const card = document.createElement('div'); card.className='traj-card drillable';
    const badges = [];
    if (r.promoted) badges.push('<span class="badge promoted">Promoted DC→DL</span>');
    if (r.became_supervisor) badges.push('<span class="badge supervisor">New supervisor</span>');
    card.innerHTML =
      '<div class="traj-top"><span class="traj-loc">'+r.label+'</span><span class="traj-pct">'+fmtPct(r.pct,0)+'</span></div>'+
      '<div class="traj-dollars">'+fmtDollar(r.start_salary)+' → '+fmtDollar(r.end_salary)+'</div>'+
      '<div class="traj-span">'+r.span+'</div>'+
      (badges.length? '<div class="badge-row">'+badges.join('')+'</div>' : '');
    card.addEventListener('click', () => PersonModal.open(r.id));
    wrap.appendChild(card);
  });
})();

