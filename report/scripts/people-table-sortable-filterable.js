// ---------- People table (sortable + filterable) ----------
const PeopleTable = (function(){
  const raw = DATA.people_table || [];
  const rows = raw.map(p => ({
    ...p,
    plan: p.start_plan === p.end_plan ? p.start_plan : (p.start_plan + ' → ' + p.end_plan),
    status_sort: p.active ? '0' : '1-' + (p.last_seen||''),
    status_label: p.active ? 'Active' : ('Left ' + fmtMonth(p.last_seen)),
    notes_sort: (p.promoted?'0':'1') + (p.supervisor?'0':'1'),
  }));

  let sortKey = 'joined', sortType = 'str', sortDir = 'asc';
  let filter = null; // {conditions: [{field, value}], label}

  function cmp(a, b){
    let av = a[sortKey], bv = b[sortKey];
    if (av == null && bv == null) return 0;
    if (av == null) return 1;
    if (bv == null) return -1;
    if (sortType === 'num') { av = Number(av); bv = Number(bv); }
    if (av < bv) return sortDir === 'asc' ? -1 : 1;
    if (av > bv) return sortDir === 'asc' ? 1 : -1;
    return 0;
  }

  let searchText = '';

  function filteredRows(){
    let out = rows;
    if (filter) {
      out = filter.ids
        ? out.filter(r => filter.ids.has(r.id))
        : out.filter(r => filter.conditions.every(c => r[c.field] === c.value));
    }
    if (searchText) {
      const q = searchText.toLowerCase();
      out = out.filter(r =>
        (r.duty_station||'').toLowerCase().includes(q) ||
        (r.latest_duty_station||'').toLowerCase().includes(q) ||
        (r.subelement||'').toLowerCase().includes(q) ||
        (r.cohort||'').toLowerCase().includes(q) ||
        (r.education_bracket||'').toLowerCase().includes(q) ||
        (r.how_left||'').toLowerCase().includes(q) ||
        (r.plan||'').toLowerCase().includes(q)
        || (r.rate_tier||'').toLowerCase().includes(q)
      );
    }
    return out;
  }

  function renderFilterBar(){
    const bar = document.getElementById('filter-bar');
    if (!filter) { bar.innerHTML = ''; return; }
    const n = filteredRows().length;
    bar.innerHTML =
      '<span class="filter-chip">'+filter.label+'<button type="button" id="clear-filter-btn">×</button></span>' +
      '<span class="filter-count">'+n+' '+(n===1?'person':'people')+'</span>';
    document.getElementById('clear-filter-btn').addEventListener('click', clearFilter);
  }

  function sparkline(pid, active){
    const hist = (DATA.person_history[pid] || []).filter(h => h.sal != null);
    if (hist.length < 2) return '';
    const W=64,H=22,pad=2;
    const vals = hist.map(h=>h.sal);
    const lo = Math.min(...vals), hi = Math.max(...vals);
    const x = i => pad + (i/(hist.length-1))*(W-2*pad);
    const y = v => hi===lo ? H/2 : H-pad-((v-lo)/(hi-lo))*(H-2*pad);
    let d = 'M '+x(0)+' '+y(vals[0]);
    for (let i=1;i<vals.length;i++) d += ' L '+x(i)+' '+y(vals[i]);
    const stroke = active ? colorDC : colorMuted;
    return '<svg width="'+W+'" height="'+H+'" viewBox="0 0 '+W+' '+H+'" style="display:block;">' +
      '<path d="'+d+'" fill="none" stroke="'+stroke+'" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>' +
      '<circle cx="'+x(vals.length-1)+'" cy="'+y(vals[vals.length-1])+'" r="1.6" fill="'+stroke+'"/>' +
    '</svg>';
  }

  function render(){
    const sorted = filteredRows().slice().sort(cmp);
    const tbody = document.getElementById('people-tbody');
    tbody.innerHTML = sorted.map(r => {
      const badges = (r.promoted ? '<span class="mini-badge promoted">Promoted</span>' : '') +
                     (r.supervisor ? '<span class="mini-badge supervisor">Supervisor</span>' : '');
      const statusClass = r.active ? 'status-active' : 'status-left';
      const gapFlag = r.has_gap ? '<span title="This person\'s reconstructed timeline has a gap - a lower-confidence linkage. See methodology." style="color:var(--accent-out); cursor:help; margin-left:4px;">●</span>' : '';
      return '<tr data-id="'+r.id.replace(/"/g,'&quot;')+'">' +
        '<td class="num">'+r.rank+gapFlag+'</td>' +
        '<td>'+fmtMonth(r.joined)+'</td>' +
        '<td>'+r.cohort+'</td>' +
        '<td>'+r.duty_station+'</td>' +
        '<td>'+r.subelement+'</td>' +
        '<td class="num">'+(r.prior_years!=null ? r.prior_years+'y' : '–')+'</td>' +
        '<td>'+r.plan+'</td>' +
        '<td class="num">'+(r.start_salary!=null ? fmtDollar(r.start_salary) : '–')+'</td>' +
        '<td class="num">'+(r.end_salary!=null ? fmtDollar(r.end_salary) : '–')+'</td>' +
        '<td class="num">'+(r.pct_change!=null ? fmtPct(r.pct_change) : '–')+'</td>' +
        '<td>'+sparkline(r.id, r.active)+'</td>' +
        '<td class="'+statusClass+'">'+r.status_label+'</td>' +
        '<td>'+(badges || '–')+'</td>' +
      '</tr>';
    }).join('');
    tbody.querySelectorAll('tr').forEach(tr => {
      tr.addEventListener('click', () => PersonModal.open(tr.dataset.id));
    });
    const countEl = document.getElementById('people-result-count');
    if (countEl) countEl.textContent = sorted.length + ' shown';
  }

  function applyFilter(field, value, label, extraConditions){
    filter = { conditions: [{field, value}].concat(extraConditions||[]), label };
    renderFilterBar();
    render();
    Tabs.show('individuals');
  }
  function applyIdFilter(ids, label){
    filter = { ids: new Set(ids), label };
    renderFilterBar();
    render();
    Tabs.show('individuals');
  }
  function clearFilter(){
    filter = null;
    renderFilterBar();
    render();
  }
  function setSearch(text){
    searchText = text;
    render();
  }

  document.querySelectorAll('#people-table th[data-key]').forEach(th => {
    th.addEventListener('click', () => {
      const key = th.dataset.key, type = th.dataset.type;
      if (sortKey === key) {
        sortDir = sortDir === 'asc' ? 'desc' : 'asc';
      } else {
        sortKey = key; sortType = type;
        sortDir = type === 'num' ? 'desc' : 'asc';
      }
      document.querySelectorAll('#people-table th').forEach(h => { h.classList.remove('sort-active'); h.removeAttribute('data-dir'); });
      th.classList.add('sort-active'); th.setAttribute('data-dir', sortDir);
      render();
    });
  });

  document.getElementById('people-search').addEventListener('input', (e) => setSearch(e.target.value));

  // CSV export via the artifact "downloads" capability - script-driven file
  // saves are otherwise blocked in a published artifact, so this is the only
  // working path for an in-page export button.
  (async () => {
    const btn = document.getElementById('export-csv-btn');
    let cap = null;
    try {
      if (window.claude && typeof window.claude.use === 'function') cap = await window.claude.use('downloads');
    } catch (e) { cap = null; }
    if (!cap) { btn.disabled = true; btn.title = 'Export isn’t available in this view'; return; }
    btn.addEventListener('click', async () => {
      const cols = ['rank','joined','cohort','duty_station','latest_duty_station','subelement','prior_years','plan','start_salary','end_salary','pct_change','status_label','how_left'];
      const csvRows = filteredRows().slice().sort(cmp);
      const escape = v => { if (v==null) v=''; v=String(v).replace(/"/g,'""'); return /[",\n]/.test(v) ? '"'+v+'"' : v; };
      const csv = [cols.join(',')].concat(csvRows.map(r => cols.map(c=>escape(r[c])).join(','))).join('\n');
      try { await cap.save({ filename: 'ctms_individuals' + (filter ? '_filtered' : '') + '.csv', data: csv }); }
      catch (e) { /* viewer declined the save - nothing to do */ }
    });
  })();

  render();
  return { applyFilter, applyIdFilter, clearFilter, setSearch, rows };
})();

