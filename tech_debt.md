# Deployment Compatibility Debt

## Purpose

This document records source changes and deployment choices made specifically
to work around incomplete Python 3.14 support in Nuitka. They are not application
requirements and should be reconsidered when Nuitka's Python 3.14 support is
complete.

The behavior described here was observed with Python 3.14 and Nuitka 4.1.2 while
building the Windows one-file executable through `pyside6-deploy`.

## Nuitka Workarounds

### Postpone annotations in every source module

Every Python file under `src/` contains:

```python
from __future__ import annotations
```

CPython 3.14 implements deferred annotation evaluation through PEP 649 and does
not require this import for ordinary forward references. The compiled program,
however, initially evaluated annotations eagerly. It failed during import with:

```text
NameError: name 'MatterState' is not defined
```

Quoting individual return annotations was not sufficient in the deployed
program. Adding the future import consistently across the application allowed
the application modules to load without relying on Nuitka's incomplete default
PEP 649 implementation.

The first known failures were:

- `MatterState.from_doc_form() -> MatterState` in `info_classes.py`;
- `Recipe.create_scaled() -> Recipe` in `info_classes.py`;
- `ProductionChain.to_saveable() -> _ProductionChainSavable` in
  `production_chain.py`.

The import was added to every source module so that newly added annotations do
not silently reintroduce deployment-only failures.

### Use string type parameters in runtime casts

Two PEP 695 generic classes passed their type parameter to `typing.cast`:

```python
ty.cast(T, value)
```

Unlike an annotation, the first argument to `typing.cast` is an ordinary runtime
expression. CPython preserves the generic class's `T` binding, but the compiled
program did not. Selecting an item in the GUI therefore failed with:

```text
NameError: name 'T' is not defined
```

The two calls currently use a string forward reference instead:

```python
ty.cast("T", value)
```

They are located in:

- `gui/dialog_components.py`, in
  `SearchableSelectionList._object_from_item()`;
- `gui/dialogs.py`, in `_SearchDialog._accept_object()`.

The string has no runtime lookup and is still understood by mypy and Pyright.

### Do not enable Nuitka's experimental deferred-annotations mode yet

Nuitka contains an experimental implementation enabled with:

```text
--experimental=deferred-annotations
```

This fixed the application's first forward-reference failure, but broke while
importing `pydantic_core.core_schema`. The deployed executable failed inside
`annotationlib.call_annotate_function` with:

```text
AttributeError: 'dict' object has no attribute '__dict__'
```

Consequently, `pysidedeploy.spec` must not add that flag until the complete
application—including Pydantic—passes the deployment smoke test. The relevant
upstream implementation was introduced in
[Nuitka PR #3880](https://github.com/Nuitka/Nuitka/pull/3880), but remained
experimental in the version tested here.

## How to Remove This Debt

Do not remove the workarounds merely because a newer Nuitka release exists.
First confirm that the release supports the required behavior with Python 3.14.

Use the following sequence:

1. Pin the candidate Nuitka version in both the `deploy` dependency group in
   `pyproject.toml` and the `packages` setting in `pysidedeploy.spec`, then update
   `uv.lock`.
2. Remove `from __future__ import annotations` from one representative module,
   initially `info_classes.py`.
3. Restore the two runtime casts from `ty.cast("T", value)` to
   `ty.cast(T, value)`.
4. Build from a clean deploy-only environment using Python 3.14.
5. Run both deployment checks:

   ```powershell
   .\dist\SatisfactoryRecipes.exe --help
   $env:QT_QPA_PLATFORM = "offscreen"
   .\dist\SatisfactoryRecipes.exe --deployment-smoke-test
   Remove-Item Env:QT_QPA_PLATFORM
   ```

6. Launch the GUI normally and exercise both item and recipe selection dialogs.
   The smoke test does not select list entries and therefore cannot detect the
   generic `T` failure by itself.
7. If those checks pass, remove the future import from the remaining source
   modules, then run pytest, Ruff, mypy, and Pyright before rebuilding once more.

Removal is complete only when all of the following work in the compiled
executable without compatibility imports or string runtime casts:

- self-referential and later-declared annotations;
- PEP 695 generic class type parameters used inside method bodies;
- Pydantic and `pydantic-core` imports;
- the GUI deployment smoke test;
- selecting and accepting both item and recipe dialog entries.

If a stable Nuitka release enables correct deferred annotations by default, no
experimental flag should be necessary. If the flag still exists, test the full
Pydantic import and GUI workflow before adopting it.

## Related Deployment Details That Are Not Nuitka Workarounds

These details were discovered during the same work but should not be conflated
with the annotation compatibility debt:

- `--windows-console-mode=force` is useful only while diagnosing startup
  failures. Restore `--windows-console-mode=disable` for the release build after
  the smoke test and normal launch pass.
- The workflow creates `dist/` before invoking `pyside6-deploy` because its
  finalizer does not create the configured output directory. This is a
  `pyside6-deploy` behavior, not an annotation workaround.
- `pyside6-deploy` places intermediate Nuitka output beside the entry point in a
  `deployment/` directory. It normally deletes that directory after a successful
  final copy; failed finalization can leave it behind.
- The `dumpbin` warning concerns discovery of transitive Qt dependencies. It did
  not cause any of the annotation tracebacks above.
- Compiling `satisfactory_recipes/__main__.py` produces a Nuitka warning about
  package `__main__` semantics. The resulting executable was functional, so this
  warning is currently accepted to avoid maintaining a separate launcher.
- A real `pyside6-deploy` run rewrites parts of `pysidedeploy.spec`, including
  the Python executable, icon, and discovered plugins. Review those generated
  absolute paths and platform-specific values before committing the spec.

## Lower-Risk Fallback

If Python 3.14 deployment remains unstable, Python 3.13 is the practical
fallback recommended by Nuitka's own warning. The application currently appears
to need Python 3.13 features—most notably `copy.replace`—but not a feature unique
to Python 3.14. Adopting this fallback would require changing
`requires-python`, testing the entire project on 3.13, and changing the GitHub
Actions build interpreter. It should be treated as an explicit compatibility
decision rather than an invisible release-only substitution.
