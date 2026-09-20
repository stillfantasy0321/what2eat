<script setup lang="ts">
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { useStatus } from './composables/useStatus'
import logoUrl from './assets/what2eat-logo.svg'

const { status } = useStatus()
const route = useRoute()
</script>
<template>
  <div class="site-shell">
    <header class="topbar">
      <RouterLink class="brand" to="/" aria-label="吃神马首页">
        <img class="brand-logo" :src="logoUrl" alt="">
        <span><strong>吃神马</strong><small>what2eat</small></span>
      </RouterLink>
      <nav aria-label="主导航">
        <RouterLink to="/" :class="{ active: route.path === '/' || route.path.startsWith('/chat') }">对话</RouterLink>
        <RouterLink to="/recipes" :class="{ active: route.path.startsWith('/recipes') }">菜谱</RouterLink>
      </nav>
      <span class="service-indicator" :class="{ ready: status?.capabilities.database?.ready }" :title="status?.capabilities.database?.ready ? '服务已连接' : '服务待配置'" />
    </header>
    <main class="site-main"><RouterView /></main>
  </div>
</template>
