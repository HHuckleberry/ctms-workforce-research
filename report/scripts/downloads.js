// ---------- Full-dataset downloads ----------
// DATA.downloads is written by run.py at build time from the files it copies
// into report/data/, so names, row counts and sizes always match what ships.
(function downloads(){
  const files = DATA.downloads || [];
  const fmtSize = b => b >= 1e6 ? (b / 1e6).toFixed(1) + ' MB' : Math.max(1, Math.round(b / 1e3)) + ' KB';
  const shape = f => f.rows != null ? f.rows.toLocaleString() + ' rows × ' + f.columns + ' columns · ' : '';
  const dictionary = '<a href="https://data.opm.gov/data-standards/ehri-data-standards" target="_blank" rel="noopener">OPM\'s EHRI data standards</a>';

  document.querySelectorAll('.downloads-list').forEach(el => {
    if (!files.length) { el.innerHTML = '<div class="chart-foot">No download files were built with this report.</div>'; return; }
    el.innerHTML = files.map(f =>
      '<div class="download-row">' +
        '<a class="export-btn header-link" style="margin-left:0;" href="data/' + f.file + '" download>' + f.file + '</a>' +
        '<div><div class="download-desc">' + f.description + '</div>' +
        '<div class="chart-foot" style="margin-top:2px;">' + shape(f) + fmtSize(f.bytes) + '</div></div>' +
      '</div>'
    ).join('') +
    '<p class="chart-foot" style="margin-top:12px;">Field definitions: ' + dictionary + '. <code>person_id</code> is this report\'s reconstructed link between months (see methodology), not an OPM field.</p>';
  });

  document.querySelectorAll('.downloads-inline').forEach(el => {
    el.innerHTML = files.length
      ? files.map(f => '<a href="data/' + f.file + '" download>' + f.file + '</a>').join(' &middot; ') +
        '. <code>ctms_person_months.csv</code> carries every OPM field for every person-month; field definitions follow ' + dictionary + '.'
      : 'No download files were built with this report.';
  });
})();
