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

  // Two different things both look like "a promotion": moving pay plan
  // (DC -> DL, a track change) and moving up a RATE tier within the same
  // plan. RATE numbers only mean something within one plan's own scale - the
  // same month a person moves DC -> DL, their rate tier can read as "going
  // down" (e.g. DC RATE 02 -> DL RATE 01) purely because DL numbers its own
  // tiers from 01, not because anything got worse. So: when a rate-tier
  // change lands on the same month as a pay-plan change, it's folded into
  // that one track-promotion line rather than judged as its own up/down move.
  function buildPromotionHistory(events){
    const planChangeMonths = new Set(events.filter(e => e.event === 'pay_plan_change').map(e => e.to));
    const items = [];
    events.forEach(e => {
      if (e.event === 'pay_plan_change') {
        items.push({
          date: e.to,
          kind: e.to_value === 'DL' ? 'track-promotion' : 'track-move',
          label: e.to_value === 'DL' ? 'Track promotion' : 'Track move',
          detail: e.from_value + ' → ' + e.to_value + ' (pay plan)',
        });
      } else if (e.event === 'rate_tier_change' && !planChangeMonths.has(e.to)) {
        const fromN = parseInt(String(e.from_value).replace(/\D/g, ''), 10);
        const toN = parseInt(String(e.to_value).replace(/\D/g, ''), 10);
        const up = toN > fromN;
        items.push({
          date: e.to,
          kind: up ? 'tier-advancement' : 'tier-decrease',
          label: up ? 'Rate tier advancement' : 'Rate tier decrease',
          detail: e.from_value + ' → ' + e.to_value + ' (same pay plan)',
        });
      }
    });
    return items.sort((a, b) => a.date < b.date ? -1 : a.date > b.date ? 1 : 0);
  }
  const promoColor = { 'track-promotion': colorDL, 'track-move': colorMuted, 'tier-advancement': colorDC, 'tier-decrease': colorOut };

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
    const totalFedSvc = person.prior_years != null ? Math.round((person.prior_years + person.tenure_months / 12) * 10) / 10 : null;

    const startRow = person.start_salary != null
      ? '<div class="timeline-row">' +
          '<span class="timeline-date">'+fmtMonth(person.joined)+'</span>' +
          '<span class="timeline-icon" style="background:'+colorMuted+'"></span>' +
          '<span class="timeline-desc">Starting point: <b>'+fmtDollar(person.start_salary)+'</b>'+(person.start_rate_tier?' · <b>'+person.start_rate_tier+'</b>':'')+'</span>' +
        '</div>'
      : '';

    // Events sharing the same "to" month (e.g. a promotion that moves rate
    // tier, pay, and pay plan all at once) are one real-world transition, not
    // three unrelated ones - group them visually: show the date once, and
    // drop the divider between rows in the same group.
    const eventRows = events.map((e, i) => {
      const desc = eventDesc[e.event] ? eventDesc[e.event](e) : e.event;
      const sameAsPrev = i > 0 && events[i-1].to === e.to;
      const sameAsNext = i < events.length - 1 && events[i+1].to === e.to;
      const cls = 'timeline-row' + (sameAsNext ? ' timeline-row-tight' : '');
      return '<div class="'+cls+'">' +
        '<span class="timeline-date">'+(sameAsPrev ? '' : fmtMonth(e.to))+'</span>' +
        '<span class="timeline-icon" style="background:'+(eventColor[e.event]||colorMuted)+'"></span>' +
        '<span class="timeline-desc">'+desc+'</span>' +
      '</div>';
    }).join('');

    const timelineHtml = (startRow + eventRows) ||
      '<div style="font-size:12.5px;color:var(--text-muted);">No detected pay/career events for this person.</div>';

    const promotions = buildPromotionHistory(events);
    const promoHtml = promotions.length
      ? '<div class="modal-section-title">Promotion history ('+promotions.length+')</div>' +
        '<div class="timeline" style="max-height:none;">' + promotions.map(p =>
          '<div class="timeline-row">' +
            '<span class="timeline-date">'+fmtMonth(p.date)+'</span>' +
            '<span class="timeline-icon" style="background:'+(promoColor[p.kind]||colorMuted)+'"></span>' +
            '<span class="timeline-desc"><b>'+p.label+'</b> — '+p.detail+'</span>' +
          '</div>'
        ).join('') + '</div>'
      : '';

    card.innerHTML =
      '<div class="modal-top">' +
        '<div><div class="modal-title">'+person.duty_station+' · '+person.subelement+'</div>' +
        '<div class="modal-sub">'+person.cohort+' cohort · first observed '+firstObservedLabel(person.joined)+'</div></div>' +
        '<button class="modal-close" id="modal-close-btn" aria-label="Close">✕</button>' +
      '</div>' +
      (badges ? '<div class="badge-row" style="margin-bottom:14px;">'+badges+'</div>' : '') +
      '<div class="modal-stat-grid">' +
        '<div class="modal-stat"><div class="modal-stat-label">Status</div><div class="modal-stat-value" style="color:'+(person.active?'var(--good)':'var(--text-muted)')+'">'+(person.active?'Active':('Left '+fmtMonth(person.last_seen)))+'</div></div>' +
        '<div class="modal-stat"><div class="modal-stat-label">Tenure in CTMS</div><div class="modal-stat-value">'+person.tenure_months+' mo</div></div>' +
        '<div class="modal-stat"><div class="modal-stat-label">Federal svc before CTMS</div><div class="modal-stat-value">'+(person.prior_years!=null?person.prior_years+'y':'–')+'</div></div>' +
        '<div class="modal-stat"><div class="modal-stat-label">Total federal svc</div><div class="modal-stat-value">'+(totalFedSvc!=null?totalFedSvc+'y':'–')+'</div></div>' +
        '<div class="modal-stat"><div class="modal-stat-label">Pay plan</div><div class="modal-stat-value">'+person.plan+'</div></div>' +
        '<div class="modal-stat"><div class="modal-stat-label">Rate tier</div><div class="modal-stat-value">'+(person.rate_tier||'–')+'</div></div>' +
        (person.how_left ? '<div class="modal-stat"><div class="modal-stat-label">Left because</div><div class="modal-stat-value" style="font-size:12px;">'+titleCase(person.how_left)+'</div></div>' : '') +
      '</div>' +
      promoHtml +
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

