// ---------- Tabs ----------
const Tabs = (function(){
  const ids = ['overview', 'raises', 'locality', 'individuals'];
  const btns = {}, panels = {};
  ids.forEach(id => {
    btns[id] = document.getElementById('tabbtn-' + id);
    panels[id] = document.getElementById('tab-' + id);
    btns[id].addEventListener('click', () => show(id));
  });
  document.getElementById('tab-individuals-count').textContent = '(' + (DATA.people_table||[]).length + ')';

  function show(which){
    ids.forEach(id => {
      const active = id === which;
      panels[id].hidden = !active;
      btns[id].classList.toggle('active', active);
      btns[id].setAttribute('aria-selected', active);
    });
  }
  return { show };
})();

