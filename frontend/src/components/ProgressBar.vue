<script setup>
const props = defineProps({
  current: Number,
  total: Number,
  results: { type: Array, default: () => [] },
})

// Una celda por pregunta: acierto, fallo, la actual o pendiente.
function cellClass(n) {
  if (n <= props.results.length) return props.results[n - 1] ? 'hit' : 'miss'
  return n === props.current ? 'now' : ''
}
</script>

<template>
  <div
    class="progress-info"
    role="progressbar"
    aria-valuemin="1"
    :aria-valuemax="total"
    :aria-valuenow="current"
    :aria-valuetext="`Pregunta ${current} de ${total}`"
  >
    <span class="progress-label">Pregunta {{ current }} de {{ total }}</span>
    <div class="progress" aria-hidden="true">
      <i v-for="n in total" :key="n" :class="cellClass(n)"></i>
    </div>
  </div>
</template>
