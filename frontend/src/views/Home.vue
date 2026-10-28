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
    <div>
      <small>JUEGA A· ONE TO FOUR</small>
      <h1>¿Cuánto<br><em>sabes?</em></h1>
      <p>Pon a prueba tus conocimientos. Cuatro opciones, una respuesta correcta y una nueva partida cada vez.</p>

      <form class="card" @submit.prevent="empezar">
        <label>Nombre del jugador
          <input v-model="jugador" maxlength="30" placeholder="Ej. Javi" required>
        </label>
        <button class="primary">Empezar partida · 10 preguntas <span>→</span></button>
      </form>
    </div>

    <div class="visual">
      <strong>1</strong><i>/</i><strong>4</strong>
      <p>Una pregunta.<br>Cuatro posibilidades.</p>
    </div>
  </section>
</template>
