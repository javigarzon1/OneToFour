<script setup>
import {onMounted,ref} from 'vue'
import {getRanking} from '../services/api'
const ranking=ref([]),loading=ref(true)
onMounted(async()=>{ranking.value=await getRanking();loading.value=false})
</script>
<template><section class="ranking page"><small>CLASIFICACIÓN</small><h1>Ranking</h1><p>Los mejores resultados registrados.</p><div v-if="loading" class="state">Cargando...</div><div v-else class="card rows"><div v-for="(x,i) in ranking" :key="x.jugador" class="row"><b>{{i+1}}</b><strong>{{x.jugador}}</strong><span>{{x.puntuacion}} pts</span><span>{{x.porcentaje}}%</span></div></div></section></template>