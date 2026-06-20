# Third-Party Notices

Satisfactory Recipes is built with and distributed alongside open-source
software. The following inventory covers the direct runtime and deployment
components expected in the Windows executable. The final compiled artifact
should be inspected before each public release in case its dependency inventory
has changed.

## Runtime Components

- [Python](https://www.python.org/): Python Software Foundation License.
- [Qt](https://www.qt.io/) and
  [Qt for Python / PySide6 / Shiboken6](https://doc.qt.io/qtforpython-6/):
  available under LGPLv3/GPLv3 or applicable commercial terms. This project
  currently intends to use the open-source distribution and must comply with
  its applicable terms.
- [platformdirs](https://github.com/tox-dev/platformdirs): BSD 3-Clause License.
- [Pydantic](https://github.com/pydantic/pydantic): MIT License.
- [pydantic-core](https://github.com/pydantic/pydantic-core): MIT License.
- [annotated-types](https://github.com/annotated-types/annotated-types):
  MIT License.
- [typing-extensions](https://github.com/python/typing_extensions):
  Python Software Foundation License.
- [typing-inspection](https://github.com/pydantic/typing-inspection):
  MIT License.

## Deployment Components

These packages participate in producing or supporting the one-file executable.
They are listed conservatively even when a component may remain build-time-only.

- [Nuitka](https://github.com/Nuitka/Nuitka): Apache License 2.0.
- [ordered-set](https://github.com/rspeer/ordered-set): MIT License.
- [python-zstandard](https://github.com/indygreg/python-zstandard):
  BSD 3-Clause License.

Qt and Qt for Python contain additional third-party components. Their notices
are documented in the
[Qt for Python license inventory](https://doc.qt.io/qtforpython-6/licenses.html)
and the Qt documentation shipped with the corresponding Qt version.

The Satisfactory Recipes source code is distributed under the PolyForm
Noncommercial License 1.0.0, as described in the repository README. This notice
is informational and is not a substitute for the complete license terms of any
component.
