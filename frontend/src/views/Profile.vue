<script setup>
import {computed,onMounted,ref} from 'vue'
import {getPlayerProfile,getAuthenticatedUser} from '../services/api'

const jugador=ref(getAuthenticatedUser()?.usuario||'')
const data=ref(null),loading=ref(false),error=ref('')

const unlocked=computed(()=>data.value?.achievements?.filter(a=>a.desbloqueado).length||0)
const totalAchievements=computed(()=>data.value?.achievements?.length||0)
const progress=computed(()=>totalAchievements.value?Math.round(unlocked.value/totalAchievements.value*100):0)

async function load(){
  if(!jugador.value)return
  loading.value=true
  error.value=''
  try{data.value=await getPlayerProfile()}catch(e){error.value=e.message;data.value=null}finally{loading.value=false}
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
  <small>MI PROGRESO</small>
  <h1>Tu perfil</h1>
  <p class="profile-intro">Consulta tu evolución, tus mejores resultados y los logros que has desbloqueado.</p>

  <div class="profile-search card"><div><small>CUENTA</small><strong>{{jugador}}</strong><span>Tu progreso está vinculado a esta cuenta.</span></div><button class="primary" :disabled="loading" @click="load">{{loading?'Cargando...':'Actualizar progreso'}} <span>↻</span></button></div>

  <div v-if="error" class="agent-error">{{error}}</div>
  <template v-if="data">
    <div class="profile-heading">
      <div><small>JUGADOR</small><h2>{{data.jugador}}</h2></div>
      <div class="achievement-progress"><strong>{{unlocked}}/{{totalAchievements}}</strong><span>logros · {{progress}}%</span></div>
    </div>

    <div class="stat-cards profile-cards">
      <div class="stat-card"><small>PARTIDAS</small><strong>{{data.summary.partidas}}</strong><span>completadas</span></div>
      <div class="stat-card"><small>PUNTOS TOTALES</small><strong>{{data.summary.puntos_totales}}</strong><span>acumulados</span></div>
      <div class="stat-card"><small>MEJOR PARTIDA</small><strong>{{data.summary.mejor_puntuacion}}</strong><span>puntos</span></div>
      <div class="stat-card"><small>MEDIA</small><strong>{{data.summary.porcentaje_medio}}%</strong><span>aciertos</span></div>
    </div>

    <div class="profile-grid">
      <article class="card achievements">
        <div><small>COLECCIÓN</small><h2>Logros</h2></div>
        <div class="achievement-list">
          <div v-for="achievement in data.achievements" :key="achievement.id" class="achievement" :class="{locked:!achievement.desbloqueado}">
            <div class="achievement-icon">{{achievement.icono}}</div>
            <div><strong>{{achievement.titulo}}</strong><span>{{achievement.descripcion}}</span></div>
            <b>{{achievement.desbloqueado?'✓':'🔒'}}</b>
          </div>
        </div>
      </article>

      <article class="card recent-profile">
        <div><small>HISTORIAL</small><h2>Últimas partidas</h2></div>
        <div v-if="!data.recent.length" class="empty">Todavía no hay partidas.</div>
        <div v-for="(item,i) in data.recent" :key="i" class="profile-match">
          <div><strong>{{item.puntuacion}} pts</strong><span>{{item.porcentaje}}% · {{item.categoria}}</span></div>
          <small>{{formatDate(item.fecha)}}</small>
        </div>
      </article>
    </div>
  </template>
</section>
</template>
