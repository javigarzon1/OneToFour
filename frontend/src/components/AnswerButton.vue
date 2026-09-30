<script setup>
defineProps({letter:String,text:String,selected:Boolean,disabled:Boolean,state:String})
defineEmits(['select'])
</script>
<template><button class="answer" :class="{selected,state}" :disabled="disabled" @click="$emit('select',letter)"><b>{{letter}}</b><span>{{text}}</span></button></template>