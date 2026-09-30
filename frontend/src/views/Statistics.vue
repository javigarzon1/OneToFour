<script setup>
import {computed,onMounted,ref} from 'vue'
import {getStats} from '../services/api'

const data=ref(null),loading=ref(true),error=ref('')
const summary=computed(()=>data.value?.summary?.[0]||{})
const maxCategory=computed(()=>Math.max(...(data.value?.categories||[]).map(x=>Number(x.porcentaje_medio)||0),1))
const maxDifficulty=computed(()=>Math.max(...(data.value?.difficulties||[]).map(x=>Number(x.porcentaje_medio)||0),1))
function formatDate(value){
  if(!value)return '-'
  const date=new Date(value)
  return Number.isNaN(date.getTime())?value:date.toLocaleDateString('es-ES',{day:'2-digit',month:'short'})
}
onMounted(async()=>{
  try{data.value=await getStats()}catch(e){error.value=e.message}finally{loading.value=false}
})
</script>
<template>
<section class="stats page">
  <small>ANALÍTICA</small>
  <h1>Estadísticas</h1>
  <p>Una visión general del rendimiento de OneToFour.</p>
  <div v-if="loading" class="state">Cargando estadísticas...</div>
  <div v-else-if="error" class="state">{{error}}</div>
  <template v-else>
    <div class="stat-cards">
      <div class="stat-card"><small>PARTIDAS</small><strong>{{summary.partidas||0}}</strong><span>partidas registradas</span></div>
      <div class="stat-card"><small>JUGADORES</small><strong>{{summary.jugadores||0}}</strong><span>jugadores distintos</span></div>
      <div class="stat-card"><small>MEDIA</small><strong>{{summary.porcentaje_medio||0}}%</strong><span>acierto medio</span></div>
      <div class="stat-card"><small>MEJOR PUNTUACIÓN</small><strong>{{summary.mejor_puntuacion||0}}</strong><span>puntos conseguidos</span></div>
    </div>

    <div class="stats-grid">
      <article class="card stats-panel">
        <div class="panel-title"><div><small>CATEGORÍAS</small><h2>Rendimiento por categoría</h2></div></div>
        <div v-if="!data.categories.length" class="empty">Todavía no hay datos por categoría.</div>
        <div v-for="item in data.categories" :key="item.categoria" class="bar-row">
          <div class="bar-label"><strong>{{item.categoria}}</strong><span>{{item.porcentaje_medio}}% · {{item.partidas}} partidas</span></div>
          <div class="bar"><i :style="{width:(item.porcentaje_medio/maxCategory*100)+'%'}"></i></div>
        </div>
      </article>

      <article class="card stats-panel">
        <div><small>DIFICULTAD</small><h2>Rendimiento por nivel</h2></div>
        <div v-if="!data.difficulties.length" class="empty">Todavía no hay datos por dificultad.</div>
        <div v-for="item in data.difficulties" :key="item.dificultad" class="bar-row">
          <div class="bar-label"><strong>{{item.dificultad}}</strong><span>{{item.porcentaje_medio}}%</span></div>
          <div class="bar"><i :style="{width:(item.porcentaje_medio/maxDifficulty*100)+'%'}"></i></div>
        </div>
      </article>
    </div>

    <article class="card recent-panel">
      <div><small>HISTORIAL</small><h2>Últimas partidas</h2></div>
      <div v-if="!data.recent.length" class="empty">No hay partidas registradas todavía.</div>
      <div v-else class="recent-table">
        <div class="recent-head"><span>Jugador</span><span>Puntos</span><span>Resultado</span><span>Categoría</span><span>Fecha</span></div>
        <div v-for="(item,i) in data.recent" :key="item.jugador+i" class="recent-row">
          <strong>{{item.jugador}}</strong><span>{{item.puntuacion}}</span><span>{{item.porcentaje}}%</span><span>{{item.categoria}}</span><span>{{formatDate(item.fecha)}}</span>
        </div>
      </div>
    </article>
  </template>
</section>
</template>