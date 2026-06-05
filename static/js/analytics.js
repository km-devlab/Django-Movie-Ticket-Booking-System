document.addEventListener('DOMContentLoaded', function() {
  const root = document.documentElement;
  document.addEventListener('mousemove', function(e) {
    const x = e.clientX + 'px';
    const y = e.clientY + 'px';
    root.style.setProperty('--mouse-x', x);
    root.style.setProperty('--mouse-y', y);
  });
});
