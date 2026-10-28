<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AnswerButton from '../components/AnswerButton.vue'
import ProgressBar from '../components/ProgressBar.vue'
import { answerGame, finishGame, getGame, getPlayer, startGame } from '../services/api'

// El servidor guarda las preguntas de la partida, corrige cada respuesta y
// calcula la puntuación final. Aquí sólo se muestra el estado y se envían respuestas.

const TIME_PER_QUESTION = 15
const POINTS = { Fácil: 1, Medio: 2, Difícil: 3 }

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const error = ref('')
const answerError = ref('')
const saveError = ref('')
const checking = ref(false)
const saving = ref(false)

const gameId = ref('')
const player = ref(route.query.jugador || getPlayer())
const category = ref('')
const difficulty = ref('')
const questions = ref([])
const index = ref(0)
const score = ref(0)
const streak = ref(0)

const selected = ref('')
const locked = ref(false)
const timeout = ref(false)
const review = ref(null) // solución y puntos devueltos por el servidor tras responder
const timeLeft = ref(TIME_PER_QUESTION)
let timer = null
const pendingAnswer = ref(null) // última respuesta que no llegó a confirmarse (para reintentar)

const question = computed(() => questions.value[index.value])
const total = computed(() => questions.value.length)
const answers = computed(() =>
  question.value
    ? [
        ['A', question.value.opcion_a],
        ['B', question.value.opcion_b],
        ['C', question.value.opcion_c],
        ['D', question.value.opcion_d],
      ]
    : [],
)
const difficultyPoints = computed(() => POINTS[question.value?.dificultad] ?? 1)
const timerProgress = computed(() => `${Math.max(0, (timeLeft.value / TIME_PER_QUESTION) * 100)}%`)
const isCorrect = computed(() => Boolean(review.value?.acierto))
const correctAnswerText = computed(
  () => answers.value.find(([letter]) => letter === review.value?.correcta)?.[1] || '',
)
const feedback = computed(() => {
  if (!review.value) return ''
  if (timeout.value) return 'Se acabó el tiempo.'
  return isCorrect.value ? '¡Respuesta correcta!' : 'Respuesta incorrecta.'
})
const answerState = (letter) => {
  if (!review.value) return ''
  if (letter === review.value.correcta) return 'correct'
  return letter === selected.value ? 'wrong' : ''
}

function stopTimer() {
  if (timer) clearInterval(timer)
  timer = null
}

function startTimer() {
  stopTimer()
  timeLeft.value = TIME_PER_QUESTION
  timer = setInterval(() => {
    if (locked.value) {
      stopTimer()
      return
    }
    timeLeft.value = Math.max(0, timeLeft.value - 1)
    if (timeLeft.value === 0) answer('', true)
  }, 1000)
}

function applyState(state) {
  gameId.value = state.partida_id
  player.value = state.jugador
  category.value = state.categoria
  difficulty.value = state.dificultad
  questions.value = state.preguntas
  score.value = state.puntuacion
  streak.value = state.racha
  index.value = Math.min(state.respondidas, Math.max(state.preguntas.length - 1, 0))
}

function resetQuestion() {
  selected.value = ''
  locked.value = false
  timeout.value = false
  review.value = null
  answerError.value = ''
  pendingAnswer.value = null
}

async function answer(letter, expired = false) {
  if (locked.value || checking.value || !question.value) return
  stopTimer()
  selected.value = letter
  timeout.value = expired
  locked.value = true
  checking.value = true
  answerError.value = ''
  pendingAnswer.value = { letter, expired }

  try {
    const result = await answerGame(gameId.value, index.value, expired ? '' : letter)
    review.value = result
    score.value = result.puntuacion
    streak.value = result.racha
    pendingAnswer.value = null
  } catch (e) {
    answerError.value = e instanceof Error ? e.message : 'No se pudo comprobar la respuesta.'
    // 409: el servidor ya tenía esa respuesta (se perdió la confirmación). Se resincroniza.
    if (e?.status === 409) await resync()
  } finally {
    checking.value = false
  }
}

