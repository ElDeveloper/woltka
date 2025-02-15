# Input files

The input files for Woltka are sequence **alignment** files. The term "alignment" here describes the operation of aligning short sequencing reads against long reference sequences. The basic information an alignment file provides is the **mapping** between queries and subjects. In addition, the position and quality of alignments are available in some formats, which are useful in some applications.

Also check out this [guideline](align.md) for sequence alignment generation.

## Contents

- [Input filepath](#input-filepath)
- [File formats](#file-formats)
- [Filename pattern](#filename-pattern)
- [Sample list](#sample-list)
- [Demultiplexing](#demultiplexing)
- [Subject trimming](#subject-trimming)

## Input filepath

Parameter `--input` or `-i` is to let Woltka know where to find the input alignment file(s). It can be any of the following four scenarios:

1\. A **directory**. Woltka will search this directory for alignment files, and treat each of them as _one sample_. An example is below. If not all files in the directory are alignments, one may specify a filename pattern (see [details](#filename-pattern)) to include alignments only.

```
align/
├── S01.sam.gz
├── S02.sam.gz
└── S03.sam.gz
```

2\. A **mapping file** of sample ID \<tab\> alignment file path. The paths must point to existing files. They can either be full paths, or simply filenames under the same directory as the mapping file. For example, one can place a `map.txt` of the following content to where alignment files are located.

```
S01 <tab> S01.sam.gz
S02 <tab> S02.sam.gz
S03 <tab> S03.sam.gz
...
```

3\. A single **alignment file**. Woltka considers it as a _multiplexed_ alignment file. Sample IDs will be extracted from sequence identifiers (see [demultiplexing](#demultiplexing) below).

- If you don't want demultiplexing (i.e., it is a single-sample file), add `--no-demux` to the command.

4\. "-", representing standard input (**stdin**). Using this method, you can ["pipe"](https://en.wikipedia.org/wiki/Pipeline_(Unix)) alignments generated by another program directly into Woltka. Demultiplexing is on by default (see above). For example, you can do:

```bash
bowtie2 -x db -U input.fq | woltka classify -i - -o output.biom
```

```bash
samtools view input.bam | woltka classify -i - -o output.biom
```

## File formats

Woltka supports the following alignment formats (specified by parameter `--format` or `-f`):

- `map`: A **simple map** in the format of query \<tab\> subject.
- `sam`: [**SAM**](https://en.wikipedia.org/wiki/SAM_(file_format)) format. Supported by multiple tools such as Bowtie2, BWA and Minimap2.
- `b6o`: [**BLAST**](https://www.metagenomics.wiki/tools/blast/blastn-output-format-6) tabular format (i.e., BLAST parameter `-outfmt 6`). Supported by multiple tools such as BLAST, DIAMOND and BURST.

If not specified, Woltka will _automatically_ infer the format of input alignment files.

Other formats may be converted into any of these three formats so that Woltka can parse them. Examples include **BAM**, **CRAM** and **PAF**. Here are example [commands](faq.md#input-files).

Woltka supports and automatically detects common file compression formats including `gzip`, `bzip2` and `xz`. Any input files, including alignment files and database files, can be supplied in any of these three formats. This saves disk space and compute.

## Filename pattern

When Woltka searches a directory specified by `--input`, by default, it considers every file as an alignment file for one sample. The sample ID is automatically extracted from the filename, with filename extension stripped. Compression file extensions are automatically recognized. For example, the sample IDs for `S01.sam` and `S02.m8.gz` are `S01` and `S02`, respectively.

One may restrict this behavior to avoid confusions. One method is to use parameter `--filext` or `-e`. It is a suffix to be stripped from filenames, and the remaining part is considered a sample ID.

  For example, if valid alignment filenames have the pattern of `ID_L001.aln.bz2`, you may specify `-e _L001.aln.bz2`, so that only `ID` is retained, and filenames which do not have this suffix (e.g., `slurm.o123456` or `readme.txt`) are ignored.

A second method is detailed below.

## Sample list

Parameter `--samples` or `-s` is to instruct Woltka which samples are to be included in the analysis, and in which order they should appear in the output feature table. If not specified, all samples will appear in alphabetical order. This feature applies to all three types of `--input` parameters (see [above](#input-filepath)).

It can be a list of sample IDs separated by comma (e.g., `S01,S02,S03...`), if there aren't many IDs to type. Or,

It can point to a file containing sample IDs, one ID per line. Only the first column before \<tab\> is considered. Lines starting with `#` are omitted. Therefore, a **metadata table** may also serve as a valid sample ID list. For examples:

```
S01
S02
S03
...
```

Or:

#SampleID | Age | BMI | Diagnosis
--- | --- | --- | ---
S01 | 25 | 25.0 | Healthy
S02 | 30 | 27.5 | Healthy
S03 | 35 | 32.5 | Sick
... |

## Demultiplexing

Woltka supports convenient demultiplexing. If the input path (specified by `--input` or `-i`) points to a file instead of a directory, Woltka will treat it as a multiplexed alignment file.

Specifically, the program divides sample ID and read ID by the first underscore in each query identifier in the alignment file (i.e., a pattern of `sampleID_readID`).

One may manually switch on or off the demultiplexing function by adding flag `--demux` or `--no-demux` to the command. This is useful when there are several multiplexed alignment files (e.g., each from one sequencing lane) in one **directory**, or the only input alignment **file** provided is not multiplexed but just for a single sample.

Example of a complete command:

```bash
woltka classify \
  --input blast_output/ \
  --format b6o \
  --filext .blast6out.gz \
  --samples ids.txt \
  --no-demux \
  --output profile.biom \
  ...
```

## Subject trimming

The parameter `--trim-sub <delim>` lets Woltka trim subject IDs at the last occurrence of the given delimiter. Examples include trimming off version numbers from NCBI accessions (`--trim-sub .`: `NP_123456.1` => `NP_123456`, trimming off ORF indices from nucleotide sequences (`--trim-sub _`: `Contig_5_20` => `Contig_5`).

This allows flexible adaptation to alternative classification systems without manually editing the alignment files. A use case is the stratified structural/functional classification (see [details](stratify.md)).
