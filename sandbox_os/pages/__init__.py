# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""The pages: every view constructed from the store's lines on demand, every count computed at render, each view also
a file that opens with the server stopped, and served on the loopback address only.

    render(view, workshop, **ids) -> str      a view as one HTML document (workshop: a folder or an open store)
    write_views(workshop, unit=None)          the files: pages/*.html, projects/<unit>/pages/*.html, where-it-stands.md, grants.md
    serve(workshop, port=0)                   the pages on 127.0.0.1, with the desk token and the two posts
    PreviewServer(folder, port=0)             a read-only second server for the thing being made
    url(view, **ids)                          a view's route"""
from sandbox_os.pages import serve as _serving, write as _writing  # loaded first, so `serve` below stays the function
from sandbox_os.pages.views import render, VIEWS  # noqa: F401
from sandbox_os.pages.serve import PreviewServer, first_view  # noqa: F401
from sandbox_os.pages.frame import SERVED


def write_views(workshop, unit=None, **kw):
    return _writing.write_views(workshop, unit, **kw)


def serve(workshop, port=0, **kw):
    return _serving.serve(workshop, port, **kw)


def url(view, **ids):
    if view == "world":
        return "/graph"
    key = ids.get("unit") or ids.get("id") or ("move" if view == "cards" else None) or ids.get("name")
    return "/" if view == "brief" else SERVED.get(view) or f"/{view}" + (f"/{key}" if key else "") + (f"?q={ids['q']}" if ids.get("q") else "")
