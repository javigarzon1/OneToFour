<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { generateQuiz, getAgentOptions, getPlayer } from '../services/api'

const VIDEOGAME_PERIODS = ['Años 90', 'Años 80', 'Años 2000', 'Arcades clásicos', 'Consolas clásicas']

const router = useRouter()
const options = ref({ categorias: [], dificultades: [], max_preguntas: 10, proveedor: 'Groq' })
const tema = ref('Historia')
const subtema = ref(VIDEOGAME_PERIODS[0])
const customTema = ref('')
const dificultad = ref('Medio')
const loading = ref(false)
const error = ref('')

onMounted(async () => {
  try {
    options.value = await getAgentOptions()
    const { categorias, dificultades } = options.value
    tema.value = categorias.includes('Videojuegos') ? 'Videojuegos' : categorias[0] || 'Historia'
    dificultad.value = dificultades[1] || 'Medio'
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'No se pudieron cargar las opciones.'
  }
})

function selectedTopic() {
  if (tema.value === 'Videojuegos') return `Videojuegos — ${subtema.value}`
  if (tema.value === 'Otro') return customTema.value.trim()
  return tema.value
}

async function generar() {
  loading.value = true
  error.value = ''
  try {
    const topic = selectedTopic()
    if (!topic) throw new Error('Escribe el tema que quieres jugar.')

    // El servidor genera las preguntas, guarda la partida y devuelve su identificador.
    const result = await generateQuiz({
      numero_preguntas: 10,
      tema: topic,
      dificultad: dificultad.value,
      jugador: getPlayer(),
    })
    if (!result.partida_id) throw new Error('El servidor no ha creado la partida.')

    await router.push({ path: '/jugar', query: { partida: result.partida_id } })
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'No se pudo generar la partida.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="agent page">
    <h1>Crea tu propio quiz</h1>
    <p class="agent-intro">
      Elige una categoría, un tema concreto y la dificultad. La IA (Groq) generará 10 preguntas nuevas para tu partida.
    </p>

    <form class="card agent-card" @submit.prevent="generar">
      <label>Número de preguntas
        <input value="10" readonly>
      </label>

      <label>Tema
        <select v-model="tema">
          <option v-for="item in options.categorias" :key="item" :value="item">{{ item }}</option>
          <option value="Otro">Otro tema...</option>
        </select>
      </label>

      <label v-if="tema === 'Videojuegos'">Periodo
        <select v-model="subtema">
          <option v-for="period in VIDEOGAME_PERIODS" :key="period">{{ period }}</option>
        </select>
      </label>

      <label v-if="tema === 'Otro'">¿Qué tema quieres?
        <input v-model="customTema" maxlength="80" placeholder="Ej. Fórmula 1 en los años 90">
      </label>

      <label>Dificultad
        <select v-model="dificultad">
          <option v-for="item in options.dificultades" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>

      <div v-if="error" class="agent-error" role="alert">{{ error }}</div>

      <button class="primary" :disabled="loading">
        {{ loading ? 'Generando 10 preguntas…' : 'Generar mi partida' }}
      </button>
    </form>
  </section>
</template>
