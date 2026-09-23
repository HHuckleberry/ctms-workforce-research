// ---------- CTMS vs. series 2210 ----------
(function vs2210Chart(){
  const V = DATA.vs_2210;
  if (!V) { document.getElementById('vs2210-section').style.display = 'none'; return; }
  const months = V.months, ctmsIdx = V.ctms_index, itIdx = V.series_2210_index;
  const n = months.length;
  const W=920,H=320, ML=36, MR=12, MT=20, MB=34;
  const plotW=W-ML-MR, plotH=H-MT-MB;
  const allVals = ctmsIdx.concat(itIdx);
  const yMin = Math.floor(Math.min(...allVals)/10)*10 - 2;
  const yMax = Math.ceil(Math.max(...allVals)/10)*10 + 2;
  const x = i => ML + (i/(n-1))*plotW;
  const y = v => MT + plotH - ((v-yMin)/(yMax-yMin))*plotH;

  const svg = document.getElementById('vs2210-svg');
  svg.innerHTML='';
  const ticksY=5;
  for(let t=0;t<=ticksY;t++){
    const v = yMin + (yMax-yMin)*t/ticksY;
    const gy=y(v);
    svg.appendChild(svgEl('line',{x1:ML,x2:W-MR,y1:gy,y2:gy,stroke:colorGrid,'stroke-width':1}));
    svg.appendChild(svgEl('text',{x:ML-8,y:gy+4,'text-anchor':'end','font-size':10.5,fill:colorMuted,'font-family':'IBM Plex Mono, monospace'})).textContent = Math.round(v);
  }
  svg.appendChild(svgEl('line',{x1:ML,x2:W-MR,y1:y(100),y2:y(100),stroke:colorAxis,'stroke-width':1,'stroke-dasharray':'3,3'}));

  function linePath(arr){ let d='M '+x(0)+' '+y(arr[0]); for(let i=1;i<n;i++) d+=' L '+x(i)+' '+y(arr[i]); return d; }
  svg.appendChild(svgEl('path',{d:linePath(ctmsIdx), fill:'none', stroke:colorDC, 'stroke-width':2.5, 'stroke-linecap':'round','stroke-linejoin':'round'}));
  svg.appendChild(svgEl('path',{d:linePath(itIdx), fill:'none', stroke:colorDL, 'stroke-width':2.5, 'stroke-linecap':'round','stroke-linejoin':'round'}));

  // Sep-Oct 2025 shock band
  const bandStart = months.indexOf('2025-09'), bandEnd = months.indexOf('2025-10');
  if (bandStart>=0 && bandEnd>=0) {
    svg.appendChild(svgEl('rect',{x:x(bandStart), y:MT, width:x(bandEnd)-x(bandStart), height:plotH, fill:colorOut, 'fill-opacity':0.08}));
  }

  monthLabelIndices(n,autoStep(n,11)).forEach(i=>{
    const t=svgEl('text',{x:x(i),y:H-12,'text-anchor':'middle','font-size':10,fill:colorMuted,'font-family':'IBM Plex Mono, monospace'});
    t.textContent = fmtMonth(months[i]);
    svg.appendChild(t);
  });

  const wrap = document.getElementById('vs2210-wrap');
  const tip = document.getElementById('vs2210-tooltip');
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
    const px=(x(idx)/W)*wrapRect.width, py=(Math.min(y(ctmsIdx[idx]),y(itIdx[idx]))/H)*wrapRect.height;
    tip.style.left=px+14+'px'; tip.style.top=Math.max(0,py-56)+'px';
    tip.innerHTML = '<b>'+fmtMonth(months[idx])+'</b><br>CTMS '+V.ctms[idx]+' (idx '+ctmsIdx[idx].toFixed(1)+')<br>2210 '+V.series_2210[idx]+' (idx '+itIdx[idx].toFixed(1)+')';
    tip.classList.add('show');
  });
  overlay.addEventListener('mouseleave',()=>{tip.classList.remove('show'); crosshair.setAttribute('opacity',0);});

  document.getElementById('vs2210-shock-ctms').textContent = fmtPct(V.shock_ctms_pct);
  document.getElementById('vs2210-shock-ctms').style.color = 'var(--accent-out)';
  document.getElementById('vs2210-shock-it').textContent = fmtPct(V.shock_it_pct);
  document.getElementById('vs2210-shock-it').style.color = 'var(--accent-out)';
  document.getElementById('vs2210-peak-ctms').textContent = fmtPct(V.ctms_peak_to_now_pct);
  document.getElementById('vs2210-peak-ctms').style.color = 'var(--accent-out)';
  document.getElementById('vs2210-peak-it').textContent = fmtPct(V.it_peak_to_now_pct);
  document.getElementById('vs2210-peak-it').style.color = 'var(--accent-out)';
  document.getElementById('vs2210-foot').textContent =
    'The Sep–Oct 2025 shock hit both tracks almost identically (' + fmtPct(V.shock_ctms_pct) + ' vs ' + fmtPct(V.shock_it_pct) + ') — not a CTMS-specific event. ' +
    'But CTMS’s total contraction from its own peak (' + fmtMonth(V.ctms_peak.month) + ', ' + V.ctms_peak.value + ') runs meaningfully steeper than 2210’s (' + fmtMonth(V.it_peak.month) + ', ' + V.it_peak.value + ') — that gap, not the shared shock, is where CTMS underperforms the conventional track.';
})();

