<script setup lang="ts">
import { computed } from 'vue'
const props = defineProps<{ page: number; totalPages: number; busy?: boolean }>()
defineEmits<{ change: [page: number] }>()
const pages = computed(() => Array.from({length: props.totalPages}, (_, index) => index + 1))
</script>
<template><nav v-if="totalPages>1" class="pagination" aria-label="分页"><button type="button" :disabled="busy||page<=1" aria-label="上一页" @click="$emit('change',page-1)">←</button><button v-for="number in pages" :key="number" type="button" :class="{active:number===page}" :aria-label="`第 ${number} 页`" :aria-current="number===page?'page':undefined" :disabled="busy" @click="$emit('change',number)">{{number}}</button><button type="button" :disabled="busy||page>=totalPages" aria-label="下一页" @click="$emit('change',page+1)">→</button></nav></template>
