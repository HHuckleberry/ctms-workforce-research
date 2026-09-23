// ---------- Headcount stacked area ----------
(function headcountChart(){
  const months = DATA.headcount.months, dc = DATA.headcount.dc, dl = DATA.headcount.dl, total = DATA.headcount.total;
  const W = 920, H = 360, ML = 40, MR = 12, MT = 20, MB = 40;
  const plotW = W - ML - MR, plotH = H - MT - MB;
  const n = months.length;
  const yMax = niceMax(Math.max(...total) * 1.12);
  const x = i => ML + (i/(n-1)) * plotW;
  const y = v => MT + plotH - (v/yMax) * plotH;

  const svg = document.getElementById('headcount-svg');
  svg.innerHTML = '';

  // gridlines
  const ticksY = 4;
  for (let t=0;t<=ticksY;t++){
    const v = yMax * t/ticksY;
    const gy = y(v);
    svg.appendChild(svgEl('line',{x1:ML,x2:W-MR,y1:gy,y2:gy,stroke:colorGrid,'stroke-width':1}));
    svg.appendChild(svgEl('text',{x:ML-8,y:gy+4,'text-anchor':'end','font-size':11,fill:colorMuted,'font-family':'IBM Plex Mono, monospace'})).textContent = Math.round(v);
  }
  // baseline
  svg.appendChild(svgEl('line',{x1:ML,x2:W-MR,y1:y(0),y2:y(0),stroke:colorAxis,'stroke-width':1}));

  // dc area (0..dc)
  let dPath = 'M ' + x(0) + ' ' + y(0);
  for (let i=0;i<n;i++) dPath += ' L ' + x(i) + ' ' + y(dc[i]);
  dPath += ' L ' + x(n-1) + ' ' + y(0) + ' Z';
  svg.appendChild(svgEl('path',{d:dPath, fill:colorDC, 'fill-opacity':0.85}));

  // dl area (dc..dc+dl)
  let dPath2 = 'M ' + x(0) + ' ' + y(dc[0]);
  for (let i=0;i<n;i++) dPath2 += ' L ' + x(i) + ' ' + y(dc[i]+dl[i]);
  for (let i=n-1;i>=0;i--) dPath2 += ' L ' + x(i) + ' ' + y(dc[i]);
  dPath2 += ' Z';
  svg.appendChild(svgEl('path',{d:dPath2, fill:colorDL, 'fill-opacity':0.85}));

  // Largest two-month separation window, calculated by the pipeline.
  const exitEvent = DATA.major_exit_event;
  const bandStart = exitEvent ? months.indexOf(exitEvent.start) : -1;
  const bandEnd = exitEvent ? months.indexOf(exitEvent.end) : -1;
  if (bandStart>=0 && bandEnd>=0) {
    svg.appendChild(svgEl('rect',{x:x(bandStart), y:MT, width:x(bandEnd)-x(bandStart), height:plotH, fill:colorOut, 'fill-opacity':0.08}));
    const lbl = svgEl('text',{x:(x(bandStart)+x(bandEnd))/2, y:MT-6, 'text-anchor':'middle','font-size':11,fill:colorOut,'font-family':'IBM Plex Mono, monospace','font-weight':600});
    lbl.textContent = (exitEvent.headcount_change>0?'+':'')+exitEvent.headcount_change+' headcount';
    svg.appendChild(lbl);
  }

  // peak marker
  const peakIdx = total.indexOf(Math.max(...total));
  svg.appendChild(svgEl('circle',{cx:x(peakIdx), cy:y(total[peakIdx]), r:3.5, fill:'none', stroke:colorText, 'stroke-width':1.5}));
  const peakLbl = svgEl('text',{x:x(peakIdx), y:y(total[peakIdx])-10, 'text-anchor':'middle','font-size':11,fill:colorText,'font-family':'IBM Plex Mono, monospace'});
  peakLbl.textContent = 'peak ' + total[peakIdx];
  svg.appendChild(peakLbl);

  // current marker
  const lastIdx = n-1;
  svg.appendChild(svgEl('circle',{cx:x(lastIdx), cy:y(total[lastIdx]), r:3.5, fill:colorText}));

  // x axis labels
  monthLabelIndices(n,autoStep(n,11)).forEach(i=>{
    const t = svgEl('text',{x:x(i), y:H-14,'text-anchor':'middle','font-size':10.5,fill:colorMuted,'font-family':'IBM Plex Mono, monospace'});
    t.textContent = fmtMonth(months[i]);
    svg.appendChild(t);
  });

  // hover
  const wrap = document.getElementById('headcount-wrap');
  const tip = document.getElementById('headcount-tooltip');
  const crosshair = svgEl('line',{x1:0,x2:0,y1:MT,y2:MT+plotH,stroke:colorAxis,'stroke-width':1,opacity:0});
  svg.appendChild(crosshair);
  const overlay = svgEl('rect',{x:ML,y:MT,width:plotW,height:plotH,fill:'transparent'});
  svg.appendChild(overlay);
  overlay.addEventListener('mousemove', (e)=>{
    const rect = svg.getBoundingClientRect();
    const scaleX = W/rect.width;
    const mx = (e.clientX-rect.left)*scaleX;
    let idx = Math.round((mx-ML)/plotW*(n-1));
    idx = Math.max(0, Math.min(n-1, idx));
    crosshair.setAttribute('x1', x(idx)); crosshair.setAttribute('x2', x(idx)); crosshair.setAttribute('opacity',1);
    const wrapRect = wrap.getBoundingClientRect();
    const px = (x(idx)/W)*wrapRect.width;
    const py = (y(total[idx])/H)*wrapRect.height;
    tip.style.left = px+14+'px'; tip.style.top = Math.max(0,py-46)+'px';
    tip.innerHTML = '<b>'+fmtMonth(months[idx])+'</b><br>DC '+dc[idx]+' &middot; DL '+dl[idx]+'<br>Total <b>'+total[idx]+'</b>';
    tip.classList.add('show');
  });
  overlay.addEventListener('mouseleave', ()=>{ tip.classList.remove('show'); crosshair.setAttribute('opacity',0); });

  document.getElementById('headcount-foot').textContent =
    'Peak ' + total[peakIdx] + ' in ' + fmtMonth(months[peakIdx]) + ', now ' + total[lastIdx] + ' in ' + fmtMonth(months[lastIdx]) +
    ' — a ' + Math.abs(((total[lastIdx]-total[peakIdx])/total[peakIdx]*100)).toFixed(0) + '% decline. The shaded band marks the largest two-month separation window ('+fmtMonth(exitEvent.start)+'–'+fmtMonth(exitEvent.end)+').';
  document.getElementById('headcount-heading').textContent =
    'Headcount, ' + fmtMonth(months[0]) + ' – ' + fmtMonth(months[lastIdx]);
})();
