// ---------- Flow diverging bars ----------
(function flowChart(){
  const months = DATA.flow.months, acc = DATA.flow.accessions, sep = DATA.flow.separations;
  const n = months.length;
  const W=920,H=300, ML=36, MR=12, MT=16, MB=34;
  const plotW=W-ML-MR, plotH=H-MT-MB;
  const yMax = niceMax(Math.max(Math.max(...acc), Math.max(...sep)) * 1.15);
  const x0 = i => ML + (i/n)*plotW;
  const bw = plotW/n * 0.62;
  const yMid = MT + plotH/2;
  const yScale = v => (v/yMax) * (plotH/2);

  const svg = document.getElementById('flow-svg');
  svg.innerHTML='';
  [0.5,1].forEach(f=>{
    const v = yMax*f;
    svg.appendChild(svgEl('line',{x1:ML,x2:W-MR,y1:yMid-yScale(v),y2:yMid-yScale(v),stroke:colorGrid,'stroke-width':1}));
    svg.appendChild(svgEl('line',{x1:ML,x2:W-MR,y1:yMid+yScale(v),y2:yMid+yScale(v),stroke:colorGrid,'stroke-width':1}));
  });
  svg.appendChild(svgEl('line',{x1:ML,x2:W-MR,y1:yMid,y2:yMid,stroke:colorAxis,'stroke-width':1}));

  const bars = [];
  for(let i=0;i<n;i++){
    const cx = x0(i) + (plotW/n)/2;
    const hAcc = yScale(acc[i]);
    const rAcc = svgEl('rect',{x:cx-bw/2, y:yMid-hAcc, width:bw, height:Math.max(hAcc,0.6), fill:colorDC, rx:2});
    svg.appendChild(rAcc);
    const hSep = yScale(sep[i]);
    const rSep = svgEl('rect',{x:cx-bw/2, y:yMid, width:bw, height:Math.max(hSep,0.6), fill:colorOut, rx:2});
    svg.appendChild(rSep);
    bars.push({cx, i});
  }

  monthLabelIndices(n,autoStep(n,11)).forEach(i=>{
    const cx = x0(i) + (plotW/n)/2;
    const t=svgEl('text',{x:cx,y:H-12,'text-anchor':'middle','font-size':10.5,fill:colorMuted,'font-family':'IBM Plex Mono, monospace'});
    t.textContent = fmtMonth(months[i]);
    svg.appendChild(t);
  });

  const wrap = document.getElementById('flow-wrap');
  const tip = document.getElementById('flow-tooltip');
  const hitW = plotW/n;
  bars.forEach(b=>{
    const hit = svgEl('rect',{x:b.cx-hitW/2, y:MT, width:hitW, height:plotH, fill:'transparent'});
    svg.appendChild(hit);
    hit.addEventListener('mouseenter', ()=>{
      const wrapRect = wrap.getBoundingClientRect();
      const px = (b.cx/W)*wrapRect.width, py=(yMid/H)*wrapRect.height;
      tip.style.left = px+12+'px'; tip.style.top = Math.max(0,py-60)+'px';
      tip.innerHTML = '<b>'+fmtMonth(months[b.i])+'</b><br>Joined '+acc[b.i]+' &middot; Left '+sep[b.i]+'<br>Net '+(acc[b.i]-sep[b.i]>=0?'+':'')+(acc[b.i]-sep[b.i]);
      tip.classList.add('show');
    });
    hit.addEventListener('mouseleave', ()=> tip.classList.remove('show'));
  });

  const event = DATA.major_exit_event;
  document.getElementById('flow-foot').textContent = event
    ? fmtMonth(event.start)+'–'+fmtMonth(event.end)+': '+event.departures+' departures in the largest two-month separation window — '+event.share_of_all_departures_pct.toFixed(1)+'% of everyone who left across '+n+' months of history.'
    : 'No two-month exit window is available.';
})();
