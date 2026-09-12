# Architecture

TeXDelta is a staged command-line pipeline:

1. `workspace.py` validates roots and copies projects into isolated temporary directories.
2. `toolchain.py` probes pdfLaTeX, BibTeX, Perl, latexpand, and latexdiff capabilities.
3. `latex.py` compiles sources, produces and expands BBL files, flattens nested inputs, and captures graphics in document order.
4. `figures.py` parses figure environments; `matching.py` pairs only sufficiently supported candidates.
5. `appendix.py` copies referenced assets into content-addressed paths and produces accessible comparison markup.
6. `pipeline.py` invokes latexdiff and compiles up to three passes, with bounded math and abstract fallbacks.
7. `report.py` records stages, diagnostics, hashes, and matching evidence; `output.py` atomically promotes the completed bundle.

Build work happens outside the destination. Successful outputs omit raw stage logs; failed builds retain a diagnostic directory when possible. A dependency fingerprint in `report.json` enables reuse unless `--rebuild` is supplied.

Only the CLI, TOML schema, JSON report schema, and output layout are compatibility surfaces during the source preview. Python modules under `texdelta` are internal.

TeXDelta does not execute a security sandbox. It rejects project escapes and disables shell escape by default, but supported inputs are still trusted documents processed by a local TeX installation.
