// ---------- Pay spread (percentile bands) ----------
function drawSpread(svgId, wrapId, tipId, months, series, color){
  const pts = months.map((m,i)=>({m, s: series[i]})).filter(p=>p.s);
  if (pts.length < 2) { document.getElementById(svgId).outerHTML = '<div style="font-size:12px;color:var(--text-muted);padding:20px 0;">Not enough data.</div>'; return; }
  const W=460,H=220, ML=46, MR=10, MT=14, MB=26;
  const plotW=W-ML-MR, plotH=H-MT-MB;
  const n = pts.length;
  const allVals = pts.flatMap(p=>[p.s.p10, p.s.p90]);
  const yMin = Math.min(...allVals)*0.96, yMax = Math.max(...allVals)*1.04;
  const x = i => ML+(i/(n-1))*plotW;
  const y = v => MT+plotH-((v-yMin)/(yMax-yMin))*plotH;

  const svg = document.getElementById(svgId);
  svg.innerHTML = '';
  [yMin, (yMin+yMax)/2, yMax].forEach(v=>{
    const gy=y(v);
    svg.appendChild(svgEl('line',{x1:ML,x2:W-MR,y1:gy,y2:gy,stroke:colorGrid,'stroke-width':1}));
    svg.appendChild(svgEl('text',{x:ML-6,y:gy+3,'text-anchor':'end','font-size':9,fill:colorMuted,'font-family':'IBM Plex Mono, monospace'})).textContent = fmtDollar(v).replace(/,\d{3}$/, 'k').replace('$','$');
  });

  // p25-p75 band
  let bandD = 'M '+x(0)+' '+y(pts[0].s.p25);
  for(let i=1;i<n;i++) bandD += ' L '+x(i)+' '+y(pts[i].s.p25);
  for(let i=n-1;i>=0;i--) bandD += ' L '+x(i)+' '+y(pts[i].s.p75);
  bandD += ' Z';
  svg.appendChild(svgEl('path',{d:bandD, fill:color, 'fill-opacity':0.18}));

  function line(key, width, dash){
    let d = 'M '+x(0)+' '+y(pts[0].s[key]);
    for(let i=1;i<n;i++) d += ' L '+x(i)+' '+y(pts[i].s[key]);
    const attrs = {d, fill:'none', stroke:color, 'stroke-width':width, 'stroke-linecap':'round','stroke-linejoin':'round'};
    if (dash) attrs['stroke-dasharray'] = dash;
    svg.appendChild(svgEl('path', attrs));
  }
  line('p10', 1, '2,2');
  line('p90', 1, '2,2');
  line('median', 2.25, null);

  monthLabelIndices(n, autoStep(n,7)).forEach(i=>{
    const t=svgEl('text',{x:x(i),y:H-8,'text-anchor':'middle','font-size':9.5,fill:colorMuted,'font-family':'IBM Plex Mono, monospace'});
    t.textContent = fmtMonth(pts[i].m); svg.appendChild(t);
  });

  const wrap = document.getElementById(wrapId);
  const tip = document.getElementById(tipId);
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
    const px=(x(idx)/W)*wrapRect.width, py=(y(pts[idx].s.median)/H)*wrapRect.height;
    tip.style.left=px+12+'px'; tip.style.top=Math.max(0,py-70)+'px';
    const s = pts[idx].s;
    tip.innerHTML = '<b>'+fmtMonth(pts[idx].m)+'</b><br>p90 '+fmtDollar(s.p90)+'<br>p75 '+fmtDollar(s.p75)+'<br><b>median '+fmtDollar(s.median)+'</b><br>p25 '+fmtDollar(s.p25)+'<br>p10 '+fmtDollar(s.p10)+'<br>n='+s.n;
    tip.classList.add('show');
  });
  overlay.addEventListener('mouseleave',()=>{tip.classList.remove('show'); crosshair.setAttribute('opacity',0);});
}

(function spreadCharts(){
  const S = DATA.salary_spread;
  if (!S) return;
  drawSpread('spread-dc-svg','spread-dc-wrap','spread-dc-tooltip', S.months, S.dc, colorDC);
  drawSpread('spread-dl-svg','spread-dl-wrap','spread-dl-tooltip', S.months, S.dl, colorDL);
  const lastDc = [...S.dc].reverse().find(Boolean), lastDl = [...S.dl].reverse().find(Boolean);
  if (lastDc && lastDl) {
    document.getElementById('spread-foot').textContent =
      'Latest month: DC ranges '+fmtDollar(lastDc.p10)+'–'+fmtDollar(lastDc.p90)+' (p10–p90) around a '+fmtDollar(lastDc.median)+' median — more than 2x top-to-bottom at the same nominal pay plan. DL ranges '+fmtDollar(lastDl.p10)+'–'+fmtDollar(lastDl.p90)+' around '+fmtDollar(lastDl.median)+'.';
  }
})();

