# you can provide an argument like 1-40 to only extract revisions r1 to r-40, inclusive
# or default scan all revisions if no argument is provided

import functools
import pathlib
import re
import subprocess
import sys
from typing import List, NamedTuple, Optional


SVN = 'svn'
ROOT_URL = ''

OUTDIR = pathlib.Path('mergedrs.out')


class Mergeinfo(NamedTuple):
    path: str
    revbegin: int # inclusive
    revend: int   # inclusive


run_command = functools.partial(subprocess.run, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def get_last_rev_number() -> int:
    res = run_command([SVN, 'info', '--show-item', 'revision', ROOT_URL])
    if res.returncode != 0:
        print('cannot get last revision.')
        exit(1)
    return int(res.stdout.strip(b'\n'))


def get_mergeinfo(revision: int) -> Optional[Mergeinfo]:
    proc = run_command([SVN, 'diff', ROOT_URL, '-c', str(revision)])
    if proc.returncode != 0:
        return None
    match = re.search(b'Merged (.*):r(\d+)-(\d+)', proc.stdout)
    if match is None:
        return None
    return Mergeinfo(match.group(1).decode('utf-8'), int(match.group(2)), int(match.group(3)))


def get_inrange_revisions(mergeinfo: Mergeinfo) -> Optional[List[int]]:
    proc = run_command([SVN, 'log', ROOT_URL + mergeinfo.path])
    if proc.returncode != 0:
        return None
    nums = []
    for line in proc.stdout.splitlines():
        match = re.search(b'^r(\d+) \|', line)
        if match:
            nums.append(int(match.group(1)))
    res = [x for x in nums if mergeinfo.revbegin <= x <= mergeinfo.revend]
    res.reverse()
    return res


def scan(since: int, to: int) -> None:
    OUTDIR.mkdir(exist_ok=True)
    ofile = (OUTDIR / f'merges{since}-{to}.txt').open('w')

    for i in range(since, to+1):
        print(f'trying {i}...')
        mginfo = get_mergeinfo(i)
        if mginfo is None:
            continue
        lst = get_inrange_revisions(mginfo)
        ofile.write('{} path="{}" revbegin={} revend={} commits={}\n'
            .format(i, mginfo.path, mginfo.revbegin, mginfo.revend,
                ",".join([str(x) for x in lst]) if lst else ''
        ))

    ofile.close()


if __name__ == '__main__':
    if len(sys.argv) == 2:
        arg1 = sys.argv[1].split('-')
        since = int(arg1[0])
        to = int(arg1[1])
    else:
        since = 1
        to = get_last_rev_number()
    scan(since, to)
