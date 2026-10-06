<script setup>
import {ref} from 'vue'
import {useRouter} from 'vue-router'
import {getPlayer,setPlayer} from '../services/api'
const router=useRouter()
const jugador=ref(getPlayer())
const numero=10,modo=ref('normal'),categoria=ref('Todas'),dificultad=ref('Todas')
function empezar(){
  const nombre=jugador.value.trim()||'Jugador'
  setPlayer(nombre)
  router.push({path:'/jugar',query:{jugador:nombre,numero,modo:modo.value,categoria:modo.value==='aleatorio'?'Aleatorio':categoria.value,dificultad:dificultad.value}})
}
</script>
<template><section class="home page"><div><small>JUEGA A· ONE TO FOUR</small><h1>¿Cuánto<br><em>sabes?</em></h1><p>Pon a prueba tus conocimientos. Cuatro opciones, una respuesta correcta y una nueva partida cada vez.</p>
<form class="card" @submit.prevent="empezar">
<label>Nombre del jugador<input v-model="jugador" maxlength="30" placeholder="Ej. Javi" required></label>
<div class="grid"><label>Preguntas<input value="10" readonly></label><label>Modo de juego<select v-model="modo"><option value="normal">Por tema</option><option value="aleatorio">Aleatorio · mezcla de temas</option></select></label></div>
<label v-if="modo==='normal'">Categoría<select v-model="categoria"><option>Todas</option><option>Historia</option><option>Cine</option><option>Ciencia</option><option>Deporte</option><option>Corazón</option><option>Naturaleza</option><option>Geografía</option><option>Tecnología</option><option>Música</option><option>Arte</option><option>Literatura</option><option>Cultura general</option></select></label>
<label>Dificultad<select v-model="dificultad"><option>Todas</option><option>Fácil</option><option>Medio</option><option>Difícil</option></select></label>
<div v-if="modo==='aleatorio'" class="random-info">🎲 Las 10 preguntas se seleccionarán al azar entre los diferentes temas disponibles.</div>
<button class="primary">Empezar partida · 10 preguntas <span>→</span></button>
</form></div><div class="visual"><strong>1</strong><i>/</i><strong>4</strong><p>Una pregunta.<br>Cuatro posibilidades.</p></div></section></template>
