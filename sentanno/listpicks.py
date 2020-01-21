#!/usr/bin/env python3

import sys
import os

import json

from standoff import load_standoff


def argparser():
    from argparse import ArgumentParser
    ap = ArgumentParser()
    ap.add_argument('-e', '--encoding', default='utf-8')
    ap.add_argument('file', nargs='+', help='input JSON files')
    return ap


def process(fn, options):
    with open(fn, encoding=options.encoding) as f:
        data = json.load(f)
    doc_id = os.path.splitext(os.path.basename(fn))[0]
    source = data['candidate_source']
    c_id = data['candidate_id']
    c_set = data['candidate_set']
    c_annfn = '{}.{}'.format(os.path.splitext(fn)[0], c_set)
    c_anns = load_standoff(c_annfn, encoding=options.encoding)
    c_ann = [a for a in c_anns if a.id == c_id][0]
    c_type = c_ann.type
    accepted = data.get('accepted', [])
    rejected = data.get('rejected', [])
    if c_set in accepted:
        status = 'accepted'
    elif c_set in rejected:
        status = 'rejected'
    else:
        status = 'unknown'
    print('\t'.join([source, doc_id, c_id, c_type, status]))


def main(argv):
    args = argparser().parse_args(argv[1:])
    for fn in args.file:
        process(fn, args)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
