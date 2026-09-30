<script setup>
import {onMounted,ref} from 'vue'
import {useRouter} from 'vue-router'
import {generateQuiz,getAgentOptions} from '../services/api'

const router=useRouter()
const options=ref({categorias:[],dificultades:[],max_preguntas:20})
const numero=ref(5),tema=ref('Historia'),customTema=ref(''),dificultad=ref('Medio')
const loading=ref(false),error=ref('')

onMounted(async()=>{
  try{options.value=await getAgentOptions();tema.value=options.value.categorias[0]||'Historia';dificultad.value=options.value.dificultades[1]||'Medio'}
  catch(e){error.value=e.message}
})

async function generar(){
  loading.value=true;error.value=''
  try{
    const selectedTema=tema.value==='Otro'?customTema.value.trim():tema.value
    if(!selectedTema) throw new Error('Escribe el tema que quieres jugar.')
    const result=await generateQuiz({numero_preguntas:Number(numero.value),tema:selectedTema,dificultad:dificultad.value})
    sessionStorage.setItem('onetoFour_ai_quiz',JSON.stringify(result.preguntas))
    router.push({path:'/jugar',query:{jugador:'Jugador',numero:result.preguntas.length,categoria:tema.value==='Otro'?customTema.value:tema.value,dificultad:dificultad.value,ai:'1'}})
  }catch(e){error.value=e.message}
  finally{loading.value=false}
}
</script>

<template>
<section class="agent page">
  <small>AGENTE IA · ONE TO FOUR</small>
  <h1>Crea tu<br><em>propio quiz.</em></h1>
  <p class="agent-intro">Dile al agente qué quieres jugar y generará preguntas nuevas para tu partida.</p>
  <form class="card agent-card" @submit.prevent="generar">
    <label>Número de preguntas
      <select v-model="numero">
        <option v-for="n in options.max_preguntas" :key="n" :value="n">{{n}}</option>
      </select>
    </label>
    <label>Tema
      <select v-model="tema">
        <option v-for="item in options.categorias" :key="item" :value="item">{{item}}</option>
        <option value="Otro">Otro tema...</option>
      </select>
    </label>
    <label v-if="tema==='Otro'">¿Qué tema quieres?
      <input v-model="customTema" maxlength="80" placeholder="Ej. Videojuegos de los 90">
    </label>
    <label>Dificultad
      <select v-model="dificultad">
        <option v-for="item in options.dificultades" :key="item" :value="item">{{item}}</option>
      </select>
    </label>
    <div v-if="error" class="agent-error">{{error}}</div>
    <button class="primary" :disabled="loading">{{loading?'Generando preguntas...':'Generar mi partida'}}<span>→</span></button>
  </form>
</section>
</template>