<script setup>
import {computed,ref,onMounted,onUnmounted} from 'vue'
import {RouterLink,RouterView,useRouter} from 'vue-router'
import {getAuthenticatedUser,logout} from './services/api'
const router=useRouter()
const user=ref(getAuthenticatedUser())
const authenticated=computed(()=>Boolean(user.value))
function refreshUser(){user.value=getAuthenticatedUser()}
async function signOut(){await logout();refreshUser();router.push('/')}
onMounted(()=>window.addEventListener('auth-changed',refreshUser))
onUnmounted(()=>window.removeEventListener('auth-changed',refreshUser))
</script>
<template>
<div class="app">
<header>
  <RouterLink class="brand" to="/"><b>1</b> OneToFour</RouterLink>
  <nav><RouterLink to="/">Inicio</RouterLink><RouterLink to="/jugar">Jugar</RouterLink><RouterLink to="/ranking">Ranking</RouterLink><RouterLink to="/estadisticas">Estadísticas</RouterLink><RouterLink to="/perfil">Mi progreso</RouterLink><RouterLink to="/agente">Agente IA</RouterLink><RouterLink v-if="!authenticated" to="/cuenta">Entrar</RouterLink><button v-else class="nav-user" @click="signOut">{{user.usuario}} · Salir</button></nav>
</header>
<main><RouterView/></main>
<footer><span>OneToFour</span><span>Python · Vue 3 · Azure Databricks</span></footer>
</div>
</template>
