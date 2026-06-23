import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
RULES_PATH = BASE / 'data' / 'extracted' / 'safety_rules.json'


def match_safety_rule(text: str):
    rules = json.loads(RULES_PATH.read_text(encoding='utf-8'))['rules']
    low = text.lower()
    matches = []
    for r in rules:
        if any(k.lower() in low for k in r['keywords']):
            matches.append(r)
    order = {'emergency': 0, 'urgent': 1, 'warning': 2}
    matches.sort(key=lambda x: order.get(x['level'], 9))
    return matches


if __name__ == '__main__':
    text = input('Câu hỏi / triệu chứng: ')
    matches = match_safety_rule(text)
    if not matches:
        print('No safety rule matched.')
    else:
        r = matches[0]
        print(f"Matched: {r['id']} | level={r['level']}")
        print(r['response_template'])
