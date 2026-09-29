<script setup>
import {computed,onMounted,ref} from 'vue'
import {useRoute,useRouter} from 'vue-router'
import AnswerButton from '../components/AnswerButton.vue'
import ProgressBar from '../components/ProgressBar.vue'
import {getQuestions,saveGame} from '../services/api'
const route=useRoute(),router=useRouter(),loading=ref(true),error=ref(''),questions=ref([]),index=ref(0),selected=ref(''),score=ref(0),locked=ref(false)
const player=computed(()=>route.query.jugador||'Jugador'),question=computed(()=>questions.value[index.value]),total=computed(()=>questions.value.length)
const answers=computed(()=>question.value?[['A',question.value.opcion_a],['B',question.value.opcion_b],['C',question.value.opcion_c],['D',question.value.opcion_d]]:[])
async function load(){try{questions.value=await getQuestions({categoria:route.query.categoria,dificultad:route.query.dificultad});questions.value.sort(()=>Math.random()-.5);questions.value=questions.value.slice(0,Number(route.query.numero||5));if(!questions.value.length)error.value='No hay preguntas para estos filtros.'}catch(e){error.value=e.message}finally{loading.value=false}}
function answer(letter){if(locked.value)return;selected.value=letter;locked.value=true;if(letter===question.value.correcta)score.value++;setTimeout(async()=>{if(index.value+1<total.value){index.value++;selected.value='';locked.value=false}else{try{const r=await saveGame({jugador:player.value,puntuacion:score.value,total_preguntas:total.value,porcentaje:Math.round(score.value/total.value*100)});router.push({path:'/resultado',query:{jugador:player.value,score:score.value,total:total.value,porcentaje:r.porcentaje}})}catch(e){error.value=e.message;locked.value=false}}},550)}
onMounted(load)
</script>
<template><section class="game page"><div v-if="loading" class="state">Cargando partida...</div><div v-else-if="error" class="state">{{error}}</div><template v-else><div class="game-top"><div><small>JUGADOR</small><h2>{{player}}</h2></div><div class="score">Puntos <b>{{score}}</b></div></div><ProgressBar :current="index+1" :total="total"/><article class="question card"><small>{{question.categoria}} · {{question.dificultad}}</small><h1>{{question.pregunta}}</h1><div class="answers"><AnswerButton v-for="a in answers" :key="a[0]" :letter="a[0]" :text="a[1]" :selected="selected===a[0]" :disabled="locked" @select="answer"/></div></article></template></section></template>