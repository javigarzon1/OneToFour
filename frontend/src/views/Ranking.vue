<script setup>
import { onMounted, ref } from 'vue'
import { getRanking } from '../services/api'

const ranking = ref([])
const loading = ref(true)
const error = ref('')

async function loadRanking() {
  loading.value = true
  error.value = ''
  try {
    const data = await getRanking()
    ranking.value = Array.isArray(data) ? data : []
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'No se pudo cargar el ranking.'
  } finally {
    loading.value = false
  }
}

onMounted(loadRanking)
</script>

<template>
  <section class="ranking page">
    <div class="ranking-heading">
      <div>
        <small>CLASIFICACIÓN</small>
        <h1>Ranking</h1>
        <p>Los mejores resultados registrados.</p>
      </div>
      <div class="ranking-mark" aria-hidden="true">🏆</div>
    </div>

    <div v-if="loading" class="state" role="status">Cargando ranking…</div>

    <div v-else-if="error" class="state error-state" role="alert">
      <span class="state-icon" aria-hidden="true">!</span>
      <h2>No se pudo cargar el ranking</h2>
      <p>{{ error }}</p>
      <button class="primary retry-button" type="button" @click="loadRanking">Reintentar</button>
    </div>

    <div v-else-if="ranking.length === 0" class="state empty-state">
      <span class="state-icon" aria-hidden="true">✦</span>
      <h2>El podio está esperando</h2>
      <p>Aún no hay resultados registrados. ¡Juega una partida y estrena la clasificación!</p>
      <RouterLink class="primary ranking-cta" to="/">Jugar ahora <span>→</span></RouterLink>
    </div>

    <div v-else class="card rows">
      <div class="ranking-table-head">
        <span>Puesto</span><span>Jugador</span><span>Puntuación</span><span>Precisión</span>
      </div>
      <div v-for="(x, i) in ranking" :key="x.jugador + '-' + i" class="row" :class="{ 'podium-row': i < 3 }">
        <b class="rank-position" :class="'rank-' + (i + 1)">
          <span v-if="i === 0" aria-label="Primer puesto">♛</span>
          <span v-else-if="i === 1" aria-label="Segundo puesto">Ⅱ</span>
          <span v-else-if="i === 2" aria-label="Tercer puesto">Ⅲ</span>
          <span v-else>{{ i + 1 }}</span>
        </b>
        <strong class="rank-player">{{ x.jugador }}</strong>
        <span class="rank-points">{{ x.puntuacion }} <small>pts</small></span>
        <span class="rank-percent">{{ x.porcentaje }}%</span>
      </div>
    </div>
  </section>
</template>
