from decimal import Decimal
import hashlib
from what2eat.recipes.planning import normalize
from what2eat.recipes.schemas import Recipe


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value.normalize(), 'f')


def build_shopping_list(recipes: list[Recipe], diners: int, pantry: list[str]) -> list[dict]:
    if not 1 <= diners <= 12:
        raise ValueError('人数须为1—12')
    available_names = {normalize(item) for item in pantry}
    grouped: dict[tuple[str, str | None, str | None], dict] = {}
    for recipe in recipes:
        for ingredient in recipe.ingredients:
            canonical = normalize(ingredient.name)
            merge_raw = None if ingredient.unit and ingredient.amount is not None else ingredient.raw
            key = (canonical, ingredient.unit, merge_raw)
            scaled = ingredient.amount
            estimated = False
            if ingredient.amount is not None and recipe.servings:
                scaled = ingredient.amount * Decimal(diners) / recipe.servings
                estimated = True
            if key not in grouped:
                stable = hashlib.sha256('|'.join(str(value or '') for value in key).encode()).hexdigest()[:20]
                grouped[key] = {
                    'item_id': stable, 'name': ingredient.name, 'amount_decimal': Decimal('0') if scaled is not None else None,
                    'unit': ingredient.unit, 'raw': ingredient.raw,
                    'source_recipe_ids': [], 'estimated': estimated,
                    'available': canonical in available_names, 'checked': False,
                }
            item = grouped[key]
            if scaled is not None:
                if item['amount_decimal'] is None:
                    item['amount_decimal'] = Decimal('0')
                item['amount_decimal'] += scaled
            item['estimated'] = item['estimated'] or estimated
            source_id = str(recipe.id)
            if source_id not in item['source_recipe_ids']:
                item['source_recipe_ids'].append(source_id)
    result = []
    for item in grouped.values():
        amount = item.pop('amount_decimal')
        item['amount'] = _decimal_text(amount)
        result.append(item)
    return sorted(result, key=lambda item: (item['available'], normalize(item['name']), item['unit'] or '', item['item_id']))
