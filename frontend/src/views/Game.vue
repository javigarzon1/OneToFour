<script setup>
import {computed,onBeforeUnmount,onMounted,ref} from 'vue'
import {useRoute,useRouter} from 'vue-router'
import AnswerButton from '../components/AnswerButton.vue'
import ProgressBar from '../components/ProgressBar.vue'
import {getQuestions,saveGame} from '../services/api'

const route=useRoute(),router=useRouter()
const loading=ref(true),error=ref(''),questions=ref([]),index=ref(0),selected=ref(''),score=ref(0),locked=ref(false)
const streak=ref(0),maxStreak=ref(0),timeLeft=ref(15),correctAnswers=ref(0),timeout=ref(false)
let timer=null

const player=computed(()=>route.query.jugador||'Jugador')
const question=computed(()=>questions.value[index.value])
const total=computed(()=>questions.value.length)
const answers=computed(()=>question.value?[['A',question.value.opcion_a],['B',question.value.opcion_b],['C',question.value.opcion_c],['D',question.value.opcion_d]]:[])
const difficultyPoints=computed(()=>question.value?.dificultad==='Difícil'?3:question.value?.dificultad==='Medio'?2:1)
const maxScore=computed(()=>questions.value.reduce((sum,q)=>sum+(q.dificultad==='Difícil'?3:q.dificultad==='Medio'?2:1),0))
const percent=computed(()=>maxScore.value?Math.round(score.value/maxScore.value*100):0)
const feedback=computed(()=>{
  if(!locked.value)return ''
  if(timeout.value)return 'Se acabó el tiempo.'
  return selected.value===question.value?.correcta?'¡Correcto!':'Respuesta incorrecta'
})
const answerState=(letter)=>locked.value?(letter===question.value.correcta?'correct':letter===selected.value?'wrong':''):''

function startTimer(){
  clearInterval(timer)
  timeLeft.value=15
  timer=setInterval(()=>{timeLeft.value--;if(timeLeft.value<=0)answer('',true)},1000)
}
function stopTimer(){clearInterval(timer);timer=null}

async function finish(){
  stopTimer()
  try{
    const r=await saveGame({jugador:player.value,puntuacion:score.value,total_preguntas:total.value,porcentaje:percent.value})
    router.push({path:'/resultado',query:{jugador:player.value,score:score.value,total:total.value,porcentaje:percent.value,racha:maxStreak.value}})
  }catch(e){error.value=e.message;locked.value=false}
}
function answer(letter,expired=false){
  if(locked.value)return
  stopTimer();selected.value=letter;timeout.value=expired;locked.value=true
  const correct=!expired&&letter===question.value.correcta
  if(correct){score.value+=difficultyPoints.value;correctAnswers.value++;streak.value++;maxStreak.value=Math.max(maxStreak.value,streak.value)}
  else streak.value=0
  setTimeout(async()=>{
    if(index.value+1<total.value){index.value++;selected.value='';locked.value=false;timeout.value=false;startTimer()}
    else await finish()
  },900)
}
async function load(){
  try{
    questions.value=await getQuestions({categoria:route.query.categoria,dificultad:route.query.dificultad})
    questions.value.sort(()=>Math.random()-.5)
    questions.value=questions.value.slice(0,Number(route.query.numero||5))
    if(!questions.value.length)error.value='No hay preguntas para estos filtros.'
    else startTimer()
  }catch(e){error.value=e.message}
  finally{loading.value=false}
}
onMounted(load)
onBeforeUnmount(stopTimer)
</script>

<template>
<section class="game page">
  <div v-if="loading" class="state">Cargando partida...</div>
  <div v-else-if="error" class="state">{{error}}</div>
  <template v-else>
    <div class="game-top">
      <div><small>JUGADOR</small><h2>{{player}}</h2></div>
      <div class="game-metrics">
        <div class="metric">Puntos <b>{{score}}</b></div>
        <div class="metric streak">🔥 <b>{{streak}}</b> racha</div>
        <div class="timer" :class="{urgent:timeLeft<=5}">⏱ {{timeLeft}}s</div>
      </div>
    </div>
    <ProgressBar :current="index+1" :total="total"/>
    <article class="question card">
      <div class="question-meta"><small>{{question.categoria}} · {{question.dificultad}} · +{{difficultyPoints}} puntos</small></div>
      <h1>{{question.pregunta}}</h1>
      <div class="answers">
        <AnswerButton v-for="a in answers" :key="a[0]" :letter="a[0]" :text="a[1]" :selected="selected===a[0]" :disabled="locked" :state="answerState(a[0])" @select="answer"/>
      </div>
      <div v-if="locked" class="feedback" :class="{success:selected===question.correcta}">
        <strong>{{feedback}}</strong>
        <span v-if="question.explicacion">{{question.explicacion}}</span>
      </div>
    </article>
  </template>
</section>
</template>