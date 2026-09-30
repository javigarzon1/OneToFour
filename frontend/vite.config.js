import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
export default defineConfig({ plugins:[vue()], base:process.env.GITHUB_ACTIONS?'/OneToFour/':'/', server:{port:5173} })