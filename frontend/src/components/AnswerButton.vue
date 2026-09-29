<script setup>
defineProps({letter:String,text:String,selected:Boolean,disabled:Boolean})
defineEmits(['select'])
</script>
<template><button class="answer" :class="{selected}" :disabled="disabled" @click="$emit('select',letter)"><b>{{letter}}</b><span>{{text}}</span></button></template>