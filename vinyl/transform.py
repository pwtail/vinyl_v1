import re
import sys
from pathlib import Path

di = {
    # 'await'
}

def replace(line):
    # assert not 'await ('
    substitutions = (
        (r'await\(', 'Await('),
        ('await ', ''),
        ('async ', ''),
        #TODO think about async with, async for
    )
    for src, repl in substitutions:
        line = re.sub(src, repl, line)
    return line


if __name__ == '__main__':
    fpath = sys.argv[1]
    lines = []
    with Path(fpath).open('r') as f:
        for line in f.readlines():
            lines.append(replace(line))
    text = ''.join(lines)
    with Path(fpath).open('w') as f:
        f.write(text)