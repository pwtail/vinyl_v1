import re
import shutil
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


def main(out_dir='vinyl_sync/vinyl'):
    pkg = Path(__file__).parent / 'vinyl'
    out_dir = Path(out_dir)
    shutil.copytree(str(pkg), out_dir, dirs_exist_ok=True)
    py_files = Path(out_dir).rglob("*.py")
    for fpath in py_files:
        try:
            replace_file(fpath)
        except SkipFile:
            print(f'Skipped: {fpath}')
            continue


if __name__ == '__main__':
    main()