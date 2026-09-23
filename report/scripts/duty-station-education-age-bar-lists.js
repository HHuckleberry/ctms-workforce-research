// ---------- Duty station / education / age bar lists ----------
function titleCaseLabel(label){ return label.split(' ').map(w=>w? w[0]+w.slice(1).toLowerCase():w).join(' '); }
function renderSimpleBarList(elId, obj, color, filterField, opts){
  opts = opts || {};
  const entries = Object.entries(obj).sort((a,b)=>b[1]-a[1]);
  const max = entries[0][1];
  const el = document.getElementById(elId);
  entries.forEach(([rawLabel,val])=>{
    const display = opts.rawLabels ? rawLabel : titleCaseLabel(rawLabel);
    const row = document.createElement('div'); row.className='bar-row' + (filterField ? ' drillable' : '');
    row.innerHTML = '<span class="bl-label" title="'+rawLabel+'">'+display+'</span>'+
      '<span class="bl-track"><span class="bl-fill" style="width:'+(val/max*100)+'%; background:'+color+'"></span></span>'+
      '<span class="bl-val">'+val+'</span>';
    if (filterField) row.addEventListener('click', () => PeopleTable.applyFilter(filterField, rawLabel, display + ' (' + filterField.replace(/_/g,' ') + ', currently active)', [{field:'active', value:true}]));
    el.appendChild(row);
  });
}
renderSimpleBarList('duty-list', DATA.duty_station_top, colorDC, 'latest_duty_station', {rawLabels:true});
renderSimpleBarList('edu-list', DATA.education_latest, colorDL, 'education_bracket');
renderSimpleBarList('age-list', DATA.age_latest, colorDC, 'age_bracket', {rawLabels:true});
document.getElementById('composition-heading').textContent = "Who's still here — " + fmtMonth(DATA.coverage.last) + ' snapshot';
document.getElementById('composition-sub').textContent = DATA.latest_headcount + ' people. Where they work, and how the cohort is educated.';

document.getElementById('generated-line').textContent = 'Report generated ' + new Date(DATA.generated).toUTCString() + '.';
document.getElementById('print-btn').addEventListener('click', () => window.print());
document.getElementById('tracking-result').textContent =
  'Result: ' + DATA.summary.total_tracked_individuals + ' tracked individuals from ' + DATA.summary.raw_keys_before_linking +
  ' raw keys; ' + DATA.summary.people_with_gap_in_timeline + ' still show a gap in their monthly timeline, meaning the linkage is a best estimate, not ground truth.';

