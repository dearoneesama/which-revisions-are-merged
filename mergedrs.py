#!/usr/bin/env python3
# you can provide an argument like `-r 1-40` to only extract revisions r1 to r-40, inclusive
# or default scan all revisions if no argument is provided

import argparse
import functools
import pathlib
import re
import subprocess
from typing import List, NamedTuple, Optional

run_command = functools.partial(subprocess.run, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


class Mergeinfo(NamedTuple):
    path: str
    revbegin: int # inclusive
    revend: int   # inclusive


class Program:

    def __init__(self, svn: str, rooturl: str):
        self.SVN = svn
        self.ROOT_URL = rooturl
        self.OUTDIR = pathlib.Path('mergedrs.out')

    def get_last_rev_number(self) -> int:
        res = run_command([self.SVN, 'info', '--show-item', 'revision', self.ROOT_URL])
        if res.returncode != 0:
            print('cannot get last revision.')
            exit(1)
        return int(res.stdout.strip(b'\n'))


    def get_mergeinfo(self, revision: int) -> Optional[Mergeinfo]:
        proc = run_command([self.SVN, 'diff', self.ROOT_URL, '-c', str(revision)])
        if proc.returncode != 0:
            return None
        match = re.search(b'Merged (.*):r(\d+)-(\d+)', proc.stdout)
        if match is None:
            return None
        return Mergeinfo(match.group(1).decode('utf-8'), int(match.group(2)), int(match.group(3)))


    def get_inrange_revisions(self, mergeinfo: Mergeinfo) -> Optional[List[int]]:
        proc = run_command([self.SVN, 'log', self.ROOT_URL + mergeinfo.path])
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


    def scan(self, since: int, to: int) -> None:
        self.OUTDIR.mkdir(exist_ok=True)
        ofile = (self.OUTDIR / f'merges{since}-{to}.txt').open('w')

        for i in range(since, to+1):
            print(f'trying {i}...')
            mginfo = self.get_mergeinfo(i)
            if mginfo is None:
                continue
            lst = self.get_inrange_revisions(mginfo)
            ofile.write('{} path="{}" revbegin={} revend={} commits={}\n'
                .format(i, mginfo.path, mginfo.revbegin, mginfo.revend,
                    ",".join([str(x) for x in lst]) if lst else ''
            ))

        ofile.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser('wram')
    parser.add_argument('-e', '--executable', type=str, help='path to svn')
    parser.add_argument('-u', '--url', required=True,  help='url to repository')
    parser.add_argument('-r', '--range', type=str, help='revision range xx-yy')
    args = parser.parse_args()

    exe = args.executable or 'svn'
    url = args.url
    p = Program(exe, url)

    rangestr = args.range
    if rangestr is not None:
        since, to = [int(x) for x in rangestr.split('-')]
    else:
        since, to = 1, p.get_last_rev_number()
    p.scan(since, to)
