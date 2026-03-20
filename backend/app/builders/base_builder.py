from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.build_context import BuildContext


class BaseBuilder(ABC):
    @abstractmethod
    def build(self, context: BuildContext, *, minify: bool = True) -> dict:
        raise NotImplementedError

    def _emit_progress(self, context: BuildContext, percent: int, step: str, message: str) -> None:
        if context.progress_callback:
            context.progress_callback(percent, step, message)

    def _check_cancelled(self, context: BuildContext) -> None:
        if context.cancel_check:
            context.cancel_check()
