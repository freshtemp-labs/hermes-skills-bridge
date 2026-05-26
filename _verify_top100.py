import json
with open('top100.json') as f:
    data = json.load(f)
count = len(data['skills'])
print(f'Valid JSON with {count} skills')

cats = {}
tags_all = {}
for s in data['skills']:
    c = s['category']
    cats[c] = cats.get(c, 0) + 1
    for t in s.get('tags', []):
        tags_all[t] = tags_all.get(t, 0) + 1

print(f'Categories: {cats}')
print(f'Tags: {tags_all}')

# Verify all required fields
required = ['name', 'description', 'category', 'tags', 'popularity_score']
missing = False
for i, s in enumerate(data['skills']):
    for f in required:
        if f not in s:
            print(f'  MISSING {f} in skill #{i+1} ({s.get("name", "?")})')
            missing = True
if not missing:
    print('All skills have complete fields ✓')

# Verify popularity_score range
for s in data['skills']:
    p = s.get('popularity_score', 0)
    if not (0 <= p <= 1):
        print(f'  INVALID popularity_score {p} in {s["name"]}')
print('All popularity_scores in range [0,1] ✓')

# Print top 10 by popularity
sorted_skills = sorted(data['skills'], key=lambda x: x['popularity_score'], reverse=True)
print(f'\nTop 10 by popularity:')
for s in sorted_skills[:10]:
    print(f'  {s["name"]:30s} {s["popularity_score"]:.2f}  [{", ".join(s["tags"])}]')
