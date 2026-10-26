// ---------- Source cards and claim checks, rendered from DATA.sources / DATA.claim_checks ----------
(function accountabilityDynamic(){
  const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const statusText = {primary:'Primary-verified', secondary:'Secondary source', unverified:'Unverified'};
  const verdictText = {match:'Consistent', mismatch:'Differs', unverified:'Not verified', not_comparable:'Not comparable'};

  const grid = document.getElementById('acct-cards');
  if (grid) grid.innerHTML = (DATA.sources || []).map(s => {
    const link = s.link ? '<a href="'+esc(s.link.url)+'" target="_blank" rel="noopener" style="font-size:11.5px; color:var(--accent-dc);">'+esc(s.link.text)+' &#8594;</a>' : '';
    const foot = s.foot ? '<span style="font-size:11.5px; color:var(--text-muted);">'+esc(s.foot)+'</span>' : '';
    const caveat = s.caveat ? '<p style="font-size:12px; color:var(--text-muted); margin:0 0 10px;">'+esc(s.caveat)+'</p>' : '';
    const stale = s.stale ? ' &middot; <span title="Source is '+s.age_months+' months old">recheck</span>' : '';
    return '<div class="chart-card">'
      + '<div class="stat-label" style="margin-bottom:8px;">'+esc(s.label)+' <span style="font-weight:400;">&middot; '+statusText[s.status]+stale+'</span></div>'
      + '<p style="font-size:13.5px; line-height:1.6; margin:0 0 10px;">'+s.html+(s.context ? ' '+s.context : '')+'</p>'
      + caveat + link + foot + '</div>';
  }).join('');

  const tbody = document.getElementById('acct-claims-tbody');
  if (tbody) tbody.innerHTML = (DATA.claim_checks || []).map(c => {
    const num = v => v == null ? '&mdash;' : esc(typeof v === 'number' && !Number.isInteger(v) ? v.toFixed(1) : v);
    return '<tr><td>'+esc(c.source_label)+'</td><td>'+esc(c.claim)+'</td><td style="text-align:right">'+num(c.claim_value)+'</td>'
      + '<td>'+(c.observed_label ? esc(c.observed_label) : '&mdash;')+'</td><td style="text-align:right">'+num(c.observed)+'</td>'
      + '<td title="'+esc(c.note || '')+'">'+verdictText[c.verdict]+'</td></tr>';
  }).join('');
})();
