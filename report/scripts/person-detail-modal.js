// ---------- Person detail modal ----------
const PersonModal = (function(){
  const overlay = document.getElementById('person-modal');
  const card = document.getElementById('person-modal-card');

  const eventDesc = {
    pay_increase: e => 'Pay <b>' + fmtDollar(e.from_salary) + ' → ' + fmtDollar(e.to_salary) + '</b> (' + fmtPct(e.pct) + ')',
    pay_decrease: e => 'Pay <b>' + fmtDollar(e.from_salary) + ' → ' + fmtDollar(e.to_salary) + '</b> (' + fmtPct(e.pct) + ')' + (e.reason ? ' — ' + e.reason.replace(/_/g,' ') : ''),
    pay_plan_change: e => (e.to_value==='DL' ? '<b>Promoted</b> ' : '<b>Moved</b> ') + e.from_value + ' → ' + e.to_value,
    rate_tier_change: e => 'Rate tier <b>' + e.from_value + ' → ' + e.to_value + '</b>',
    became_supervisor: () => 'Became a <b>supervisor/manager</b>',
    relocation: e => 'Relocated <b>' + titleCase(e.from_value) + ' → ' + titleCase(e.to_value) + '</b>',
  };
  function titleCase(s){ return (s||'').split(' ').map(w=>w? w[0]+w.slice(1).toLowerCase():w).join(' '); }
  const eventColor = { pay_increase: colorDC, pay_decrease: colorOut, pay_plan_change: colorDL, rate_tier_change: colorDL, became_supervisor: colorDC, relocation: colorMuted };

  function drawTrajectory(history){
    const W = 560, H = 130, ML = 44, MR = 10, MT = 10, MB = 20;
    const plotW = W-ML-MR, plotH = H-MT-MB;
    const pts = history.filter(h => h.sal != null);
    if (pts.length < 2) return '<div style="font-size:12px;color:var(--text-muted);padding:10px 0;">Not enough salary data points to chart.</div>';
    const n = pts.length;
    const yMin = Math.min(...pts.map(p=>p.sal)) * 0.97, yMax = Math.max(...pts.map(p=>p.sal)) * 1.03;
    const x = i => ML + (i/(n-1))*plotW;
    const y = v => MT + plotH - ((v-yMin)/(yMax-yMin))*plotH;
    let d = 'M '+x(0)+' '+y(pts[0].sal);
    for (let i=1;i<n;i++) d += ' L '+x(i)+' '+y(pts[i].sal);
    const gridY = [yMin, (yMin+yMax)/2, yMax];
    let svg = '<svg viewBox="0 0 '+W+' '+H+'" style="width:100%;height:auto;display:block;">';
    gridY.forEach(v=>{
      svg += '<line x1="'+ML+'" x2="'+(W-MR)+'" y1="'+y(v)+'" y2="'+y(v)+'" stroke="'+colorGrid+'" stroke-width="1"/>';
      svg += '<text x="'+(ML-6)+'" y="'+(y(v)+3)+'" text-anchor="end" font-size="9" fill="'+colorMuted+'" font-family="IBM Plex Mono, monospace">'+fmtDollar(v).replace('$','$').replace(/,000$/,'k')+'</text>';
    });
    svg += '<path d="'+d+'" fill="none" stroke="'+colorDC+'" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>';
    svg += '<circle cx="'+x(n-1)+'" cy="'+y(pts[n-1].sal)+'" r="3" fill="'+colorDC+'"/>';
    svg += '</svg>';
    return svg;
  }

  function open(pid){
    const person = PeopleTable.rows.find(p => p.id === pid);
    if (!person) return;
    const history = DATA.person_history[pid] || [];
    const events = DATA.person_events[pid] || [];

    const badges = (person.promoted ? '<span class="mini-badge promoted">Promoted DC→DL</span>' : '') +
                   (person.supervisor ? '<span class="mini-badge supervisor">Became supervisor</span>' : '');

    const timelineHtml = events.length
      ? events.map(e => {
          const desc = eventDesc[e.event] ? eventDesc[e.event](e) : e.event;
          return '<div class="timeline-row">' +
            '<span class="timeline-date">'+fmtMonth(e.to)+'</span>' +
            '<span class="timeline-icon" style="background:'+(eventColor[e.event]||colorMuted)+'"></span>' +
            '<span class="timeline-desc">'+desc+'</span>' +
          '</div>';
        }).join('')
      : '<div style="font-size:12.5px;color:var(--text-muted);">No detected pay/career events for this person.</div>';

    card.innerHTML =
      '<div class="modal-top">' +
        '<div><div class="modal-title">'+person.duty_station+' · '+person.subelement+'</div>' +
        '<div class="modal-sub">'+person.cohort+' cohort · first observed '+firstObservedLabel(person.joined)+'</div></div>' +
        '<button class="modal-close" id="modal-close-btn" aria-label="Close">✕</button>' +
      '</div>' +
      (badges ? '<div class="badge-row" style="margin-bottom:14px;">'+badges+'</div>' : '') +
      '<div class="modal-stat-grid">' +
        '<div class="modal-stat"><div class="modal-stat-label">Status</div><div class="modal-stat-value" style="color:'+(person.active?'var(--good)':'var(--text-muted)')+'">'+(person.active?'Active':('Left '+fmtMonth(person.last_seen)))+'</div></div>' +
        '<div class="modal-stat"><div class="modal-stat-label">Tenure</div><div class="modal-stat-value">'+person.tenure_months+' mo</div></div>' +
        '<div class="modal-stat"><div class="modal-stat-label">Prior federal svc</div><div class="modal-stat-value">'+(person.prior_years!=null?person.prior_years+'y':'–')+'</div></div>' +
        '<div class="modal-stat"><div class="modal-stat-label">Pay plan</div><div class="modal-stat-value">'+person.plan+'</div></div>' +
        '<div class="modal-stat"><div class="modal-stat-label">Rate tier</div><div class="modal-stat-value">'+(person.start_rate_tier ? (person.start_rate_tier===person.rate_tier ? person.rate_tier : person.start_rate_tier+' → '+person.rate_tier) : (person.rate_tier||'–'))+'</div></div>' +
        (person.how_left ? '<div class="modal-stat"><div class="modal-stat-label">Left because</div><div class="modal-stat-value" style="font-size:12px;">'+titleCase(person.how_left)+'</div></div>' : '') +
      '</div>' +
      '<div class="modal-section-title">Salary trajectory ('+fmtDollar(person.start_salary)+' → '+fmtDollar(person.end_salary)+', '+fmtPct(person.pct_change)+')</div>' +
      '<div class="modal-chart-wrap">'+drawTrajectory(history)+'</div>' +
      '<div class="modal-section-title">Timeline ('+events.length+' detected event'+(events.length===1?'':'s')+')</div>' +
      '<div class="timeline">'+timelineHtml+'</div>';

    overlay.hidden = false;
    document.getElementById('modal-close-btn').addEventListener('click', close);
  }
  function close(){ overlay.hidden = true; }
  overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') close(); });

  return { open, close };
})();

