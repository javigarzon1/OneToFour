<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const score = computed(() => Number(route.query.score || 0))
const total = computed(() => Number(route.query.total || 0))
const percent = computed(() => Number(route.query.porcentaje || 0))
const player = computed(() => route.query.jugador || 'Jugador')
const streak = computed(() => Number(route.query.racha || 0))
const message = computed(() =>
  percent.value === 100 ? '¡Partida perfecta!'
    : percent.value >= 70 ? '¡Gran partida!'
      : percent.value >= 50 ? '¡Buen trabajo!'
        : 'Sigue practicando.',
)
</script>

<template>
  <section class="results page">
    <div class="result">
      <h1>{{ message }}</h1>
      <p class="result-lead">{{ player }}, así ha ido tu partida de {{ total }} preguntas.</p>
      <div class="result-stats">
        <div class="result-main"><span>Puntos</span><strong>{{ score }}</strong></div>
        <div><span>Aciertos</span><strong>{{ percent }}<small>%</small></strong></div>
        <div><span>Mejor racha</span><strong>{{ streak }}</strong></div>
      </div>
      <div class="actions">
        <button class="primary" type="button" @click="router.push('/agente')">Jugar otra vez</button>
        <button class="secondary" type="button" @click="router.push('/ranking')">Ver ranking</button>
      </div>
    </div>
  </section>
</template>
