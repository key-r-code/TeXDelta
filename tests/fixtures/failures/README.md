# Failure fixtures

These original synthetic inputs exercise deterministic error paths. The root-escape test creates its symlink dynamically because a portable repository cannot contain a symlink to a test runner's temporary parent. The compilation-fallback path is driven by the basic fixture with the first compiler call replaced by a controlled failure.
