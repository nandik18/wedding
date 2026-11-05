(() => {
  'use strict';
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const navbar = document.querySelector('.navbar');
  const updateNav = () => navbar?.classList.toggle('scrolled', window.scrollY > 30);
  window.addEventListener('scroll', updateNav, {passive:true}); updateNav();
  const revealElements = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window && !reducedMotion) {
    const observer = new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting) { entry.target.classList.add('visible'); observer.unobserve(entry.target); }
    }), {threshold:0.08, rootMargin:'0px 0px -25px 0px'});
    revealElements.forEach(el => observer.observe(el));
  } else revealElements.forEach(el => el.classList.add('visible'));
  if (reducedMotion || !window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;
  document.querySelectorAll('.tilt-card').forEach(card => {
    card.addEventListener('pointermove', e => {
      const rect = card.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width - 0.5;
      const y = (e.clientY - rect.top) / rect.height - 0.5;
      card.style.transform = `perspective(1100px) rotateX(${-y * 6}deg) rotateY(${x * 6}deg) translateY(-4px)`;
    });
    card.addEventListener('pointerleave', () => {card.style.transform = '';});
    card.addEventListener('blur', () => {card.style.transform = '';});
  });
  const parallax = [...document.querySelectorAll('[data-parallax]')];
  let scheduled = false;
  const paint = () => {
    parallax.forEach(el => {
      const section = el.parentElement.getBoundingClientRect();
      if(section.bottom < 0 || section.top > innerHeight) return;
      const offset = ((section.top + section.height / 2) - innerHeight / 2) * Number(el.dataset.parallax);
      el.style.transform = `scale(1.12) translate3d(0, ${Math.max(-90, Math.min(90, -offset))}px, 0)`;
    });
    scheduled = false;
  };
  window.addEventListener('scroll', () => {if(!scheduled){scheduled=true;requestAnimationFrame(paint);}}, {passive:true});
  paint();
})();
