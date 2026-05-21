<template>
  <Main />
</template>

<script setup>
import Main from './Main.vue'
import { onMounted } from 'vue'

const FONT_KEY = 'noc-it:font-size'
const DEFAULT_SIZE = 13

function applyFontSize(px) {
  const scale = px / 13
  const app = document.getElementById('app')
  app.style.transformOrigin = '0 0'
  app.style.transform = `scale(${scale})`
  app.style.width  = (100 / scale) + 'vw'
  app.style.height = (100 / scale) + 'vh'
}

onMounted(() => {
  const saved = localStorage.getItem(FONT_KEY)
  applyFontSize(saved ? parseInt(saved, 10) : DEFAULT_SIZE)
  // sync across tabs
  window.addEventListener('storage', (e) => {
    if (e.key === FONT_KEY && e.newValue) applyFontSize(parseInt(e.newValue, 10))
  })
})
</script>

<style>
*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html, body {
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background: #1c1f24;
}

#app {
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background: #1c1f24;
  color: #e5e7eb;
  font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
  font-size: 13px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}

::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-track { background: #1c1f24; }
::-webkit-scrollbar-thumb { background: #323841; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #3d444e; }

button { cursor: pointer; font-family: inherit; }
input  { font-family: inherit; }
</style>
