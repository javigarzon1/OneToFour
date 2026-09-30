<script setup>
import {computed} from 'vue'
import {useRoute,useRouter} from 'vue-router'
const route=useRoute(),router=useRouter()
const score=computed(()=>Number(route.query.score||0)),total=computed(()=>Number(route.query.total||0)),percent=computed(()=>Number(route.query.porcentaje||0)),player=computed(()=>route.query.jugador||'Jugador'),streak=computed(()=>Number(route.query.racha||0))
const message=computed(()=>percent.value===100?'¡Partida perfecta!':percent.value>=70?'¡Gran partida!':percent.value>=50?'¡Buen trabajo!':'Sigue practicando.')
</script>
<template>
<section class="results page">
  <div class="result">
    <small>RESULTADO FINAL</small>
    <h1>{{message}}</h1>
    <p>{{player}}, así ha ido tu partida.</p>
    <div class="result-stats">
      <div><span>PUNTOS</span><strong>{{score}}</strong></div>
      <div><span>ACIERTOS</span><strong>{{percent}}%</strong></div>
      <div><span>MEJOR RACHA</span><strong>🔥 {{streak}}</strong></div>
    </div>
    <p class="result-detail">{{total}} preguntas completadas</p>
    <div class="actions"><button class="primary" @click="router.push('/')">Jugar otra vez</button><button class="secondary" @click="router.push('/ranking')">Ver ranking</button></div>
  </div>
</section>
</template>