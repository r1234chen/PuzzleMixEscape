# Browser runtime / 浏览器运行时

The offline player bundles Pyodide 0.27.7 (Python 3.12.7), its Emscripten runtime, NumPy 2.0.2 and Pillow 10.2.0. [Upstream distribution and per-file checksums](SOURCES.txt). The JavaScript transport embeds the downloaded files as base64 so that selecting a level works when opening the page directly from disk. It does not change their licenses. The original wheels retain their package metadata and notices.

运行时由浏览器在本机执行。压缩载荷只用于静态网页的离线加载，不包含 API key、第三方房屋或实验录像。

- [Pyodide — MPL 2.0](licenses/pyodide-LICENSE.txt) · [corresponding source](https://github.com/pyodide/pyodide/tree/0.27.7)
- [CPython license](licenses/CPython-LICENSE.txt) · [corresponding source](https://github.com/python/cpython/tree/v3.12.7)
- [Emscripten license](licenses/emscripten-LICENSE.txt) · [corresponding source](https://github.com/emscripten-core/emscripten/tree/3.1.58)
- [NumPy source](https://github.com/numpy/numpy/tree/v2.0.2) and [Pillow source](https://github.com/python-pillow/Pillow/tree/10.2.0): see their notices in [licenses](licenses/) and the bundled wheel files.
- The level engine includes the repository's [DejaVu font and notice](licenses/DejaVu-LICENSE.txt).
