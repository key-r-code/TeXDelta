# Configuration

TeXDelta looks for `texdelta.toml` in the current directory. Pass `--config PATH` to select another file. Scalar command-line options override TOML settings. Unknown keys and unsupported schema versions are errors.

```toml
schema_version = 1

[build]
style = "underline"          # underline or font-strike
abstract_diff = true
strict_abstract = false
shell_escape = false
figures = true

[figures]
environments = ["figure", "figure*", "wrapfigure"]
layout = "auto"              # auto, columns, or stacked
caption_words = 18
exclude_old = ["fig:logo"]
exclude_new = ["fig:logo"]

[[figures.pairs]]
old = "fig:baseline"
new = "fig:revised"
heading = "Primary result"
layout = "stacked"
```

Pair selectors may be a figure label, referenced graphic name, or normalized graphic path. Overrides are applied before automatic matching. Exclusions accept the same selectors.

Matching proceeds by explicit override, unique referenced-content hash, unique label, unique normalized name supported by caption/order evidence, and finally a mutual-best caption/order score. The report records the signals and confidence. Uncertain candidates are emitted as distinct additions and removals.

Additional figure-like environments can be listed in `environments`. TeXDelta only analyzes `\includegraphics` references inside configured environments; unrelated project images are ignored.

The checked-in report contract is [report-v1.json](../schemas/report-v1.json). Paths in reports are relative and temporary or home-directory paths are redacted.
