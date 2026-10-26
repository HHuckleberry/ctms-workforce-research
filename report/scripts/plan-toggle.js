// ---------- Shared DC / DL / Both pay-plan toggle ----------
// One state for the whole report: every mounted toggle stays in sync, and
// any section can subscribe to re-render when the plan changes.
const PlanToggle = (function(){
  const OPTIONS = [['ALL', 'Both'], ['DC', 'DC'], ['DL', 'DL']];
  let current = 'ALL';
  const listeners = [];
  const mounts = [];

  function paint(){
    mounts.forEach(el => el.querySelectorAll('button').forEach(b =>
      b.classList.toggle('active', b.dataset.plan === current)));
  }
  function set(plan){
    if (plan === current) return;
    current = plan;
    paint();
    listeners.forEach(fn => fn(current));
  }
  function mount(el){
    if (!el) return;
    el.classList.add('plan-toggle');
    el.innerHTML = '<span class="plan-toggle-label">Pay plan:</span>' + OPTIONS.map(([v, label]) =>
      '<button type="button" class="tag-filter-btn" data-plan="'+v+'">'+label+'</button>').join('');
    el.querySelectorAll('button').forEach(b => b.addEventListener('click', () => set(b.dataset.plan)));
    mounts.push(el);
    paint();
  }
  function subscribe(fn){ listeners.push(fn); }
  return { get: () => current, set, mount, subscribe };
})();
