// Learning Desk landing page. Everything here is progressive: with no script the page shows the first
// reel frame, all three showcase captions, and the sampling bars at temperature 1.
(() => {
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const phone = () => window.matchMedia('(max-width: 640px)').matches;
  const stackedHero = () => window.matchMedia('(max-width: 900px)').matches;

  // Reveal each part of a section once, as it enters. Never leaves content hidden.
  const targets = document.querySelectorAll('[data-reveal]');
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver((entries) => {
      for (const e of entries) if (e.isIntersecting) { e.target.classList.add('is-in'); io.unobserve(e.target); }
    }, { rootMargin: '0px 0px -10% 0px', threshold: 0.1 });
    targets.forEach((el) => io.observe(el));
    addEventListener('load', () => setTimeout(() => targets.forEach((el) => {
      const r = el.getBoundingClientRect(); if (r.top < innerHeight && r.bottom > 0) el.classList.add('is-in');
    }), 2000));
  } else targets.forEach((el) => el.classList.add('is-in'));

  // Hero: the reel of lesson diagrams passes through the sentence while the words hold their place.
  const hero = document.querySelector('.hero');
  const track = document.querySelector('.reel__track');
  const frames = track ? [...track.children] : [];
  // Scroll progress (0..1) through a tall section whose stage is sticky.
  const progress = (el) => {
    const r = el.getBoundingClientRect();
    const run = el.offsetHeight - innerHeight;
    return run > 0 ? Math.min(1, Math.max(0, -r.top / run)) : 0;
  };
  function placeReel() {
    if (!track || reduce || stackedHero()) { if (track) track.style.transform = ''; return; }
    const h = frames[0].getBoundingClientRect().height;
    const step = h + 24;
    // The first frame is a sliver above the start; the reel runs from frame two to the last.
    const at = 1 + progress(hero) * (frames.length - 2);
    track.style.transform = `translateY(${-(h / 2) - at * step}px)`;
  }

  // Showcase: one lesson screen at three distances, switched by scroll position.
  const showcase = document.querySelector('.showcase');
  function placeShowcase() {
    if (!showcase) return;
    if (reduce || phone()) { showcase.dataset.stage = '1'; return; }
    const p = progress(showcase);
    showcase.dataset.stage = p < 0.3 ? '1' : p < 0.66 ? '2' : '3';
  }

  let ticking = false;
  const onScroll = () => {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => { placeReel(); placeShowcase(); ticking = false; });
  };
  addEventListener('scroll', onScroll, { passive: true });
  addEventListener('resize', onScroll);
  onScroll();

  // The live thing: the sampling lesson's own example. Same scores and arithmetic as the app.
  const logits = [['report', 3.1], ['results', 2.8], ['summary', 2.2], ['paper', 1.6],
                  ['code', 1.0], ['email', 0.6], ['poem', -0.4], ['banana', -2.2]];
  const softmax = (scores, t) => {
    if (t <= 0) { const best = scores.indexOf(Math.max(...scores)); return scores.map((_, i) => (i === best ? 1 : 0)); }
    const scaled = scores.map((s) => s / t);
    const top = Math.max(...scaled);
    const w = scaled.map((s) => Math.exp(s - top));
    const total = w.reduce((a, b) => a + b, 0);
    return w.map((x) => x / total);
  };
  const pct = (p) => (p > 0 && p < 0.005 ? 'under 1%' : `${Math.round(p * 100)}%`);
  const demo = document.querySelector('.live__demo');
  if (demo) {
    const slider = demo.querySelector('#temperature');
    const shown = demo.querySelector('#temperature-value');
    const word = demo.querySelector('#next-word');
    const rows = [...demo.querySelectorAll('.bars li')];
    let probs = softmax(logits.map((x) => x[1]), 1);
    const render = () => {
      const t = Number(slider.value);
      shown.textContent = t.toFixed(1);
      probs = softmax(logits.map((x) => x[1]), t);
      rows.forEach((li, i) => {
        li.style.setProperty('--w', `${(probs[i] * 100).toFixed(1)}%`);
        li.querySelector('.b-val').textContent = probs[i] ? pct(probs[i]) : 'never';
        li.classList.toggle('is-off', probs[i] === 0);
      });
    };
    slider.addEventListener('input', render);
    demo.querySelector('#draw').addEventListener('click', () => {
      let r = Math.random(), i = 0;
      for (; i < probs.length - 1; i++) { r -= probs[i]; if (r <= 0) break; }
      word.textContent = logits[i][0];
      word.classList.add('is-new');
      setTimeout(() => word.classList.remove('is-new'), 200);
    });
    render();
  }

  // Sources: one name at a time is lit in full ink.
  const names = [...document.querySelectorAll('.names li:not(.is-fixed)')];
  if (names.length && !reduce) {
    let i = 0;
    names[0].classList.add('is-lit');
    setInterval(() => {
      if (document.hidden) return;
      names[i].classList.remove('is-lit');
      i = (i + 1) % names.length;
      names[i].classList.add('is-lit');
    }, 2000);
  }
})();
