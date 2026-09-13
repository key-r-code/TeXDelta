"""Typed errors and stable process exit codes."""


class TexDeltaError(Exception):
    exit_code = 5


class UsageError(TexDeltaError):
    exit_code = 2


class ToolchainError(TexDeltaError):
    exit_code = 3


class BuildError(TexDeltaError):
    exit_code = 4
