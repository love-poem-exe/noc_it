// Deterministic unique 3px border for every <div> to help identify elements
// Uses a stable CSS-path hash so the same element gets the same color across reloads.
(function () {
  function cssPath(el) {
    if (!el || el.nodeType !== 1) return ''
    const segments = []
    while (el && el.nodeType === 1 && el.tagName.toLowerCase() !== 'html') {
      const tag = el.tagName.toLowerCase()
      let idx = 1
      let sib = el.previousElementSibling
      while (sib) {
        if (sib.tagName && sib.tagName.toLowerCase() === tag) idx++
        sib = sib.previousElementSibling
      }
      segments.unshift(`${tag}:nth-of-type(${idx})`)
      el = el.parentElement
    }
    return segments.join('>')
  }

  function djb2(str) {
    let hash = 5381
    for (let i = 0; i < str.length; i++) {
      hash = ((hash << 5) + hash) + str.charCodeAt(i) // hash * 33 + c
      hash = hash & 0xffffffff
    }
    return Math.abs(hash)
  }

  function colorForPath(path) {
    const h = djb2(path) % 360
    const s = 70
    const l = 45
    return `hsl(${h} ${s}% ${l}%)`
  }

  function applyToDiv(div) {
    try {
      if (!div || div.dataset.__divBorderApplied) return
      const path = cssPath(div) || (div.id ? `#${div.id}` : div.className || div.tagName.toLowerCase())
      const color = colorForPath(path)
      // Use solid border to be visible regardless of background
      div.style.boxSizing = 'border-box'
      div.style.outline = `3px solid ${color}`
      div.dataset.__divBorderColor = color
      div.dataset.__divBorderApplied = '1'
    } catch (e) {
      // noop
    }
  }

  function applyToAllExisting() {
    const divs = document.querySelectorAll('div')
    for (const d of divs) applyToDiv(d)
  }

  // Observe DOM additions to apply to new divs as well (keeps borders consistent)
  function observeMutations() {
    try {
      const mo = new MutationObserver((mutations) => {
        for (const m of mutations) {
          if (m.type === 'childList') {
            for (const node of m.addedNodes) {
              if (!node) continue
              if (node.nodeType !== 1) continue
              if (node.tagName && node.tagName.toLowerCase() === 'div') applyToDiv(node)
              const inner = node.querySelectorAll && node.querySelectorAll('div')
              if (inner && inner.length) for (const d of inner) applyToDiv(d)
            }
          }
        }
      })
      mo.observe(document.documentElement || document.body, { childList: true, subtree: true })
    } catch (e) {
      // noop
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      applyToAllExisting()
      observeMutations()
    })
  } else {
    applyToAllExisting()
    observeMutations()
  }

})()
