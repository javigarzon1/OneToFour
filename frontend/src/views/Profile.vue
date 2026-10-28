<script setup>
import {computed,onMounted,ref} from 'vue'
import {getPlayerProfile,getPlayer,setPlayer} from '../services/api'

const jugador=ref(getPlayer())
const data=ref(null),loading=ref(false),error=ref('')

const unlocked=computed(()=>data.value?.achievements?.filter(a=>a.desbloqueado).length||0)
const totalAchievements=computed(()=>data.value?.achievements?.length||0)
const progress=computed(()=>totalAchievements.value?Math.round(unlocked.value/totalAchievements.value*100):0)

async function load(){
  const nombre=jugador.value.trim()||'Jugador'
  setPlayer(nombre)
  jugador.value=nombre
  loading.value=true
  error.value=''
  try{data.value=await getPlayerProfile(jugador.value)}catch(e){error.value=e.message;data.value=null}finally{loading.value=false}
}
function formatDate(value){
  if(!value)return '-'
  const date=new Date(value)
  return Number.isNaN(date.getTime())?value:date.toLocaleDateString('es-ES',{day:'2-digit',month:'short'})
}
onMounted(()=>load())
</script>

<template>
<section class="profile page">
  <h1>Mi progreso</h1>
  <p class="page-lead">Tus mejores resultados y los logros que has desbloqueado.</p>

  <form class="profile-search card" @submit.prevent="load">
    <label>Jugador
      <input v-model="jugador" maxlength="30" placeholder="Nombre del jugador">
    </label>
    <button class="primary" :disabled="loading">{{loading?'Cargando…':'Ver progreso'}}</button>
  </form>

  <div v-if="error" class="agent-error" role="alert">{{error}}</div>
  <template v-if="data">
    <div class="profile-heading">
      <h2>{{data.jugador}}</h2>
      <div class="achievement-progress"><strong>{{unlocked}}/{{totalAchievements}}</strong><span>logros conseguidos, {{progress}}%</span></div>
    </div>

    <div class="stat-cards profile-cards">
      <div class="stat-card"><span class="stat-label">Partidas</span><strong>{{data.summary.partidas}}</strong><span class="stat-note">completadas</span></div>
      <div class="stat-card"><span class="stat-label">Puntos totales</span><strong>{{data.summary.puntos_totales}}</strong><span class="stat-note">acumulados</span></div>
      <div class="stat-card"><span class="stat-label">Mejor partida</span><strong>{{data.summary.mejor_puntuacion}}</strong><span class="stat-note">puntos</span></div>
      <div class="stat-card"><span class="stat-label">Acierto medio</span><strong>{{data.summary.porcentaje_medio}}%</strong><span class="stat-note">de aciertos</span></div>
    </div>

    <div class="profile-grid">
      <article class="card achievements">
        <h2>Logros</h2>
        <div class="achievement-list">
          <div v-for="achievement in data.achievements" :key="achievement.id" class="achievement" :class="{locked:!achievement.desbloqueado}">
            <div class="achievement-icon">{{achievement.icono}}</div>
            <div><strong>{{achievement.titulo}}</strong><span>{{achievement.descripcion}}</span></div>
            <b class="achievement-state">{{achievement.desbloqueado?'Logrado':'Pendiente'}}</b>
          </div>
        </div>
      </article>

      <article class="card recent-profile">
        <h2>Últimas partidas</h2>
        <div v-if="!data.recent.length" class="empty">Todavía no hay partidas.</div>
        <div v-for="(item,i) in data.recent" :key="i" class="profile-match">
          <div><strong>{{item.puntuacion}} pts</strong><span>{{item.porcentaje}}% de aciertos en {{item.categoria}}</span></div>
          <time>{{formatDate(item.fecha)}}</time>
        </div>
      </article>
    </div>
  </template>
</section>
</template>
