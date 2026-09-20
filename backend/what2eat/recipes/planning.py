from itertools import cycle
from what2eat.recipes.schemas import PlanRequest, Recipe

ALIASES = {'番茄': '西红柿', '小葱': '葱'}
UNKNOWN_COMPOUND_MARKERS = ('复合', '调味酱', '酱料', '香料', '底料', '咖喱块')


def normalize(name: str) -> str:
    value = ''.join(name.lower().split())
    for source, target in ALIASES.items():
        value = value.replace(source, target)
    return value


def ingredient_safety(names: list[str], allergens: list[str]) -> str:
    if not allergens:
        return 'clear'
    normalized = [normalize(name) for name in names]
    for allergen in map(normalize, allergens):
        if any(allergen in name for name in normalized):
            return 'excluded'
    if any(marker in name for marker in UNKNOWN_COMPOUND_MARKERS for name in normalized):
        return 'unknown'
    return 'clear'


def dish_range(diners: int) -> tuple[int, int]:
    if not 1 <= diners <= 12:
        raise ValueError('人数须为 1—12')
    if diners == 1: return 1, 2
    if diners <= 3: return 2, 3
    if diners <= 6: return 3, 5
    return 5, 8


def _matches_exclusions(recipe: Recipe, excluded: list[str]) -> bool:
    haystack = normalize(' '.join([recipe.title, recipe.raw_text] + [item.name for item in recipe.ingredients]))
    return any(normalize(item) in haystack for item in excluded)


class Planner:
    def __init__(self, catalog, retriever):
        self.catalog = catalog
        self.retriever = retriever

    async def _candidates(self, request: PlanRequest) -> tuple[list[Recipe], list[str]]:
        recipes = [recipe for recipe in await self.catalog.all() if recipe.ingredient_status == 'complete']
        warnings: list[str] = []
        safe: list[Recipe] = []
        for recipe in recipes:
            names = [item.name for item in recipe.ingredients]
            if _matches_exclusions(recipe, request.excluded_ingredients):
                continue
            status = ingredient_safety(names, request.allergens)
            if status != 'clear':
                if status == 'unknown':
                    warnings.append(f'{recipe.title} 含成分不明确的复合调味料，未纳入推荐。')
                continue
            safe.append(recipe)
        pantry = {normalize(item) for item in request.pantry}
        safe.sort(key=lambda recipe: (
            -sum(normalize(item.name) in pantry for item in recipe.ingredients),
            recipe.category, recipe.title, str(recipe.id)))
        return safe, warnings[:8]

    @staticmethod
    def _constraints(request: PlanRequest) -> dict:
        return request.model_dump(mode='json')

    @staticmethod
    def _slot(recipe: Recipe, day: int, meal_slot: str, pantry: list[str]) -> dict:
        pantry_normalized = {normalize(item) for item in pantry}
        matched = [item.name for item in recipe.ingredients if normalize(item.name) in pantry_normalized]
        reason = f'可使用已有食材：{"、".join(matched[:3])}' if matched else f'来自{recipe.category}分类'
        return {'day': day, 'meal_slot': meal_slot, 'recipe_id': str(recipe.id),
                'title': recipe.title, 'category': recipe.category, 'reason': reason}

    async def today(self, request: PlanRequest) -> dict:
        candidates, warnings = await self._candidates(request)
        count = dish_range(request.diners)[0]
        chosen = candidates[:count]
        needs = len(chosen) < count
        if needs:
            warnings.append('符合当前条件的菜谱不足，请调整排除条件或允许重复。')
        slots = [self._slot(recipe, 1, 'dinner', request.pantry) for recipe in chosen]
        return {'slots': slots, 'recipe_ids': [str(recipe.id) for recipe in chosen],
                'sources': [recipe.source_url for recipe in chosen if recipe.source_url],
                'constraints': self._constraints(request), 'warnings': warnings,
                'needs_clarification': needs}

    async def weekly(self, request: PlanRequest) -> dict:
        candidates, warnings = await self._candidates(request)
        requested = [(day, slot) for day in range(1, request.days + 1) for slot in request.meal_slots]
        if request.allow_repeats and candidates:
            chosen = [recipe for recipe, _ in zip(cycle(candidates), requested)]
        else:
            chosen = candidates[:len(requested)]
        slots = [self._slot(recipe, day, slot, request.pantry)
                 for recipe, (day, slot) in zip(chosen, requested)]
        needs = len(slots) < len(requested)
        if needs:
            warnings.append(f'仅找到 {len(slots)} 道符合条件的菜谱，需要调整条件或允许重复。')
        return {'slots': slots, 'recipe_ids': [slot['recipe_id'] for slot in slots],
                'sources': list(dict.fromkeys(recipe.source_url for recipe in chosen if recipe.source_url)),
                'constraints': self._constraints(request), 'warnings': warnings,
                'needs_clarification': needs}
