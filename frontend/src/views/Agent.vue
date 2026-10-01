<script setup>
import {onMounted,ref} from 'vue'
import {useRouter} from 'vue-router'
import {generateQuiz,getAgentOptions,getPlayer} from '../services/api'

const router=useRouter()
const options=ref({categorias:[],dificultades:[],max_preguntas:10})
const numero=10,tema=ref('Historia'),subtema=ref('Años 90'),customTema=ref(''),dificultad=ref('Medio')
const loading=ref(false),error=ref('')

onMounted(async()=>{
  try{options.value=await getAgentOptions();tema.value=options.value.categorias.includes('Videojuegos')?'Videojuegos':options.value.categorias[0]||'Historia';dificultad.value=options.value.dificultades[1]||'Medio'}
  catch(e){error.value=e.message}
})

async function generar(){
  loading.value=true;error.value=''
  try{
    let selectedTema
    if(tema.value==='Videojuegos') selectedTema=`Videojuegos — ${subtema.value}`
    else if(tema.value==='Otro') selectedTema=customTema.value.trim()
    else selectedTema=tema.value
    if(!selectedTema) throw new Error('Escribe el tema que quieres jugar.')
    const result=await generateQuiz({numero_preguntas:numero,tema:selectedTema,dificultad:dificultad.value})
    if(!Array.isArray(result.preguntas)||result.preguntas.length!==10) throw new Error('El agente no ha generado exactamente 10 preguntas.')
    sessionStorage.setItem('onetoFour_ai_quiz',JSON.stringify(result.preguntas.slice(0,10)))
    router.push({path:'/jugar',query:{jugador:getPlayer(),numero:10,categoria:tema.value==='Otro'?customTema.value:tema.value,dificultad:dificultad.value,ai:'1',tema:selectedTema}})
  }catch(e){error.value=e.message}
  finally{loading.value=false}
}
</script>

<template>
<section class="agent page">
  <small>AGENTE IA · ONE TO FOUR</small>
  <h1>Crea tu<br><em>propio quiz.</em></h1>
  <p class="agent-intro">Elige una categoría, un tema concreto y la dificultad. La IA generará exactamente 10 preguntas nuevas para tu partida.</p>
  <form class="card agent-card" @submit.prevent="generar">
    <label>Número de preguntas
      <input value="10" readonly>
    </label>
    <label>Tema
      <select v-model="tema">
        <option v-for="item in options.categorias" :key="item" :value="item">{{item}}</option>
        <option value="Otro">Otro tema...</option>
      </select>
    </label>
    <label v-if="tema==='Videojuegos'">Periodo
      <select v-model="subtema">
        <option>Años 90</option>
        <option>Años 80</option>
        <option>Años 2000</option>
        <option>Arcades clásicos</option>
        <option>Consolas clásicas</option>
      </select>
    </label>
    <label v-if="tema==='Otro'">¿Qué tema quieres?
      <input v-model="customTema" maxlength="80" placeholder="Ej. Fórmula 1 en los años 90">
    </label>
    <label>Dificultad
      <select v-model="dificultad">
        <option v-for="item in options.dificultades" :key="item" :value="item">{{item}}</option>
      </select>
    </label>
    <div v-if="error" class="agent-error">{{error}}</div>
    <button class="primary" :disabled="loading">{{loading?'Generando 10 preguntas...':'Generar mi partida'}}<span>→</span></button>
  </form>
</section>
</template>
