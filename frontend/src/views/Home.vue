<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { getPlayer, setPlayer } from '../services/api'

const router = useRouter()
const jugador = ref(getPlayer())

function empezar() {
  setPlayer(jugador.value.trim() || 'Jugador')
  router.push('/agente')
}
</script>

<template>
  <section class="home page">
    <div class="home-main">
      <h1>¿Cuánto<br>sabes?</h1>
      <p class="home-lead">Cuatro opciones, una respuesta correcta y preguntas nuevas en cada partida.</p>

      <form class="card" @submit.prevent="empezar">
        <label>Nombre del jugador
          <input v-model="jugador" maxlength="30" placeholder="Ej. Javi" autocomplete="nickname" required>
        </label>
        <button class="primary">Empezar partida</button>
        <p class="form-hint">10 preguntas y 15 segundos para responder cada una.</p>
      </form>
    </div>

    <div class="visual">
      <div class="board" aria-hidden="true">
        <span class="tile">A</span>
        <span class="tile">B</span>
        <span class="tile lit">C</span>
        <span class="tile">D</span>
      </div>
      <p>Una pregunta.<br>Cuatro posibilidades.</p>
    </div>
  </section>
</template>
