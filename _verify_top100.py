import json
with open('top100.json') as f:
    data = json.load(f)
count = len(data['skills'])
print(f'Valid JSON with {count} skills')
cats = {}
for s in data['skills']:
    c = s['category']
    cats[c] = cats.get(c, 0) + 1
print(f'Categories: {cats}')
