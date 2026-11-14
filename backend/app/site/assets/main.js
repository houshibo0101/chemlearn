(function () {
  const nav = document.getElementById('nav')
  const toggle = document.getElementById('navToggle')
  const year = document.getElementById('year')

  if (year) year.textContent = String(new Date().getFullYear())

  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      const open = nav.classList.toggle('open')
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false')
    })
    nav.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () {
        nav.classList.remove('open')
        toggle.setAttribute('aria-expanded', 'false')
      })
    })
  }

  const items = document.querySelectorAll('.reveal')
  if (!('IntersectionObserver' in window)) {
    items.forEach(function (item) { item.classList.add('visible') })
    return
  }

  const observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible')
        observer.unobserve(entry.target)
      }
    })
  }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' })

  items.forEach(function (item) { observer.observe(item) })
})()
