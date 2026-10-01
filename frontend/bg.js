// Animated network-graph background: drifting nodes, hub-and-spoke links, mouse highlight.
(() => {
  const canvas = document.getElementById('bg-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const PALETTE = ['#2bb7a0', '#4a7be0', '#8b5cf6', '#f2b872', '#2bb7a0', '#4a7be0'];
  const HUB_COLORS = ['#4a7be0', '#8b5cf6', '#ff7a1a', '#2bb7a0'];
  let w = 0, h = 0, dpr = 1, nodes = [], hubs = [];
  const mouse = { x: -9999, y: -9999 };

  const rand = (a, b) => a + Math.random() * (b - a);

  function build() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    w = window.innerWidth; h = window.innerHeight;
    canvas.width = w * dpr; canvas.height = h * dpr;
    canvas.style.width = `${w}px`; canvas.style.height = `${h}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const count = Math.round(Math.min(150, Math.max(60, (w * h) / 11000)));
    const hubCount = Math.max(4, Math.round(count / 24));
    nodes = [];
    hubs = [];
    for (let i = 0; i < hubCount; i++) {
      const n = { x: rand(0, w), y: rand(0, h), vx: rand(-0.08, 0.08), vy: rand(-0.08, 0.08), r: rand(8, 13), c: HUB_COLORS[i % HUB_COLORS.length], hub: true, ph: rand(0, 6.28) };
      nodes.push(n); hubs.push(n);
    }
    for (let i = hubCount; i < count; i++) {
      nodes.push({ x: rand(0, w), y: rand(0, h), vx: rand(-0.18, 0.18), vy: rand(-0.18, 0.18), r: rand(2.4, 4.4), c: PALETTE[Math.floor(rand(0, PALETTE.length))], hub: false, ph: rand(0, 6.28) });
    }
    // each small node spokes to its nearest hub (hub-and-spoke look)
    nodes.forEach((n) => {
      if (n.hub) return;
      let best = null, bd = Infinity;
      hubs.forEach((hb) => { const d = (hb.x - n.x) ** 2 + (hb.y - n.y) ** 2; if (d < bd) { bd = d; best = hb; } });
      n.hubRef = best;
    });
  }

  function step(t) {
    ctx.clearRect(0, 0, w, h);
    // links: node → hub (faint), plus near-neighbour links
    ctx.lineWidth = 1;
    for (let i = 0; i < nodes.length; i++) {
      const a = nodes[i];
      if (a.hubRef) {
        const d = Math.hypot(a.x - a.hubRef.x, a.y - a.hubRef.y);
        const alpha = Math.max(0.05, 0.5 - d / 2200);
        ctx.strokeStyle = hexA(a.hubRef.c, alpha);
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(a.hubRef.x, a.hubRef.y); ctx.stroke();
      }
      for (let j = i + 1; j < nodes.length; j++) {
        const b = nodes[j];
        const d = Math.hypot(a.x - b.x, a.y - b.y);
        if (d < 130) {
          ctx.strokeStyle = hexA('#8b5cf6', (1 - d / 130) * 0.45);
          ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
        }
      }
      // mouse highlight
      const md = Math.hypot(a.x - mouse.x, a.y - mouse.y);
      if (md < 160) {
        ctx.strokeStyle = hexA('#ff7a1a', (1 - md / 160) * 0.55);
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(mouse.x, mouse.y); ctx.stroke();
      }
    }
    // nodes
    for (const n of nodes) {
      if (!reduced) {
        n.x += n.vx; n.y += n.vy;
        if (n.x < -20 || n.x > w + 20) n.vx *= -1;
        if (n.y < -20 || n.y > h + 20) n.vy *= -1;
      }
      const pulse = n.hub ? 1 + 0.12 * Math.sin(t / 900 + n.ph) : 1;
      if (n.hub) {
        const g = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, n.r * 5 * pulse);
        g.addColorStop(0, hexA(n.c, 0.5)); g.addColorStop(1, hexA(n.c, 0));
        ctx.fillStyle = g; ctx.beginPath(); ctx.arc(n.x, n.y, n.r * 5 * pulse, 0, 6.283); ctx.fill();
      }
      ctx.fillStyle = hexA(n.c, n.hub ? 1 : 0.9);
      ctx.beginPath(); ctx.arc(n.x, n.y, n.r * pulse, 0, 6.283); ctx.fill();
    }
    if (!reduced) raf = requestAnimationFrame(step);
  }

  function hexA(hex, a) {
    const v = parseInt(hex.slice(1), 16);
    return `rgba(${v >> 16}, ${(v >> 8) & 255}, ${v & 255}, ${a})`;
  }

  let raf = 0;
  const start = () => { cancelAnimationFrame(raf); build(); raf = requestAnimationFrame(step); };
  window.addEventListener('resize', start);
  window.addEventListener('mousemove', (e) => { mouse.x = e.clientX; mouse.y = e.clientY; });
  window.addEventListener('mouseleave', () => { mouse.x = mouse.y = -9999; });
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) cancelAnimationFrame(raf); else if (!reduced) raf = requestAnimationFrame(step);
  });
  start();
})();
