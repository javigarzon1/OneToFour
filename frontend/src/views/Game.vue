<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AnswerButton from '../components/AnswerButton.vue'
import ProgressBar from '../components/ProgressBar.vue'
import { getQuestions, saveGame } from '../services/api'

const route = useRoute()
const router = useRouter()
const loading = ref(true)
const error = ref('')
const saveError = ref('')
const saving = ref(false)
const questions = ref([])
const index = ref(0)
const selected = ref('')
const score = ref(0)
const locked = ref(false)
const streak = ref(0)
const maxStreak = ref(0)
const timeLeft = ref(15)
const correctAnswers = ref(0)
const timeout = ref(false)
let timer = null

const player = computed(() => route.query.jugador || 'Jugador')
const category = computed(() => route.query.modo === 'aleatorio' ? 'Mixto' : (route.query.categoria || 'Todas'))
const difficulty = computed(() => route.query.dificultad || 'Todas')
const question = computed(() => questions.value[index.value])
const total = computed(() => questions.value.length)
const answers = computed(() => question.value ? [
  ['A', question.value.opcion_a],
  ['B', question.value.opcion_b],
  ['C', question.value.opcion_c],
  ['D', question.value.opcion_d],
] : [])
const difficultyPoints = computed(() => question.value?.dificultad === 'Difícil' ? 3 : question.value?.dificultad === 'Medio' ? 2 : 1)
const maxScore = computed(() => questions.value.reduce((sum, q) => sum + (q.dificultad === 'Difícil' ? 3 : q.dificultad === 'Medio' ? 2 : 1), 0))
const percent = computed(() => maxScore.value ? Math.round(score.value / maxScore.value * 100) : 0)
const timerProgress = computed(() => String(Math.max(0, timeLeft.value / 15 * 100)) + '%')
const isCorrect = computed(() => locked.value && !timeout.value && selected.value === question.value?.correcta)
const correctAnswerText = computed(() => {
  const letter = question.value?.correcta
  return answers.value.find(([key]) => key === letter)?.[1] || ''
})
const feedback = computed(() => {
  if (!locked.value) return ''
  if (timeout.value) return 'Se acabó el tiempo.'
  return isCorrect.value ? '¡Respuesta correcta!' : 'Respuesta incorrecta.'
})
const answerState = (letter) => locked.value
  ? (letter === question.value?.correcta ? 'correct' : letter === selected.value ? 'wrong' : '')
  : ''

function stopTimer() {
  if (timer) clearInterval(timer)
  timer = null
}

function startTimer() {
  stopTimer()
  timeLeft.value = 15
  timer = setInterval(() => {
    if (locked.value) {
      stopTimer()
      return
    }
    timeLeft.value = Math.max(0, timeLeft.value - 1)
    if (timeLeft.value === 0) answer('', true)
  }, 1000)
}

function answer(letter, expired = false) {
  if (locked.value || !question.value) return
  stopTimer()
  selected.value = letter
  timeout.value = expired
  locked.value = true
  saveError.value = ''

  if (!expired && letter === question.value.correcta) {
    score.value += difficultyPoints.value
    correctAnswers.value++
    streak.value++
    maxStreak.value = Math.max(maxStreak.value, streak.value)
  } else {
    streak.value = 0
  }
}

function continueQuestion() {
  if (!locked.value || saving.value) return
  saveError.value = ''
  if (index.value + 1 < total.value) {
    index.value++
    selected.value = ''
    locked.value = false
    timeout.value = false
    startTimer()
  } else {
    finish()
  }
}

async function finish() {
  stopTimer()
  saving.value = true
  saveError.value = ''
  try {
    await saveGame({
      jugador: player.value,
      puntuacion: score.value,
      total_preguntas: total.value,
      porcentaje: percent.value,
      categoria: category.value,
      dificultad: difficulty.value,
      preguntas_ids: route.query.ai === '1' ? [] : questions.value.map(q => q.id),
    })
    await router.push({
      path: '/resultado',
      query: { jugador: player.value, score: score.value, total: total.value, porcentaje: percent.value, racha: maxStreak.value },
    })
  } catch (e) {
    saveError.value = e instanceof Error ? e.message : 'No se pudo guardar la partida.'
  } finally {
    saving.value = false
  }
}

