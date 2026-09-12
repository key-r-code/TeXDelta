# Troubleshooting

## Doctor reports a missing tool

Run `texdelta doctor` and install the named executable through your operating system or TeX distribution. TeXDelta never modifies the TeX installation.

## A file escapes the project root

Pass the actual project boundary with `--old-root` or `--new-root`, then move user-owned inputs inside it. Symlinks that resolve outside the selected root are rejected. Installed TeX packages found through the TeX search path are allowed.

## Citations or references remain unresolved

TeXDelta runs bounded compilation passes and treats remaining undefined citations or references as a failed build. Confirm that BibTeX entries exist, labels are unique, and the original projects compile cleanly with pdfLaTeX.

## Figures appear as separate additions and removals

The automatic evidence was intentionally insufficient. Add a `[[figures.pairs]]` override in `texdelta.toml` and inspect the candidate signals in `report.json`.

## The output directory already exists

Use `--force` only when replacing that exact output is intended. Use `--rebuild` as well when a valid cached result should not be reused.

## A package requires shell escape

Review the project and invoke `--allow-shell-escape` only for trusted inputs. This changes the TeX execution boundary and should not be enabled by default in automation.

For reproducible bugs, attach `report.json`, the retained failure logs, `texdelta doctor` output, and a minimal non-confidential fixture to a GitHub issue.
