const DATA = __DATA_JSON__;

function fmtMonth(ym) {
  const [y, m] = ym.split('-');
  const names = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  return names[parseInt(m,10)-1] + " '" + y.slice(2);
}
function previousMonth(ym) {
  const [y, m] = ym.split('-').map(Number);
  const d = new Date(Date.UTC(y, m - 2, 1));
  return d.getUTCFullYear() + '-' + String(d.getUTCMonth() + 1).padStart(2, '0');
}
function firstObservedLabel(ym) {
  if (ym === DATA.coverage.first) return fmtMonth(ym) + ' (present at coverage start)';
  return fmtMonth(ym) + ' (after the ' + fmtMonth(previousMonth(ym)) + ' snapshot)';
}
function fmtDollar(n) { return '$' + Math.round(n).toLocaleString('en-US'); }
function fmtPct(n, digits) { digits = digits === undefined ? 1 : digits; const s = n.toFixed(digits); return (n>0?'+':'') + s + '%'; }

