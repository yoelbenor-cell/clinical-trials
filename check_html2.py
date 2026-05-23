import re

with open('pharma_trials_dashboard.html', encoding='utf-8') as f:
    content = f.read()

arrays = re.findall(r'"y":\[([^\]]*)\]', content)
print('Total y arrays found:', len(arrays))
for i, a in enumerate(arrays[:5]):
    print(f'  y[{i}]: "{a[:150]}"')

print('Contains 149:', '149' in content)
print('Contains 192:', '192' in content)

# Print first 3000 chars to see structure
print('\n--- First 1000 chars of HTML body ---')
body_start = content.find('<body>')
print(content[body_start:body_start+1000])
