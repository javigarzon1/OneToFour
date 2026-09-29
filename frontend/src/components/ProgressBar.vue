<script setup>
defineProps({current:Number,total:Number})
</script>
<template><div class="progress-info"><span>Pregunta {{current}} de {{total}}</span><span>{{Math.round(current/total*100)}}%</span><div class="progress"><i :style="{width:(current/total*100)+'%'}"></i></div></div></template>