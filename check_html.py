import re

with open('pharma_trials_dashboard.html', encoding='utf-8') as f:
    content = f.read()

x_matches = re.findall(r'"x":\[([^\]]{1,300})\]', content)[:3]
y_matches = re.findall(r'"y":\[([^\]]{1,300})\]', content)[:3]

print('File size:', len(content), 'bytes')
print('Has plotly CDN:', 'cdn.plot.ly' in content)
print('Has plotly script:', 'plotly' in content[:500])

print('\nFirst 3 X arrays in HTML:')
for x in x_matches:
    print(' ', x[:200])

print('\nFirst 3 Y arrays in HTML:')
for y in y_matches:
    print(' ', y[:200])
