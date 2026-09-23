// ---------- Pay growth indexed line chart ----------
(function payChart(){
  const months = DATA.salary.months, dcM = DATA.salary.dc_median, dlM = DATA.salary.dl_median;
  const n = months.length;
  const dcIdx = dcM.map(v=>v/dcM[0]*100);
  const dlIdx = dlM.map(v=>v/dlM[0]*100);
  const W=620,H=340, ML=36, MR=12, MT=20, MB=34;
  const plotW=W-ML-MR, plotH=H-MT-MB;
  const allVals = dcIdx.concat(dlIdx);
  const yMin = Math.floor(Math.min(...allVals)/5)*5 - 2;
  const yMax = Math.ceil(Math.max(...allVals)/5)*5 + 2;
  const x = i => ML + (i/(n-1))*plotW;
  const y = v => MT + plotH - ((v-yMin)/(yMax-yMin))*plotH;

  const svg = document.getElementById('pay-svg');
  svg.innerHTML='';
  const ticksY=4;
  for(let t=0;t<=ticksY;t++){
    const v = yMin + (yMax-yMin)*t/ticksY;
    const gy=y(v);
    svg.appendChild(svgEl('line',{x1:ML,x2:W-MR,y1:gy,y2:gy,stroke:colorGrid,'stroke-width':1}));
    svg.appendChild(svgEl('text',{x:ML-8,y:gy+4,'text-anchor':'end','font-size':10.5,fill:colorMuted,'font-family':'IBM Plex Mono, monospace'})).textContent = Math.round(v);
  }
  // 100 baseline emphasized
  svg.appendChild(svgEl('line',{x1:ML,x2:W-MR,y1:y(100),y2:y(100),stroke:colorAxis,'stroke-width':1,'stroke-dasharray':'3,3'}));

  function linePath(arr){ let d='M '+x(0)+' '+y(arr[0]); for(let i=1;i<n;i++) d+=' L '+x(i)+' '+y(arr[i]); return d; }
  svg.appendChild(svgEl('path',{d:linePath(dcIdx), fill:'none', stroke:colorDC, 'stroke-width':2.5, 'stroke-linecap':'round','stroke-linejoin':'round'}));
  svg.appendChild(svgEl('path',{d:linePath(dlIdx), fill:'none', stroke:colorDL, 'stroke-width':2.5, 'stroke-linecap':'round','stroke-linejoin':'round'}));

  // Jan boundary ticks - year parsed from the label (was hardcoded to only
  // 2024/2025/2026 and silently mismapped any other year, e.g. Jan 2023,
  // onto 2026-02; fixed to handle whatever years jan_boundaries actually has).
  DATA.jan_boundaries.forEach(jb=>{
    const yr = jb.label.split(' ')[1];
    const febIdx = months.indexOf(yr + '-02');
    if (febIdx<0) return;
    svg.appendChild(svgEl('circle',{cx:x(febIdx),cy:y(dcIdx[febIdx]),r:3,fill:colorDC}));
    svg.appendChild(svgEl('circle',{cx:x(febIdx),cy:y(dlIdx[febIdx]),r:3,fill:colorDL}));
    if (yr === '2026') {
      const shutdownLbl = svgEl('text',{x:x(febIdx),y:y(Math.max(dcIdx[febIdx],dlIdx[febIdx]))-10,'text-anchor':'middle','font-size':9.5,fill:colorOut,'font-family':'IBM Plex Mono, monospace','font-weight':600});
      shutdownLbl.textContent = 'shutdown-delayed raise';
      svg.appendChild(shutdownLbl);
    }
  });

  monthLabelIndices(n,autoStep(n,9)).forEach(i=>{
    const t=svgEl('text',{x:x(i),y:H-12,'text-anchor':'middle','font-size':10,fill:colorMuted,'font-family':'IBM Plex Mono, monospace'});
    t.textContent = fmtMonth(months[i]);
    svg.appendChild(t);
  });

  const wrap = document.getElementById('pay-wrap');
  const tip = document.getElementById('pay-tooltip');
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
    const px=(x(idx)/W)*wrapRect.width, py=(Math.min(y(dcIdx[idx]),y(dlIdx[idx]))/H)*wrapRect.height;
    tip.style.left=px+14+'px'; tip.style.top=Math.max(0,py-56)+'px';
    tip.innerHTML = '<b>'+fmtMonth(months[idx])+'</b><br>DC '+fmtDollar(dcM[idx])+' (idx '+dcIdx[idx].toFixed(1)+')<br>DL '+fmtDollar(dlM[idx])+' (idx '+dlIdx[idx].toFixed(1)+')';
    tip.classList.add('show');
  });
  overlay.addEventListener('mouseleave',()=>{tip.classList.remove('show'); crosshair.setAttribute('opacity',0);});

  document.getElementById('dc-dollar-move').textContent = fmtDollar(dcM[0]) + ' → ' + fmtDollar(dcM[n-1]);
  document.getElementById('dl-dollar-move').textContent = fmtDollar(dlM[0]) + ' → ' + fmtDollar(dlM[n-1]);
  document.getElementById('pay-heading').textContent = 'Pay growth, indexed to ' + fmtMonth(months[0]);

  const janWrap = document.getElementById('jan-boundaries');
  DATA.jan_boundaries.forEach(jb=>{
    const dcPct = (jb.dc_after-jb.dc_before)/jb.dc_before*100;
    const dlPct = (jb.dl_after-jb.dl_before)/jb.dl_before*100;
    const row = document.createElement('div');
    row.style.cssText='display:flex; justify-content:space-between; font-size:12.5px;';
    row.innerHTML = '<span style="color:var(--text-secondary)">'+jb.label+'</span><span class="mono">DC '+fmtPct(dcPct)+' &middot; DL '+fmtPct(dlPct)+'</span>';
    janWrap.appendChild(row);
  });
})();

