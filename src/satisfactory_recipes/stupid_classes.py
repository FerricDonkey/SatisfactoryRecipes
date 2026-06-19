"""Some stupid helper classes that I shouldn't have to make."""

from __future__ import annotations

import collections
import collections.abc as cabc
import fractions
import typing as ty


class StupidFrozenDict[K, V](dict[K, V]):
    def __init__(
        self,
        mapping: cabc.Mapping[K, V] | cabc.Iterable[tuple[K, V]] = (),
        /,
        **kwargs: V,
    ) -> None:
        self._frozen = False
        super().__init__(mapping, **kwargs)

        for key, value in tuple(self.items()):
            self[key] = self._freeze_value(value)

        self._frozen = True

    @classmethod
    def _freeze_value(cls, value: ty.Any) -> ty.Any:
        if isinstance(value, list):
            return tuple(value)  # type: ignore
        if isinstance(value, set):
            return frozenset(value)  # type: ignore
        if isinstance(value, dict):
            return cls(value)  # type: ignore
        return value

    def __setitem__(self, key: K, value: V) -> None:
        if self._frozen:
            raise TypeError("NOOOO. Not allowed. That's the whole point")
        super().__setitem__(key, value)

    def __hash__(self) -> int:  # type: ignore
        return hash(tuple(sorted(self.items())))


class ScalableCounter[T](collections.defaultdict[T, fractions.Fraction]):
    """
    defaultdict(fractions.Fraction) whose values can be added/subtracted/scaled.

    Missing keys behave like 0.0, because this is intentionally still a
    defaultdict. Can be frozen for hashability.
    """

    def __init__(
        self,
        mapping: cabc.Mapping[T, fractions.Fraction]
        | cabc.Iterable[tuple[T, fractions.Fraction]] = (),
        /,
        *,
        frozen: bool = False,
        **kwargs: fractions.Fraction,
    ) -> None:
        self._frozen: bool = False
        self._hash: int | None = None

        super().__init__(fractions.Fraction)
        super().update(mapping, **kwargs)

        self._frozen = frozen

    @property
    def frozen(self) -> bool:
        return self._frozen

    def freeze(self) -> ty.Self:
        self._frozen = True
        self._hash = None
        return self

    def frozen_copy(self) -> ty.Self:
        return type(self)(self.items(), frozen=True)

    def unfrozen_copy(self) -> ty.Self:
        return type(self)(self.items(), frozen=False)

    def copy(self) -> ty.Self:
        return type(self)(self.items(), frozen=self._frozen)

    def __copy__(self) -> ty.Self:
        return self.copy()

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_frozen", False) and name != "_hash":
            raise TypeError(f"Called __setattr__ from frozen {type(self).__name__}")
        super().__setattr__(name, value)

    def __setitem__(self, key: T, value: fractions.Fraction) -> None:
        if self._frozen:
            raise TypeError(f"Called __setitem__ from frozen {type(self).__name__}")
        self._hash = None
        super().__setitem__(key, value)

    def __delitem__(self, key: T) -> None:
        if self._frozen:
            raise TypeError(f"Called __delitem__ from frozen {type(self).__name__}")
        self._hash = None
        super().__delitem__(key)

    def clear(self) -> None:
        if self._frozen:
            raise TypeError(f"Called clear from frozen {type(self).__name__}")
        self._hash = None
        super().clear()

    def pop(self, key: T, default: object = ty.cast(object, ...)) -> fractions.Fraction:
        if self._frozen:
            raise TypeError(f"Called pop from frozen {type(self).__name__}")
        self._hash = None

        if default is ...:
            return super().pop(key)

        return super().pop(key, ty.cast(fractions.Fraction, default))

    def popitem(self) -> tuple[T, fractions.Fraction]:
        if self._frozen:
            raise TypeError(f"Called popitem from frozen {type(self).__name__}")
        self._hash = None
        return super().popitem()

    def setdefault(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        key: T,
        default: fractions.Fraction = fractions.Fraction(0, 1),
    ) -> fractions.Fraction:  # type: ignore
        if self._frozen:
            raise TypeError(f"Called setdefault from frozen {type(self).__name__}")
        self._hash = None
        return super().setdefault(key, default)

    def update(  # type: ignore[override]
        self,
        mapping: cabc.Mapping[T, fractions.Fraction]
        | cabc.Iterable[tuple[T, fractions.Fraction]] = (),
        /,
        **kwargs: fractions.Fraction,
    ) -> None:
        if self._frozen:
            raise TypeError(f"Called update from frozen {type(self).__name__}")
        self._hash = None
        super().update(mapping, **kwargs)

    def __ior__(self, other: cabc.Mapping[T, fractions.Fraction]) -> ty.Self:  # type: ignore
        self.update(other)
        return self

    def __hash__(self) -> int:  # type: ignore
        if not self._frozen:
            raise TypeError(
                f"Called __hash__ from non-frozen {type(self).__name__} {self}. "
                "You can freeze first with thing.freeze()."
            )

        if self._hash is None:
            self._hash = hash(tuple(sorted(self.items())))

        return self._hash

    def __add__(self, other: cabc.Mapping[T, fractions.Fraction]) -> ty.Self:
        summed = self.unfrozen_copy()
        summed += other
        return summed

    def __iadd__(self, other: cabc.Mapping[T, fractions.Fraction]) -> ty.Self:
        self._check_mutable_for_inplace()
        for key, val in other.items():
            self[key] += val

        return self

    def __sub__(self, other: cabc.Mapping[T, fractions.Fraction]) -> ty.Self:
        subbed = self.unfrozen_copy()
        subbed -= other
        return subbed

    def __isub__(self, other: cabc.Mapping[T, fractions.Fraction]) -> ty.Self:
        self._check_mutable_for_inplace()
        for key, val in other.items():
            self[key] -= val

        return self

    def __mul__(self, scale: fractions.Fraction) -> ty.Self:
        scaled = self.unfrozen_copy()
        scaled *= scale
        return scaled

    def __rmul__(self, scale: fractions.Fraction) -> ty.Self:
        return self * scale

    def __imul__(self, scale: fractions.Fraction) -> ty.Self:
        self._check_mutable_for_inplace()
        for key in tuple(self):
            self[key] *= scale

        return self

    def __truediv__(self, scale: fractions.Fraction) -> ty.Self:
        scaled = self.unfrozen_copy()
        scaled /= scale
        return scaled

    def __itruediv__(self, scale: fractions.Fraction) -> ty.Self:
        self._check_mutable_for_inplace()
        for key in tuple(self):
            self[key] /= scale

        return self

    def _check_mutable_for_inplace(self) -> None:
        if self._frozen:
            raise TypeError(
                f"inplace operations not supported for frozen {type(self).__name__}"
            )
