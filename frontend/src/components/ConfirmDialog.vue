<script setup lang="ts">
defineProps<{ open: boolean; title: string; description: string; busy?: boolean }>()
defineEmits<{ confirm: []; cancel: [] }>()
</script>

<template>
  <div v-if="open" class="dialog-backdrop" @click.self="$emit('cancel')">
    <section class="confirm-dialog" role="alertdialog" aria-modal="true" :aria-labelledby="'confirm-title'">
      <span class="dialog-kicker">PLEASE CONFIRM</span>
      <h2 id="confirm-title">{{ title }}</h2>
      <p>{{ description }}</p>
      <div class="dialog-actions">
        <button type="button" class="secondary" :disabled="busy" @click="$emit('cancel')">取消</button>
        <button type="button" class="danger" data-action="confirm-delete" :disabled="busy" @click="$emit('confirm')">{{ busy ? '正在删除…' : '确认删除' }}</button>
      </div>
    </section>
  </div>
</template>
