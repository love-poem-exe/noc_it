import json
import os

def main():
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'sites.json'))
    with open(base, 'r', encoding='utf-8') as f:
        data = json.load(f)

    modified = 0
    for s in data:
        name = s.get('site_name', '')
        if not name.startswith('HUB '):
            s['site_name'] = 'HUB ' + name
            modified += 1

    with open(base, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f'modified={modified}, total={len(data)}')

if __name__ == '__main__':
    main()
