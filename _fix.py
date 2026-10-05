# -*- coding: utf-8 */
import io, re, sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
root = Path('src/categories')

# explanation=( ... , ) with a trailing comma makes a 1-tuple, not a string.
pattern = re.compile(r'(explanation=\(\n(?:[^()]|"(?=\n))*?)",\n(\s*)\),', re.S)

total = 0
for path in sorted(root.glob('*.py')):
    text = path.read_text(encoding='utf-8')
    new, n = pattern.subn(r'\1"\n\2),', text)
    if n:
        path.write_text(new, encoding='utf-8')
        print(f'{path.name}: fixed {n} explanation tuple(s)')
        total += n
print('total fixed:', total)
