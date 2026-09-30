import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Game from '../views/Game.vue'
import Results from '../views/Results.vue'
import Ranking from '../views/Ranking.vue'
import Statistics from '../views/Statistics.vue'
import Agent from '../views/Agent.vue'
import Profile from '../views/Profile.vue'
import Auth from '../views/Auth.vue'
import { isAuthenticated } from '../services/api'

const routes=[
  {path:'/',component:Home},
  {path:'/jugar',component:Game,meta:{requiresAuth:true}},
  {path:'/resultado',component:Results,meta:{requiresAuth:true}},
  {path:'/ranking',component:Ranking},
  {path:'/estadisticas',component:Statistics},
  {path:'/agente',component:Agent,meta:{requiresAuth:true}},
  {path:'/perfil',component:Profile,meta:{requiresAuth:true}},
  {path:'/cuenta',component:Auth}
]
const router=createRouter({history:createWebHistory(import.meta.env.BASE_URL),routes})
router.beforeEach((to)=>{
  if(to.meta.requiresAuth && !isAuthenticated()){
    return {path:'/cuenta',query:{redirect:to.fullPath}}
  }
  if(to.path==='/cuenta' && isAuthenticated()) return '/perfil'
})
export default router
