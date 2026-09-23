// ---------- shared chart helpers ----------
function svgEl(tag, attrs) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const k in attrs) el.setAttribute(k, attrs[k]);
  return el;
}
function niceMax(v) { const m=[1,2,2.5,5,10]; let p=1; while(p<v) p*=10; p/=10; for(const f of m){ if(v<=p*f) return p*f*1; } return Math.ceil(v/p)*p; }
function autoStep(n, targetLabels) { targetLabels = targetLabels || 11; return Math.max(1, Math.round(n/targetLabels)); }
function monthLabelIndices(n, step) {
  const out=[]; for(let i=0;i<n;i+=step) out.push(i);
  if (out[out.length-1] < n-1-step*0.4) out.push(n-1);
  else out[out.length-1] = n-1;
  return out;
}

const colorDC = getComputedStyle(document.documentElement).getPropertyValue('--accent-dc').trim() || '#2a78d6';
const colorDL = getComputedStyle(document.documentElement).getPropertyValue('--accent-dl').trim() || '#eb6834';
const colorOut = getComputedStyle(document.documentElement).getPropertyValue('--accent-out').trim() || '#e34948';
const colorGrid = getComputedStyle(document.documentElement).getPropertyValue('--grid').trim() || '#e1e0d9';
const colorAxis = getComputedStyle(document.documentElement).getPropertyValue('--axis').trim() || '#c3c2b7';
const colorMuted = getComputedStyle(document.documentElement).getPropertyValue('--text-muted').trim() || '#898781';
const colorText = getComputedStyle(document.documentElement).getPropertyValue('--text-secondary').trim() || '#52514e';

