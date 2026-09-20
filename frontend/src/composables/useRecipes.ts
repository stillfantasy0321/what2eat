import { ref } from 'vue'
import { api } from '../api/client'
import type { Page, Recipe } from '../api/types'

export function useRecipes() {
  const recipes = ref<Recipe[]>([])
  const categories = ref<string[]>([])
  const page = ref(1), pageSize = ref(12), total = ref(0), totalPages = ref(0)
  const activeCategory = ref('')
  const loading = ref(false)
  const error = ref('')
  async function load(options: { category?: string; page?: number } = {}) {
    loading.value = true; error.value = ''
    activeCategory.value = options.category ?? activeCategory.value
    const requestedPage = options.page ?? 1
    try {
      const params = new URLSearchParams({page:String(requestedPage),page_size:String(pageSize.value)})
      if(activeCategory.value)params.set('category',activeCategory.value)
      const [result, cats] = await Promise.all([
        api<Page<Recipe>>(`/api/recipes?${params}`),
        api<{ items: string[] }>('/api/recipes/categories'),
      ])
      recipes.value=result.items;page.value=result.page;total.value=result.total;totalPages.value=result.total_pages;categories.value=cats.items
    } catch (reason) { error.value = reason instanceof Error ? reason.message : '菜谱读取失败' }
    finally { loading.value = false }
  }
  return { recipes, categories, page, pageSize, total, totalPages, activeCategory, loading, error, load }
}
