import os
import re
import sys
from pathlib import Path


class SkipFile(Exception):
    pass


def should_skip_file(line):
    line = line.lower().strip().strip('#').strip()
    return line == 'pragma: i/o specific'


def replace_line(line):
    # assert not 'await ('
    substitutions = (
        (r'await\(', 'Await('),
        ('await ', ''),
        ('async ', ''),
        ('asynccontextmanager', 'contextmanager'),
        #TODO think about async with, async for
    )
    for src, repl in substitutions:
        line = re.sub(src, repl, line)
    return line


def replace_file(fpath):
    new_lines = []
    with Path(fpath).open('r') as f:
        lines = f.readlines()
    if not lines:
        return
    if should_skip_file(lines[0]):
        raise SkipFile
    for line in lines:
        new_lines.append(replace_line(line))
    text = ''.join(new_lines)
    with Path(fpath).open('w') as f:
        f.write(text)


def main(out_dir):
    pkg = Path(__file__).parent / 'vinyl'
    pkg = str(pkg.resolve())
    for root, dirs, files in os.walk(pkg):
        1