import { createRouter, createWebHistory } from 'vue-router'
import RecipesView from './views/RecipesView.vue'
import ChatView from './views/ChatView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: ChatView },
    { path: '/chat/:id?', component: ChatView },
    { path: '/recipes', component: RecipesView },
  ],
})
