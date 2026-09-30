<script setup>
import {computed,ref} from 'vue'
import {useRouter} from 'vue-router'
import {getAuthenticatedUser,isAuthenticated} from '../services/api'
const router=useRouter()
const user=ref(getAuthenticatedUser())
const authenticated=computed(()=>isAuthenticated() && Boolean(user.value))
const numero=ref(5),modo=ref('normal'),categoria=ref('Todas'),dificultad=ref('Todas')
function empezar(){
  router.push({path:'/jugar',query:{numero:numero.value,modo:modo.value,categoria:modo.value==='aleatorio'?'Aleatorio':categoria.value,dificultad:dificultad.value}})
}
</script>
<template><section class="home page"><div><small>QUIZ · ONE TO FOUR</small><h1>¿Cuánto<br><em>sabes?</em></h1><p>Pon a prueba tus conocimientos. Cuatro opciones, una respuesta correcta y una nueva partida cada vez.</p>
<div v-if="!authenticated" class="card auth-home"><small>ONE TO FOUR AUTH 1.0</small><strong>Juega con tu cuenta</strong><span>Inicia sesión o regístrate para guardar tus partidas y progreso.</span><button class="primary" @click="router.push('/cuenta')">Entrar o registrarme <span>→</span></button></div>
<form v-else class="card" @submit.prevent="empezar"><div class="welcome"><small>CUENTA</small><strong>Hola, {{user.usuario}}</strong><span>Tu progreso se guardará automáticamente en tu cuenta.</span></div><div class="grid"><label>Preguntas<select v-model="numero"><option :value="5">5</option><option :value="10">10</option></select></label><label>Modo de juego<select v-model="modo"><option value="normal">Por tema</option><option value="aleatorio">Aleatorio · mezcla de temas</option></select></label></div><label v-if="modo==='normal'">Categoría<select v-model="categoria"><option>Todas</option><option>Historia</option><option>Cine</option><option>Ciencia</option><option>Deporte</option><option>Corazón</option><option>Naturaleza</option><option>Geografía</option><option>Tecnología</option><option>Música</option><option>Arte</option><option>Literatura</option><option>Cultura general</option></select></label><label>Dificultad<select v-model="dificultad"><option>Todas</option><option>Fácil</option><option>Medio</option><option>Difícil</option></select></label><div v-if="modo==='aleatorio'" class="random-info">🎲 Las preguntas se seleccionarán al azar entre los diferentes temas disponibles.</div><button class="primary">Empezar partida <span>→</span></button></form></div><div class="visual"><strong>1</strong><i>/</i><strong>4</strong><p>Una pregunta.<br>Cuatro posibilidades.</p></div></section></template>