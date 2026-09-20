import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_corpus(manifest_path: Path) -> dict:
    manifest_path = manifest_path.resolve()
    data = json.loads(manifest_path.read_text(encoding='utf-8'))
    categories: set[str] = set()
    for recipe in data.get('recipes', []):
        path = manifest_path.parent / recipe['local_path']
        if not path.is_file():
            raise ValueError(f'语料文件缺失：{recipe["local_path"]}')
        if _sha(path) != recipe['sha256']:
            raise ValueError(f'语料哈希不匹配：{recipe["local_path"]}')
        categories.add(recipe['category'])
    count = len(data.get('recipes', []))
    if not 50 <= count <= 100:
        raise ValueError(f'预置菜谱数量须为50—100，当前为{count}')
    return {'verified': count, 'categories': sorted(categories)}


def fetch_corpus(manifest_path: Path, destination: Path | None = None) -> list[Path]:
    manifest_path = manifest_path.resolve()
    data = json.loads(manifest_path.read_text(encoding='utf-8'))
    destination = destination or manifest_path.parent
    paths: list[Path] = []
    for recipe in data['recipes']:
        path = destination / recipe['local_path']
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            request = Request(recipe['raw_url'], headers={'User-Agent': 'what2eat-corpus/1.0'})
            with urlopen(request, timeout=20) as response:
                path.write_bytes(response.read())
        if _sha(path) != recipe['sha256']:
            raise ValueError(f'语料哈希不匹配：{recipe["local_path"]}')
        paths.append(path)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', type=Path, required=True)
    args = parser.parse_args()
    result = verify_corpus(args.verify)
    print(f'已验证 {result["verified"]} 篇菜谱，{len(result["categories"])} 个分类。')


if __name__ == '__main__':
    main()
