const API_URL=(import.meta.env.VITE_API_URL||'http://localhost:8000').replace(/\/$/,'')

async function request(path,options={}){
  const headers=new Headers(options.headers||{})
  let response
  try{
    response=await fetch(API_URL+path,{...options,headers})
  }catch(e){
    throw new Error(`No se puede conectar con el backend (${API_URL}). Comprueba que FastAPI está arrancado en el puerto 8000.`)
  }
  if(!response.ok){
    let detail='Error en la API.'
    try{const body=await response.json();detail=body.detail||detail}catch{}
    throw new Error(detail)
  }
  return response.json()
}

export async function getQuestions(params={}){ return request('/api/questions?'+new URLSearchParams({...params,limit:10})) }
export async function saveGame(data){ return request('/api/games',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}) }
export async function getRanking(){ return request('/api/ranking') }
export async function getStats(){ return request('/api/stats') }
export async function getAgentOptions(){ return request('/api/agent/options') }
export async function generateQuiz(data){ return request('/api/agent/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}) }
export async function getPlayerProfile(jugador){ const nombre=String(jugador||localStorage.getItem('onetoFour_player')||'Jugador').trim(); return request('/api/player/'+encodeURIComponent(nombre)+'/profile') }
export function getPlayer(){ return localStorage.getItem('onetoFour_player')||'Jugador' }
export function setPlayer(nombre){ localStorage.setItem('onetoFour_player',String(nombre||'Jugador').trim()||'Jugador') }
