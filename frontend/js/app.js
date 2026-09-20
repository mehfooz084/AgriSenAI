function initNav() {
  const toggle = document.getElementById("nav-toggle");
  const menu = document.getElementById("nav-menu");
  const page = document.body.dataset.page;

  document.querySelectorAll("[data-nav]").forEach((link) => {
    if (link.dataset.nav === page) {
      link.classList.add("active");
    }
  });

  if (!toggle || !menu) return;

  toggle.addEventListener("click", () => {
    const open = menu.classList.toggle("hidden") === false;
    toggle.setAttribute("aria-expanded", String(open));
  });
}

document.addEventListener("DOMContentLoaded", initNav);
