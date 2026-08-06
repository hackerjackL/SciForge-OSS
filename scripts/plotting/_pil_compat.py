"""Pillow >= 10 compatibility shim for the blockdiag family.

Pillow removed ImageFont.getsize()/getsize_multiline(); blockdiag-family
packages (blockdiag/actdiag/seqdiag/nwdiag) still call them.  Importing
this module BEFORE those packages restores equivalent methods so the
engines work on modern Pillow.  Kept in the repo so users get it
out-of-the-box (no site-packages patching).
"""
from PIL import ImageFont

if not hasattr(ImageFont.FreeTypeFont, "getsize"):
    def _getsize(self, text, *args, **kwargs):
        l, t, r, b = self.getbbox(text or "")
        return (r - l, b - t)

    def _getsize_multiline(self, text, *args, **kwargs):
        spacing = kwargs.get("spacing", 4)
        wmax = htot = 0
        for i, line in enumerate((text or "").split("\n")):
            l, t, r, b = self.getbbox(line)
            wmax = max(wmax, r - l)
            htot += (b - t) + (spacing if i else 0)
        return (wmax, htot)

    ImageFont.FreeTypeFont.getsize = _getsize
    ImageFont.FreeTypeFont.getsize_multiline = _getsize_multiline
