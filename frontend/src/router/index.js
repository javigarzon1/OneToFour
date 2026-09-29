import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Game from '../views/Game.vue'
import Results from '../views/Results.vue'
import Ranking from '../views/Ranking.vue'
export default createRouter({
  history:createWebHistory(),
  routes:[
    {path:'/',component:Home},
    {path:'/jugar',component:Game},
    {path:'/resultado',component:Results},
    {path:'/ranking',component:Ranking}
  ]
})