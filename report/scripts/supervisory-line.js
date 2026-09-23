// ---------- Supervisory line ----------
(function supvChart(){
  const months = DATA.supervisory_pct.months, pct = DATA.supervisory_pct.pct;
  const n=months.length;
  const W=460,H=200, ML=30, MR=8, MT=14, MB=26;
  const plotW=W-ML-MR, plotH=H-MT-MB;
  const yMin = Math.floor(Math.min(...pct)/5)*5, yMax = Math.ceil(Math.max(...pct)/5)*5;
  const x = i => ML+(i/(n-1))*plotW;
  const y = v => MT+plotH-((v-yMin)/(yMax-yMin))*plotH;
  const svg = document.getElementById('supv-svg'); svg.innerHTML='';
  [yMin, (yMin+yMax)/2, yMax].forEach(v=>{
    const gy=y(v);
    svg.appendChild(svgEl('line',{x1:ML,x2:W-MR,y1:gy,y2:gy,stroke:colorGrid,'stroke-width':1}));
    svg.appendChild(svgEl('text',{x:ML-6,y:gy+3,'text-anchor':'end','font-size':10,fill:colorMuted,'font-family':'IBM Plex Mono, monospace'})).textContent = Math.round(v)+'%';
  });
  let areaD = 'M '+x(0)+' '+y(yMin);
  for(let i=0;i<n;i++) areaD += ' L '+x(i)+' '+y(pct[i]);
  areaD += ' L '+x(n-1)+' '+y(yMin)+' Z';
  svg.appendChild(svgEl('path',{d:areaD, fill:colorDC, 'fill-opacity':0.14}));
  let lineD='M '+x(0)+' '+y(pct[0]); for(let i=1;i<n;i++) lineD+=' L '+x(i)+' '+y(pct[i]);
  svg.appendChild(svgEl('path',{d:lineD, fill:'none', stroke:colorDC, 'stroke-width':2.25,'stroke-linecap':'round'}));
  monthLabelIndices(n,autoStep(n,7)).forEach(i=>{
    const t=svgEl('text',{x:x(i),y:H-8,'text-anchor':'middle','font-size':9.5,fill:colorMuted,'font-family':'IBM Plex Mono, monospace'});
    t.textContent = fmtMonth(months[i]); svg.appendChild(t);
  });
  const wrap=document.getElementById('supv-wrap'); const tip=document.getElementById('supv-tooltip');
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
    const px=(x(idx)/W)*wrapRect.width, py=(y(pct[idx])/H)*wrapRect.height;
    tip.style.left=px+10+'px'; tip.style.top=Math.max(0,py-40)+'px';
    tip.innerHTML = '<b>'+fmtMonth(months[idx])+'</b><br>'+pct[idx]+'% supervisory';
    tip.classList.add('show');
  });
  overlay.addEventListener('mouseleave',()=>{tip.classList.remove('show'); crosshair.setAttribute('opacity',0);});
  document.getElementById('supv-foot').textContent = pct[0]+'% → '+pct[n-1]+'% — roughly doubled even as headcount shrank.';
})();

