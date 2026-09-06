(() => {
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Cinematic boot sequence (first load per tab only).
  if (!sessionStorage.getItem('rsBooted') && !reduced) {
    const boot = document.createElement('div');
    boot.className = 'rs-boot';
    boot.innerHTML = `
      <div class="rs-boot-core">
        <div class="rs-boot-orb"></div>
        <div class="rs-boot-label">REPOSITORY OBSERVATORY INITIALIZATION</div>
        <div class="rs-boot-title">Calibrating the code field.</div>
        <div class="rs-boot-bar"><i></i></div>
        <div class="rs-boot-meta"><span>SIGNAL MAP / ONLINE</span><span>MODEL / EXPLAINABLE</span></div>
      </div>`;
    document.body.appendChild(boot);
    document.body.style.overflow = 'hidden';
    setTimeout(() => {
      boot.classList.add('done');
      document.body.style.overflow = '';
      sessionStorage.setItem('rsBooted', '1');
      setTimeout(() => boot.remove(), 800);
    }, 1850);
  }

  // Scroll progress telemetry.
  const progress = document.createElement('div');
  progress.className = 'rs-scroll-progress';
  document.body.appendChild(progress);
  const syncProgress = () => {
    const max = Math.max(1, document.documentElement.scrollHeight - innerHeight);
    progress.style.width = `${Math.min(100, (scrollY / max) * 100)}%`;
  };
  addEventListener('scroll', syncProgress, { passive: true });
  syncProgress();

  // Floating adaptive HUD.
  const hud = document.createElement('aside');
  hud.className = 'rs-hud';
  hud.innerHTML = `
    <div class="rs-hud-item"><small>FIELD SYNC</small><strong>99.4%</strong><i></i></div>
    <div class="rs-hud-item"><small>LATENCY</small><strong>LIVE</strong><i></i></div>
    <div class="rs-hud-item"><small>CONFIDENCE</small><strong>0.93</strong><i></i></div>`;
  document.body.appendChild(hud);

  // Telemetry rail under hero.
  const marquee = document.querySelector('.marquee');
  if (marquee) {
    const rail = document.createElement('section');
    rail.className = 'rs-telemetry reveal-ultra';
    rail.innerHTML = `
      <div class="lead"><small>LIVE OBSERVATORY FEED</small><strong>Repository state reconstructed continuously.</strong><p>Health, ownership and maintenance pressure are treated as one evolving engineering field.</p></div>
      <div><small>STRUCTURAL INDEX</small><strong>87.2</strong><span>stable / monitored</span></div>
      <div><small>OWNERSHIP ENTROPY</small><strong>0.41</strong><span>moderate concentration</span></div>
      <div><small>FLOW MOMENTUM</small><strong>+18%</strong><span>90-day activity</span></div>
      <div><small>ANOMALIES</small><strong>03</strong><span>explainable signals</span></div>`;
    marquee.insertAdjacentElement('afterend', rail);
  }

  // Observatory spectrum sweep + energy particles.
  const frame = document.querySelector('.observatory-frame');
  const stage = document.querySelector('.instrument-stage');
  if (frame && stage) {
    const beam = document.createElement('div');
    beam.className = 'rs-spectrum-beam';
    frame.appendChild(beam);
    ['one','two','three','four'].forEach(name => {
      const p = document.createElement('i');
      p.className = `rs-pulse ${name}`;
      stage.appendChild(p);
    });
  }

  // Animated architecture network behind system cards.
  const arch = document.querySelector('.architecture-grid');
  if (arch) {
    const network = document.createElement('div');
    network.className = 'rs-arch-network';
    network.innerHTML = `<svg viewBox="0 0 1200 280" preserveAspectRatio="none" aria-hidden="true">
      <path d="M145 130 C280 35 360 35 445 130 S610 225 745 130 S930 40 1055 130"/>
      <path d="M145 160 C300 245 350 240 445 160 S620 70 745 160 S900 245 1055 160"/>
    </svg>`;
    arch.prepend(network);
  }

  // Scientific portals around major sections.
  ['.principles','.compare-section','.architecture-section'].forEach(sel => {
    const section = document.querySelector(sel);
    if (section) {
      const portal = document.createElement('div');
      portal.className = 'rs-portal';
      section.appendChild(portal);
    }
  });

  // High-end reveal system.
  const revealTargets = document.querySelectorAll('.principles,.principle-grid article,.compare-section,.architecture-section,.architecture-grid article,.panel,.rs-telemetry');
  if (!reduced && 'IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.11, rootMargin: '0px 0px -35px 0px' });
    revealTargets.forEach((el, i) => {
      el.classList.add('reveal-ultra');
      el.style.transitionDelay = `${Math.min(i % 4, 3) * 70}ms`;
      observer.observe(el);
    });
  } else {
    revealTargets.forEach(el => el.classList.add('is-visible'));
  }

  // Magnetic high-value buttons.
  if (!reduced) {
    document.querySelectorAll('.primary-btn,.ghost-btn,.ai-btn').forEach(btn => {
      btn.classList.add('rs-magnetic');
      btn.addEventListener('pointermove', e => {
        const r = btn.getBoundingClientRect();
        const x = (e.clientX - r.left - r.width / 2) * 0.14;
        const y = (e.clientY - r.top - r.height / 2) * 0.14;
        btn.style.transform = `translate(${x}px,${y}px)`;
      });
      btn.addEventListener('pointerleave', () => { btn.style.transform = ''; });
    });
  }

  // Card light field tracks pointer position.
  document.querySelectorAll('.panel,.principle-grid article,.architecture-grid article').forEach(card => {
    card.addEventListener('pointermove', e => {
      const r = card.getBoundingClientRect();
      card.style.setProperty('--rsx', `${((e.clientX-r.left)/r.width)*100}%`);
      card.style.setProperty('--rsy', `${((e.clientY-r.top)/r.height)*100}%`);
    });
  });

  // Make HUD values feel alive without implying real metrics.
  if (!reduced) {
    const sync = hud.querySelectorAll('strong')[0];
    const confidence = hud.querySelectorAll('strong')[2];
    let tick = 0;
    setInterval(() => {
      tick += 1;
      sync.textContent = `${(99.1 + Math.sin(tick/2)*0.35).toFixed(1)}%`;
      confidence.textContent = (0.92 + Math.sin(tick/3)*0.015).toFixed(2);
    }, 1600);
  }
})();
