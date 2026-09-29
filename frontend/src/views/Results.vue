<script setup>
import {computed} from 'vue'
import {useRoute,useRouter} from 'vue-router'
const route=useRoute(),router=useRouter()
const score=computed(()=>Number(route.query.score||0)),total=computed(()=>Number(route.query.total||0)),percent=computed(()=>Number(route.query.porcentaje||0)),player=computed(()=>route.query.jugador||'Jugador')
const message=computed(()=>percent.value===100?'¡Partida perfecta!':percent.value>=60?'¡Buen trabajo!':'Sigue practicando.')
</script>
<template><section class="results page"><div class="result"><small>RESULTADO</small><h1>{{message}}</h1><p>{{player}}, este es el resultado de tu partida.</p><div class="big-score">{{score}}<span>/ {{total}}</span></div><b class="percent">{{percent}}%</b><div class="actions"><button class="primary" @click="router.push('/')">Jugar otra vez</button><button class="secondary" @click="router.push('/ranking')">Ver ranking</button></div></div></section></template>