function retryAnswer() {
  if (!pendingAnswer.value) return
  const { letter, expired } = pendingAnswer.value
  locked.value = false
  answer(letter, expired)
}

async function resync() {
  try {
    const state = await getGame(gameId.value)
    applyState(state)
    resetQuestion()
    if (state.respondidas >= state.preguntas.length) await finish()
    else startTimer()
  } catch (e) {
    answerError.value = e instanceof Error ? e.message : 'No se pudo recuperar la partida.'
  }
}

function continueQuestion() {
  if (!review.value || saving.value) return
  if (index.value + 1 < total.value) {
    index.value++
    resetQuestion()
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
    const result = await finishGame(gameId.value)
    await router.push({
      path: '/resultado',
      query: {
        jugador: result.jugador,
        score: result.puntuacion,
        total: result.total_preguntas,
        porcentaje: result.porcentaje,
        racha: result.racha,
      },
    })
  } catch (e) {
    saveError.value = e instanceof Error ? e.message : 'No se pudo guardar la partida.'
  } finally {
    saving.value = false
  }
}

async function load() {
  let complete = false
  try {
    if (route.query.partida) {
      // Partida ya creada (generada por el agente o retomada al recargar la página).
      const state = await getGame(route.query.partida)
      applyState(state)
      complete = state.respondidas >= state.preguntas.length
    } else {
      const state = await startGame({
        jugador: player.value,
        categoria: route.query.categoria || 'Todas',
        dificultad: route.query.dificultad || 'Todas',
        modo: route.query.modo === 'aleatorio' ? 'aleatorio' : 'normal',
      })
      applyState(state)
      // La partida queda en la URL: si se recarga, se retoma donde estaba.
      await router.replace({ query: { partida: state.partida_id } })
    }
    if (!questions.value.length) error.value = 'No hay preguntas para estos filtros.'
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'No se pudo cargar la partida.'
  } finally {
    loading.value = false
  }

  if (error.value) return
  if (complete) await finish()
  else startTimer()
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

        <div v-if="review" class="answer-review" :class="{ success: isCorrect }" aria-live="polite">
          <div class="answer-review-heading">
            <strong>{{ feedback }}</strong>
            <span v-if="timeout" class="review-chip">Tiempo agotado</span>
            <span v-else-if="isCorrect" class="review-chip">+{{ review.puntos }} puntos</span>
          </div>
          <p class="correct-answer"><span>Respuesta correcta</span><strong>{{ review.correcta }} · {{ correctAnswerText }}</strong></p>
          <p v-if="review.explicacion" class="answer-explanation">{{ review.explicacion }}</p>
        </div>

        <div class="question-actions">
          <p v-if="!locked" class="answer-hint">Selecciona una opción antes de que termine el tiempo.</p>
          <span v-else-if="checking" class="answer-hint" role="status">Comprobando respuesta…</span>
          <span v-else-if="review" class="answer-hint">{{ index + 1 < total ? '¿Listo para la siguiente?' : 'Última pregunta completada.' }}</span>
          <button v-if="review" class="primary continue-button" type="button" :disabled="saving" @click="continueQuestion">
            {{ saving ? 'Guardando…' : index + 1 < total ? 'Continuar' : 'Ver resultados' }} <span>→</span>
          </button>
        </div>

        <div v-if="answerError" class="save-error" role="alert">
          <span>{{ answerError }}</span>
          <button v-if="pendingAnswer" class="secondary" type="button" :disabled="checking" @click="retryAnswer">Reintentar</button>
        </div>
        <div v-if="saveError" class="save-error" role="alert">
          <span>{{ saveError }}</span>
          <button class="secondary" type="button" :disabled="saving" @click="finish">{{ saving ? 'Guardando…' : 'Reintentar guardado' }}</button>
        </div>
      </article>
    </template>
  </section>
</template>
