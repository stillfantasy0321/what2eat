from decimal import Decimal, InvalidOperation
import re
from langchain_core.documents import Document
from what2eat.recipes.schemas import Ingredient, Recipe

_BULLET = re.compile(r'^\s*[-*+]\s+(.+?)\s*$')
_AMOUNT = re.compile(r'(\d+(?:\.\d+)?)\s*(ml|mL|g|kg|克|千克|毫升|个|枚|颗|片|瓣|盒|根|勺|匙|杯)')


def _sections(text: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {'intro': []}
    current = 'intro'
    for line in text.splitlines():
        match = re.match(r'^##\s+(.+?)\s*$', line)
        if match:
            current = match.group(1).strip()
            result.setdefault(current, [])
        else:
            result.setdefault(current, []).append(line)
    return result


def _title(text: str, fallback: str) -> str:
    match = re.search(r'^#\s+(.+?)\s*$', text, re.MULTILINE)
    title = match.group(1).strip() if match else fallback
    return re.sub(r'的做法$', '', title)


def _ingredient_name(raw: str) -> str:
    raw = raw.strip().strip('`')
    left = raw.split('=', 1)[0]
    left = re.sub(r'^[总量：\s]+', '', left)
    left = re.sub(r'[（(].*?[)）]', '', left)
    left = re.sub(r'\s*[-–—]\s*$', '', left)
    return left.strip(' ：:') or raw[:40]


def _ingredients(sections: dict[str, list[str]]) -> list[Ingredient]:
    calculation = next((lines for name, lines in sections.items() if name.startswith('计算')), [])
    required = next((lines for name, lines in sections.items() if '原料' in name), [])
    source = calculation if any(_BULLET.match(line) for line in calculation) else required
    ingredients: list[Ingredient] = []
    seen: set[str] = set()
    for line in source:
        match = _BULLET.match(line)
        if not match:
            continue
        raw = match.group(1).strip()
        name = _ingredient_name(raw)
        if not name or name in seen:
            continue
        seen.add(name)
        amount_match = _AMOUNT.search(raw.split('=', 1)[-1])
        amount = unit = None
        if amount_match:
            try:
                amount = Decimal(amount_match.group(1))
                unit = amount_match.group(2).lower().replace('ml', 'ml')
            except InvalidOperation:
                pass
        ingredients.append(Ingredient(name=name, raw=raw, amount=amount, unit=unit))
    return ingredients


def _servings(text: str) -> Decimal | None:
    match = re.search(r'一份正好够\s*(\d+(?:\.\d+)?)\s*个人', text)
    return Decimal(match.group(1)) if match else None


def _bullet_lines(lines: list[str]) -> list[str]:
    return [match.group(1).strip() for line in lines if (match := _BULLET.match(line))]


def parse_recipe(document: Document) -> Recipe:
    text = document.page_content.replace('\r\n', '\n').strip()
    sections = _sections(text)
    operation = next((lines for name, lines in sections.items() if name.startswith('操作')), [])
    notes_section = next((lines for name, lines in sections.items() if '附加' in name or '备注' in name), [])
    ingredients = _ingredients(sections)
    steps = _bullet_lines(operation)
    if ingredients and steps:
        status = 'complete'
    elif ingredients or steps:
        status = 'partial'
    else:
        status = 'unparsed'
    return Recipe(
        id=document.metadata['document_id'],
        title=_title(text, document.metadata.get('title', '未命名菜谱')),
        category=document.metadata.get('category', '用户资料'),
        ingredients=ingredients, steps=steps, notes=_bullet_lines(notes_section),
        servings=_servings(text), source_url=document.metadata.get('source_url'),
        content_hash=document.metadata.get('content_hash', ''),
        ingredient_status=status, raw_text=text,
    )