async function load() {
  try {
    if (route.query.ai === '1') {
      const stored = sessionStorage.getItem('onetoFour_ai_quiz')
      if (!stored) throw new Error('No se encontró la partida generada por el agente.')
      questions.value = JSON.parse(stored).slice(0, 10)
      sessionStorage.removeItem('onetoFour_ai_quiz')
    } else {
      const randomMode = route.query.modo === 'aleatorio'
      const pool = await getQuestions({
        modo: randomMode ? 'aleatorio' : 'normal',
        categoria: randomMode ? undefined : route.query.categoria,
        dificultad: route.query.dificultad,
        limit: 10,
        jugador: player.value,
      })
      if (randomMode) {
        const shuffled = [...pool].sort(() => Math.random() - 0.5)
        const byCategory = new Map()
        shuffled.forEach((q) => {
          if (!byCategory.has(q.categoria)) byCategory.set(q.categoria, [])
          byCategory.get(q.categoria).push(q)
        })
        const mixed = []
        while (mixed.length < 10 && byCategory.size) {
          for (const [categoryName, items] of byCategory) {
            const q = items.shift()
            if (q) mixed.push(q)
            if (!items.length) byCategory.delete(categoryName)
            if (mixed.length === 10) break
          }
        }
        questions.value = mixed
      } else {
        questions.value = pool.slice(0, 10)
      }
    }
    if (!questions.value.length) error.value = 'No hay preguntas para estos filtros.'
    else startTimer()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'No se pudo cargar la partida.'
  } finally {
    loading.value = false
  }
}

onMounted(load)
onBeforeUnmount(stopTimer)
</script>

<template>
  <section class="game page">
    <div v-if="loading" class="state" role="status">Preparando tu partida…</div>
    <div v-else-if="error" class="state error-state" role="alert">
      <span class="state-icon" aria-hidden="true">!</span>
      <h2>No se ha podido iniciar la partida</h2>
      <p>{{ error }}</p>
      <RouterLink class="primary ranking-cta" to="/">Volver al inicio <span>→</span></RouterLink>
    </div>

    <template v-else>
      <div class="game-top">
        <div>
          <small>JUGADOR</small>
          <h2>{{ player }}</h2>
          <span class="game-mode-label">{{ category }} · {{ difficulty }}</span>
        </div>
        <div class="game-metrics">
          <div class="metric">Puntos <b>{{ score }}</b></div>
          <div class="metric streak">🔥 <b>{{ streak }}</b> racha</div>
          <div class="timer" :class="{ urgent: timeLeft <= 5 && !locked }" aria-live="polite">
            <span>⏱</span> {{ timeLeft }}s
            <i class="timer-fill" :style="{ width: timerProgress }"></i>
          </div>
        </div>
      </div>

      <ProgressBar :current="index + 1" :total="total" />

      <article v-if="question" class="question card">
        <div class="question-head">
          <div class="question-meta">
            <small>{{ question.categoria }} · {{ question.dificultad }} · +{{ difficultyPoints }} puntos</small>
          </div>
          <span class="question-number">PREGUNTA {{ String(index + 1).padStart(2, '0') }} / {{ String(total).padStart(2, '0') }}</span>
        </div>
        <h1>{{ question.pregunta }}</h1>
        <div class="answers">
          <AnswerButton
            v-for="a in answers"
            :key="a[0]"
            :letter="a[0]"
            :text="a[1]"
            :selected="selected === a[0]"
            :disabled="locked"
            :state="answerState(a[0])"
            @select="answer"
          />
        </div>

        <div v-if="locked" class="answer-review" :class="{ success: isCorrect }" aria-live="polite">
          <div class="answer-review-heading">
            <strong>{{ feedback }}</strong>
            <span v-if="timeout" class="review-chip">Tiempo agotado</span>
            <span v-else-if="isCorrect" class="review-chip">+{{ difficultyPoints }} puntos</span>
          </div>
          <p class="correct-answer"><span>Respuesta correcta</span><strong>{{ question.correcta }} · {{ correctAnswerText }}</strong></p>
          <p v-if="question.explicacion" class="answer-explanation">{{ question.explicacion }}</p>
        </div>

        <div class="question-actions">
          <p v-if="!locked" class="answer-hint">Selecciona una opción antes de que termine el tiempo.</p>
          <span v-else class="answer-hint">{{ index + 1 < total ? '¿Listo para la siguiente?' : 'Última pregunta completada.' }}</span>
          <button v-if="locked" class="primary continue-button" type="button" :disabled="saving" @click="continueQuestion">
            {{ saving ? 'Guardando…' : index + 1 < total ? 'Continuar' : 'Ver resultados' }} <span>→</span>
          </button>
        </div>
        <div v-if="saveError" class="save-error" role="alert">
          <span>{{ saveError }}</span>
          <button class="secondary" type="button" :disabled="saving" @click="finish">{{ saving ? 'Guardando…' : 'Reintentar guardado' }}</button>
        </div>
      </article>
    </template>
  </section>
</template>
