import functools
import re
import subprocess
import pathlib
from typing import List, NamedTuple, Optional


SVN = 'svn'
ROOT_URL = ''

OUTDIR = pathlib.Path('mergedrs.out')
OUTFILE = OUTDIR / 'merges.txt'


class Mergeinfo(NamedTuple):
    path: str
    revbegin: int # inclusive
    revend: int   # inclusive


run_command = functools.partial(subprocess.run, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def get_last_rev_number() -> int:
    res = run_command([SVN, 'info', '--show-item', 'revision', ROOT_URL])
    if res.returncode != 0:
        exit(1)
    return int(res.stdout.strip(b'\n'))


LAST_REV_NUMBER = get_last_rev_number()


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
    return [x for x in nums if mergeinfo.revbegin <= x <= mergeinfo.revend]


def main():
    OUTDIR.mkdir(exist_ok=True)
    ofile = OUTFILE.open('w')

    for i in range(1, LAST_REV_NUMBER+1):
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
    main()
