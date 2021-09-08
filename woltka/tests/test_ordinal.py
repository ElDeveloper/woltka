#!/usr/bin/env python3

# ----------------------------------------------------------------------------
# Copyright (c) 2020--, Qiyun Zhu.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

"""Unit tests for the ordinal system, as well as a demonstration of how the
system works. See docstrings of `test_match_read_gene`.
"""

from unittest import TestCase, main
from os.path import join, dirname, realpath
from shutil import rmtree
from tempfile import mkdtemp
from io import StringIO
from operator import itemgetter

from woltka.file import openzip
from woltka.align import parse_b6o_line, parse_sam_line
from woltka.ordinal import (
    match_read_gene, ordinal_mapper, ordinal_parser, read_gene_coords,
    calc_gene_lens)


class OrdinalTests(TestCase):
    def setUp(self):
        self.tmpdir = mkdtemp()
        self.datdir = join(dirname(realpath(__file__)), 'data')

    def tearDown(self):
        rmtree(self.tmpdir)

    def test_match_read_gene(self):
        """This test demonstrates how genes and reads are matched in an
        ordinal system.

        Illustration of gene (>) and read (-) locations on a genome (=):

           reads:             ---------r1---------
                                    ---------r2---------
                                        ---------r3---------
                                          ---------r4---------
                                                  ---------r5---------
                                                  ---------r6---------
          genome:  1 ====>>>>>>>>>>>g1>>>>>>>>>>>>===>>>>>>>>>>>>>>g2>> 50

           reads:             ---------r7---------
                                   ---------r8---------
                                                    ------r9------
          genome: 51 >>>>>>>>>>>===>>>>>>>>>>>>>>g3>>>>>>>>>>>>>======= 100
          --------------------------------------------------

        This function finds matching read/gene pairs given their overlap
        is no less than a fraction of alignment length (default: 80%). In this
        example, the matching pairs are:

          r1 - g1  (whole read within gene)
          r5 - g2  (17 / 20 nt within gene, exceeding threshold)
          r6 - g2  (same as above)
          r8 - g3  (whole read within gene)

        """
        # gene table
        genes = [('g1',  5, 29),
                 ('g2', 33, 61),
                 ('g3', 65, 94)]
        # read map
        reads = [('r1', 10, 29),
                 ('r2', 16, 35),
                 ('r3', 20, 39),
                 ('r4', 22, 41),
                 ('r5', 30, 49),
                 ('r6', 30, 49),  # identical
                 ('r7', 60, 79),
                 ('r8', 65, 84),
                 ('r9', 82, 95)]  # shorter

        # flatten lists
        # read length is uniformly 20, default threshold is 80%, so
        # length is 20 * 0.8 = 16
        genes = [x for id_, start, end in genes for x in
                 ((start, None, id_), (end,  False, id_))]
        reads = [x for id_, start, end in reads for x in
                 ((start, 16, id_), (end, 0, id_))]

        queue = sorted(genes + reads, key=itemgetter(0))

        # default
        obs = list(match_read_gene(queue))
        exp = [('r1', 'g1'),
               ('r5', 'g2'),
               ('r6', 'g2'),
               ('r8', 'g3')]
        self.assertListEqual(obs, exp)

        # threashold = 50%, so length is 20 * 0.5 = 10
        for i in range(len(queue)):
            loc = queue[i]
            if loc[1]:
                queue[i] = (loc[0], 10, loc[2])
        obs = list(match_read_gene(queue))
        exp = [('r1', 'g1'),
               ('r2', 'g1'),
               ('r3', 'g1'),
               ('r5', 'g2'),
               ('r6', 'g2'),
               ('r7', 'g3'),
               ('r8', 'g3'),
               ('r9', 'g3')]
        self.assertListEqual(obs, exp)

    def test_ordinal_mapper(self):
        # uses the same example as above, with some noises
        coords, _ = read_gene_coords((
            '>n1',
            'g1	5	29',
            'g2	33	61',
            'g3	65	94',
            'gx	108	135'))
        aln = StringIO('\n'.join((
            'r1	n1	95	20	0	0	1	20	10	29	1	1',
            'r2	n1	95	20	0	0	1	20	16	35	1	1',
            'r3	n1	95	20	0	0	1	20	20	39	1	1',
            'r4	n1	95	20	0	0	20	1	22	41	1	1',
            'r5	n1	95	20	0	0	20	1	30	49	1	1',
            'rx	nx	95	20	0	0	1	20	1	20	1	1',
            'r6	n1	95	20	0	0	1	20	49	30	1	1',
            'r7	n1	95	20	0	0	25	6	79	60	1	1',
            'r8	n1	95	20	0	0	1	20	84	65	1	1',
            'r9	n1	95	20	0	0	1	20	95	82	1	1',
            'rx	nx	95	0	0	0	0	0	0	0	1	1',
            '# end of file')))
        obs = list(ordinal_mapper(aln, coords))[0]
        exp = [('r1', 'g1'),
               ('r5', 'g2'),
               ('r6', 'g2'),
               ('r8', 'g3')]
        self.assertListEqual(list(obs[0]), [x[0] for x in exp])
        self.assertListEqual(list(obs[1]), [{x[1]} for x in exp])

        # specify format
        aln.seek(0)
        obs = list(ordinal_mapper(aln, coords, fmt='b6o'))[0]
        self.assertListEqual(list(obs[0]), [x[0] for x in exp])
        self.assertListEqual(list(obs[1]), [{x[1]} for x in exp])

        # specify chunk size
        aln.seek(0)
        obs = list(ordinal_mapper(aln, coords, n=5))
        self.assertListEqual(list(obs[0][0]), [x[0] for x in exp[:2]])
        self.assertListEqual(list(obs[0][1]), [{x[1]} for x in exp[:2]])
        self.assertListEqual(list(obs[1][0]), [x[0] for x in exp[2:]])
        self.assertListEqual(list(obs[1][1]), [{x[1]} for x in exp[2:]])

        # add prefix
        aln.seek(0)
        obs = list(ordinal_mapper(aln, coords, prefix=True))[0]
        self.assertListEqual(list(obs[0]), [x[0] for x in exp])
        self.assertListEqual(list(obs[1]), [{f'n1_{x[1]}'} for x in exp])

        # specify threshold
        aln.seek(0)
        obs = list(ordinal_mapper(aln, coords, th=0.5))[0]
        exp = [('r1', 'g1'),
               ('r2', 'g1'),
               ('r3', 'g1'),
               ('r5', 'g2'),
               ('r6', 'g2'),
               ('r7', 'g3'),
               ('r8', 'g3'),
               ('r9', 'g3')]
        self.assertListEqual(list(obs[0]), [x[0] for x in exp])
        self.assertListEqual(list(obs[1]), [{x[1]} for x in exp])

    def test_ordinal_parser(self):

        # b6o (BLAST, DIAMOND, BURST, etc.)
        b6o = (
            'S1/1	NC_123456	100	100	0	0	1	100	225	324	1.2e-30	345',
            'S1/2	NC_123456	95	98	2	1	2	99	708	608	3.4e-20	270')
        parser = parse_b6o_line
        obs = ordinal_parser(b6o, parser)
        self.assertListEqual(obs[0], ['S1/1', 'S1/2'])
        self.assertDictEqual(obs[1], {'NC_123456': {0: 100, 1: 98}})
        self.assertDictEqual(obs[2], {'NC_123456': [
            (225, True, False, 0), (324, False, False, 0),
            (608, True, False, 1), (708, False, False, 1)]})

        # sam (BWA, Bowtie2, Minimap2 etc.)
        sam = (
            # SAM header to be ignored
            '@HD	VN:1.0	SO:unsorted',
            # normal, fully-aligned, forward strand
            'S1	77	NC_123456	26	0	100M	*	0	0	*	*',
            # shortened, reverse strand
            'S1	141	NC_123456	151	0	80M	*	0	0	*	*',
            # not perfectly aligned, unpaired
            'S2	0	NC_789012	186	0	50M5I20M5D20M	*	0	0	*	*',
            # unaligned
            'S2	16	*	0	0	*	*	0	0	*	*')
        parser = parse_sam_line
        obs = ordinal_parser(sam, parser)
        self.assertListEqual(obs[0], ['S1/1', 'S1/2', 'S2'])
        self.assertDictEqual(obs[1], {
            'NC_123456': {0: 100, 1: 80},
            'NC_789012': {2: 90}})
        self.assertDictEqual(obs[2], {
            'NC_123456': [(26,  True, False, 0), (125, False, False, 0),
                          (151, True, False, 1), (230, False, False, 1)],
            'NC_789012': [(186, True, False, 2), (280, False, False, 2)]})

    def test_read_gene_coords(self):
        # simple case
        tbl = ('>n1',
               'g1	5	29',
               'g2	33	61',
               'g3	65	94')
        obs, isdup = read_gene_coords(tbl)
        self.assertFalse(isdup)
        exp = {'n1': [
            (5,  None, 'g1'), (29, False, 'g1'),
            (33, None, 'g2'), (61, False, 'g2'),
            (65, None, 'g3'), (94, False, 'g3')]}
        self.assertDictEqual(obs, exp)

        # NCBI accession
        tbl = ('## GCF_000123456\n',
               '# NC_123456\n',
               '1	5	384\n',
               '2	410	933\n',
               '# NC_789012\n',
               '1	912	638\n',
               '2	529	75\n')
        obs, isdup = read_gene_coords(tbl, sort=True)
        self.assertTrue(isdup)
        exp = {'NC_123456': [
            (5,   None, '1'), (384, False, '1'),
            (410, None, '2'), (933, False, '2')],
               'NC_789012': [
            (75,  None, '2'), (529, False, '2'),
            (638, None, '1'), (912, False, '1')]}
        self.assertDictEqual(obs, exp)

        # don't sort
        obs = read_gene_coords(tbl, sort=False)[0]['NC_789012']
        exp = [(638, None, '1'), (912, False, '1'),
               (75,  None, '2'), (529, False, '2')]
        self.assertListEqual(obs, exp)

        # incorrect formats
        # only one column
        msg = 'Cannot extract coordinates from line:'
        with self.assertRaises(ValueError) as ctx:
            read_gene_coords(('hello',))
        self.assertEqual(str(ctx.exception), f'{msg} "hello".')
        # only two columns
        with self.assertRaises(ValueError) as ctx:
            read_gene_coords(('hello\t100',))
        self.assertEqual(str(ctx.exception), f'{msg} "hello\t100".')
        # three columns but 3rd is string
        with self.assertRaises(ValueError) as ctx:
            read_gene_coords(('hello\t100\tthere',))
        self.assertEqual(str(ctx.exception), f'{msg} "hello\t100\tthere".')

        # real coords file
        fp = join(self.datdir, 'function', 'coords.txt.xz')
        with openzip(fp) as f:
            obs, isdup = read_gene_coords(f, sort=True)
        self.assertTrue(isdup)
        self.assertEqual(len(obs), 107)
        obs_ = obs['G000006745']
        self.assertEqual(len(obs_), 7188)
        self.assertTupleEqual(obs_[0], (372,  None,  '1'))
        self.assertTupleEqual(obs_[1], (806,  False, '1'))
        self.assertTupleEqual(obs_[2], (816,  None,  '2'))
        self.assertTupleEqual(obs_[3], (2177, False, '2'))

    def test_calc_gene_lens(self):
        coords = {'NC_123456': [
            (5,   None, '1'), (384, False, '1'),
            (410, None, '2'), (933, False, '2')],
                  'NC_789012': [
            (75,  None, '2'), (529, False, '2'),
            (638, None, '1'), (912, False, '1')]}
        obs = calc_gene_lens(coords, True)
        exp = {'NC_123456_1': 380,
               'NC_123456_2': 524,
               'NC_789012_2': 455,
               'NC_789012_1': 275}
        self.assertDictEqual(obs, exp)

        coords = {'NC_123456': [
            (5,   None,  'NP_135792.1'),
            (384, False, 'NP_135792.1'),
            (410, None,  'NP_246801.2'),
            (933, False, 'NP_246801.2')],
                  'NC_789012': [
            (75,  None,  'NP_258147.1'),
            (529, False, 'NP_258147.1'),
            (638, None,  'NP_369258.2'),
            (912, False, 'NP_369258.2')]}
        obs = calc_gene_lens(coords, False)
        exp = {'NP_135792.1': 380,
               'NP_246801.2': 524,
               'NP_258147.1': 455,
               'NP_369258.2': 275}
        self.assertDictEqual(obs, exp)


if __name__ == '__main__':
    main()
