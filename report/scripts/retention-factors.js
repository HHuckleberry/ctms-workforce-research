// ---------- Retention factors ----------
(function retentionFactors(){
  // Prior experience vs retention
  const priorList = document.getElementById('prior-retention-list');
  (DATA.prior_vs_retention || []).forEach(p => {
    const row = document.createElement('div'); row.className = 'bar-row drillable';
    row.innerHTML = '<span class="bl-label" title="'+p.bucket+'">'+p.bucket+'</span>'+
      '<span class="bl-track"><span class="bl-fill" style="width:'+p.retention_pct+'%; background:'+colorDC+'"></span></span>'+
      '<span class="bl-val">'+p.retention_pct+'%</span>';
    row.addEventListener('click', () => PeopleTable.applyFilter('prior_service_bucket', p.bucket, p.bucket + ' (n=' + p.n + ')'));
    priorList.appendChild(row);
  });
  const priorVals = (DATA.prior_vs_retention||[]).map(p=>p.retention_pct);
  const priorSpread = priorVals.length ? Math.max(...priorVals) - Math.min(...priorVals) : 0;
  document.getElementById('prior-retention-foot').textContent =
    priorSpread <= 8
      ? 'Roughly flat across experience levels (spread of only ' + priorSpread.toFixed(1) + ' points) — prior federal experience doesn’t meaningfully predict who stays.'
      : 'A ' + priorSpread.toFixed(1) + '-point spread across experience levels.';

  // Relocation & veteran status
  const rvList = document.getElementById('reloc-veteran-list');
  const rvMax = Math.max(...Object.values(DATA.reloc_vs_retention||{1:0}), ...Object.values(DATA.veteran_retention||{1:0}));
  Object.entries(DATA.reloc_vs_retention||{}).forEach(([label,pct])=>{
    const row = document.createElement('div'); row.className='bar-row drillable';
    row.innerHTML = '<span class="bl-label">'+label+'</span>'+
      '<span class="bl-track"><span class="bl-fill" style="width:'+(pct/rvMax*100)+'%; background:'+colorDC+'"></span></span>'+
      '<span class="bl-val">'+pct+'%</span>';
    row.addEventListener('click', () => PeopleTable.applyFilter('had_relocation', label.startsWith('Relocated'), label));
    rvList.appendChild(row);
  });
  const vetLabels = {Y:'Veteran', N:'Not a veteran'};
  Object.entries(DATA.veteran_retention||{}).forEach(([code,pct])=>{
    const label = vetLabels[code]||code;
    const row = document.createElement('div'); row.className='bar-row drillable';
    row.innerHTML = '<span class="bl-label">'+label+'</span>'+
      '<span class="bl-track"><span class="bl-fill" style="width:'+(pct/rvMax*100)+'%; background:'+colorDL+'"></span></span>'+
      '<span class="bl-val">'+pct+'%</span>';
    row.addEventListener('click', () => PeopleTable.applyFilter('veteran', code, label));
    rvList.appendChild(row);
  });
  const vetCount = (DATA.veteran_counts||{}).Y || 0;
  const vetTotal = Object.values(DATA.veteran_counts||{}).reduce((a,b)=>a+b,0);
  document.getElementById('reloc-veteran-foot').textContent =
    'Relocating at least once tracks with meaningfully higher retention. ' + vetCount + ' of ' + vetTotal + ' tracked people (' + Math.round(vetCount/vetTotal*100) + '%) are veterans.';

  // Tenure-group trend (stacked area)
  const T = DATA.tenure_trend;
  if (T) {
    const seriesNames = Object.keys(T).filter(k=>k!=='months');
    const seriesColors = [colorDC, colorDL, colorMuted];
    const months = T.months, n = months.length;
    const W=460,H=220, ML=36, MR=10, MT=10, MB=26;
    const plotW=W-ML-MR, plotH=H-MT-MB;
    const x = i => ML+(i/(n-1))*plotW;
    const y = v => MT+plotH-(v/100)*plotH;
    const svg = document.getElementById('tenure-svg'); svg.innerHTML='';
    [0,25,50,75,100].forEach(v=>{
      const gy=y(v);
      svg.appendChild(svgEl('line',{x1:ML,x2:W-MR,y1:gy,y2:gy,stroke:colorGrid,'stroke-width':1}));
      svg.appendChild(svgEl('text',{x:ML-6,y:gy+3,'text-anchor':'end','font-size':9,fill:colorMuted,'font-family':'IBM Plex Mono, monospace'})).textContent = v+'%';
    });
    let cum = new Array(n).fill(0);
    seriesNames.forEach((name,si)=>{
      const vals = T[name];
      let d = 'M '+x(0)+' '+y(cum[0]);
      for(let i=0;i<n;i++) d += ' L '+x(i)+' '+y(cum[i]+vals[i]);
      for(let i=n-1;i>=0;i--) d += ' L '+x(i)+' '+y(cum[i]);
      d += ' Z';
      svg.appendChild(svgEl('path',{d, fill:seriesColors[si%seriesColors.length], 'fill-opacity':0.75}));
      cum = cum.map((c,i)=>c+vals[i]);
    });
    monthLabelIndices(n,autoStep(n,6)).forEach(i=>{
      const t=svgEl('text',{x:x(i),y:H-8,'text-anchor':'middle','font-size':9,fill:colorMuted,'font-family':'IBM Plex Mono, monospace'});
      t.textContent = fmtMonth(months[i]); svg.appendChild(t);
    });
    const legend = document.getElementById('tenure-legend');
    legend.innerHTML = seriesNames.map((name,si)=>
      '<span class="legend-item"><span class="legend-swatch" style="background:'+seriesColors[si%seriesColors.length]+'"></span>'+name+'</span>').join('');

    const wrap = document.getElementById('tenure-wrap'); const tip = document.getElementById('tenure-tooltip');
    const crosshair = svgEl('line',{x1:0,x2:0,y1:MT,y2:MT+plotH,stroke:colorAxis,'stroke-width':1,opacity:0});
    svg.appendChild(crosshair);
    const overlay = svgEl('rect',{x:ML,y:MT,width:plotW,height:plotH,fill:'transparent'});
    svg.appendChild(overlay);
    overlay.addEventListener('mousemove',(e)=>{
      const rect=svg.getBoundingClientRect(); const scaleX=W/rect.width;
      const mx=(e.clientX-rect.left)*scaleX;
      let idx=Math.round((mx-ML)/plotW*(n-1)); idx=Math.max(0,Math.min(n-1,idx));
      crosshair.setAttribute('x1',x(idx)); crosshair.setAttribute('x2',x(idx)); crosshair.setAttribute('opacity',1);
      const wrapRect=wrap.getBoundingClientRect();
      const px=(x(idx)/W)*wrapRect.width, py=(H/2/H)*wrapRect.height;
      tip.style.left=px+10+'px'; tip.style.top=Math.max(0,py-60)+'px';
      tip.innerHTML = '<b>'+fmtMonth(months[idx])+'</b><br>'+seriesNames.map(name=>name+': '+T[name][idx]+'%').join('<br>');
      tip.classList.add('show');
    });
    overlay.addEventListener('mouseleave',()=>{tip.classList.remove('show'); crosshair.setAttribute('opacity',0);});
  }

  // Time to advance
  const ta = DATA.time_to_advance || {};
  document.getElementById('time-to-promo').textContent = ta.promotion && ta.promotion.n ? ta.promotion.median_months + ' mo (n=' + ta.promotion.n + ')' : '–';
  document.getElementById('time-to-supervisor').textContent = ta.supervisor && ta.supervisor.n ? ta.supervisor.median_months + ' mo (n=' + ta.supervisor.n + ')' : '–';

  // Boomerang
  const bm = DATA.boomerangs || [];
  document.getElementById('boomerang-note').textContent = bm.length
    ? bm.length + ' case' + (bm.length===1?'':'s') + ' where someone left and a later accession shares their service date: ' +
      bm.map(b=>fmtMonth(b.left)+' → back by '+fmtMonth(b.rejoined)).join('; ') + '.'
    : 'No boomerang cases found — nobody who left has a later accession record sharing their service date.';
})();

