// ---------- Within-tier pay compression (scatter + fitted trend per year) ----------
(function payCompression(){
  const years = DATA.pay_compression || [];
  const wrap = document.getElementById('pay-compression-cards');
  if (!wrap) return;

  const TIER_COLORS = {
    'RATE 01': colorDC, 'RATE 02': colorDL, 'RATE 03': colorOut,
    'RATE 04': '#9b6fd1', 'RATE 05': '#2ea88a', 'RATE 06': colorMuted,
  };
  function tierColor(t){ return TIER_COLORS[t] || colorMuted; }

  function quantile(sorted, q){
    const pos = (sorted.length - 1) * q, base = Math.floor(pos), rest = pos - base;
    return sorted[base + 1] !== undefined ? sorted[base] + rest * (sorted[base + 1] - sorted[base]) : sorted[base];
  }

  function drawScatter(pc){
    const W = 620, H = 200, ML = 56, MR = 14, MT = 12, MB = 30;
    const plotW = W - ML - MR, plotH = H - MT - MB;
    const pts = pc.points || [];
    if (pts.length < 3) return '<div style="font-size:12px;color:var(--text-muted);padding:10px 0;">Not enough people that year to plot.</div>';

    const xs = pts.map(p => p.starting_salary), ys = pts.map(p => p.raise_pct);
    const xMin = Math.min(...xs) * 0.98, xMax = Math.max(...xs) * 1.02;
    // Robust (Tukey-fence) y-domain instead of raw min/max - one outsized
    // individual raise shouldn't compress everyone else into an unreadable
    // sliver. Points outside the fence are still drawn, just clamped to the
    // axis edge with a distinct marker and their real value in the tooltip.
    const ySorted = ys.slice().sort((a, b) => a - b);
    const q1 = quantile(ySorted, 0.25), q3 = quantile(ySorted, 0.75), iqr = q3 - q1;
    const fenceLo = q1 - 1.5 * iqr, fenceHi = q3 + 1.5 * iqr;
    const yMin = Math.min(0, Math.max(Math.min(...ys), fenceLo) - 0.5);
    const yMax = Math.min(Math.max(...ys), fenceHi) + 0.5;
    const x = v => ML + ((v - xMin) / (xMax - xMin)) * plotW;
    const y = v => MT + plotH - ((Math.max(yMin, Math.min(yMax, v)) - yMin) / (yMax - yMin)) * plotH;
    const offScale = pts.filter(p => p.raise_pct < yMin || p.raise_pct > yMax);

    let svg = '<svg viewBox="0 0 '+W+' '+H+'" style="width:100%;height:auto;display:block;">';

    // gridlines + y labels
    const yTicks = 4;
    for (let i = 0; i <= yTicks; i++) {
      const v = yMin + (yMax - yMin) * (i / yTicks);
      svg += '<line x1="'+ML+'" x2="'+(W-MR)+'" y1="'+y(v)+'" y2="'+y(v)+'" stroke="'+colorGrid+'" stroke-width="1"/>';
      svg += '<text x="'+(ML-8)+'" y="'+(y(v)+3)+'" text-anchor="end" font-size="9.5" fill="'+colorMuted+'" font-family="IBM Plex Mono, monospace">'+v.toFixed(1)+'%</text>';
    }
    // x labels (min/max starting salary)
    svg += '<text x="'+ML+'" y="'+(H-8)+'" font-size="9.5" fill="'+colorMuted+'" font-family="IBM Plex Mono, monospace">'+fmtDollar(Math.min(...xs))+'</text>';
    svg += '<text x="'+(W-MR)+'" y="'+(H-8)+'" text-anchor="end" font-size="9.5" fill="'+colorMuted+'" font-family="IBM Plex Mono, monospace">'+fmtDollar(Math.max(...xs))+'</text>';
    svg += '<text x="'+((ML+W-MR)/2)+'" y="'+(H-8)+'" text-anchor="middle" font-size="9.5" fill="'+colorMuted+'" font-family="IBM Plex Mono, monospace">starting salary</text>';

    // fitted trend line
    if (pc.overall_slope != null && pc.overall_intercept != null) {
      const y1 = pc.overall_slope * xMin + pc.overall_intercept;
      const y2 = pc.overall_slope * xMax + pc.overall_intercept;
      svg += '<line x1="'+x(xMin)+'" y1="'+y(Math.max(yMin,Math.min(yMax,y1)))+'" x2="'+x(xMax)+'" y2="'+y(Math.max(yMin,Math.min(yMax,y2)))+'" stroke="'+colorText+'" stroke-width="1.5" stroke-dasharray="4 3"/>';
    }

    // points - off-scale ones (beyond the robust fence) are clamped to the
    // axis edge and drawn as a hollow diamond so they read as "there's more
    // here" rather than silently vanishing or wrecking everyone else's scale
    pts.forEach(p => {
      const off = p.raise_pct < yMin || p.raise_pct > yMax;
      const cx = x(p.starting_salary), cy = y(p.raise_pct);
      const title = '<title>'+p.tier+' · '+fmtDollar(p.starting_salary)+' · '+fmtPct(p.raise_pct)+(off?' (off scale)':'')+'</title>';
      svg += off
        ? '<rect x="'+(cx-3.5)+'" y="'+(cy-3.5)+'" width="7" height="7" transform="rotate(45 '+cx+' '+cy+')" fill="none" stroke="'+tierColor(p.tier)+'" stroke-width="1.5">'+title+'</rect>'
        : '<circle cx="'+cx+'" cy="'+cy+'" r="2.6" fill="'+tierColor(p.tier)+'" fill-opacity="0.75">'+title+'</circle>';
    });

    svg += '</svg>';
    const note = offScale.length
      ? '<div style="font-size:10.5px;color:var(--text-muted);margin-top:2px;">'+offScale.length+' point'+(offScale.length===1?'':'s')+' outside the typical range shown as a hollow diamond at the edge, actual value in its tooltip (largest: '+fmtPct(Math.max(...offScale.map(p=>Math.abs(p.raise_pct))) * (offScale.find(p=>Math.abs(p.raise_pct)===Math.max(...offScale.map(q=>Math.abs(q.raise_pct))))?.raise_pct < 0 ? -1 : 1))+').</div>'
      : '';
    return svg + note;
  }

  function legend(pc){
    const tiersUsed = Array.from(new Set((pc.points||[]).map(p=>p.tier))).sort();
    return '<div class="legend" style="margin-top:6px;">' + tiersUsed.map(t =>
      '<span class="legend-item"><span class="legend-swatch" style="background:'+tierColor(t)+';"></span>'+t+'</span>'
    ).join('') + '</div>';
  }

  function tierTable(pc){
    const rows = (pc.by_tier || []).map(t =>
      '<tr><td>'+t.tier+'</td><td class="num">'+t.n+'</td>' +
      '<td class="num">'+(t.corr!=null?t.corr.toFixed(2):'–')+'</td>' +
      '<td class="num">'+fmtDollar(t.min_salary)+' – '+fmtDollar(t.max_salary)+'</td>' +
      '<td class="num">'+fmtPct(t.bottom_third_avg_pct)+'</td>' +
      '<td class="num">'+fmtPct(t.top_third_avg_pct)+'</td>' +
      '<td class="num"'+(t.top_third_at_zero>0?' style="color:var(--accent-out);"':'')+'>'+t.top_third_at_zero+' / '+t.top_third_n+'</td></tr>'
    ).join('');
    return '<table class="decrease-table" style="margin-top:10px;font-size:12px;">' +
      '<thead><tr><th>Tier</th><th style="text-align:right">People</th><th style="text-align:right">Correlation</th><th style="text-align:right">Starting-salary range</th>' +
      '<th style="text-align:right">Bottom-third avg raise</th><th style="text-align:right">Top-third avg raise</th><th style="text-align:right">Top-third at ~0%</th></tr></thead>' +
      '<tbody>'+rows+'</tbody></table>';
  }

  wrap.innerHTML = years.map(pc => {
    const corrLabel = pc.overall_corr == null ? '–' : pc.overall_corr.toFixed(2);
    // Read off the by-tier correlations, not the pooled overall_corr: pooling
    // people across tiers with very different pay levels dilutes a real
    // within-tier effect (each tier has its own intercept), so the honest
    // per-tier evidence can show clear compression even when the naive
    // pooled number looks closer to flat.
    const tierCorrs = (pc.by_tier || []).map(t => t.corr).filter(c => c != null);
    const negCount = tierCorrs.filter(c => c <= -0.15).length;
    const readLabel = tierCorrs.length === 0 ? '–'
      : (negCount >= Math.ceil(tierCorrs.length / 2) ? 'compression in most tiers' : 'flat - no consistent relationship');
    return '<div class="raise-year-card">' +
      '<div class="raise-year-top">' +
        '<span class="raise-year-title">'+pc.year+'</span>' +
        '<span class="raise-year-transition">'+fmtMonth(pc.from_month)+' → '+fmtMonth(pc.to_month)+' · n='+pc.overall_n+'</span>' +
      '</div>' +
      '<div class="raise-stat-row">' +
        '<div class="raise-stat"><span class="raise-stat-label">Overall correlation</span><span class="raise-stat-value">'+corrLabel+'</span></div>' +
        '<div class="raise-stat"><span class="raise-stat-label">Reading</span><span class="raise-stat-value" style="font-size:12.5px;">'+readLabel+'</span></div>' +
      '</div>' +
      drawScatter(pc) +
      legend(pc) +
      tierTable(pc) +
    '</div>';
  }).join('');

  if (!years.length) {
    wrap.innerHTML = '<div style="font-size:13px;color:var(--text-muted);">No pay-compression data available for this pull.</div>';
  }
})();
