"""Find the navy 'initials' placeholder boxes (flat RGB 39,51,83) on lawmaker cards."""
import numpy as np
from scipy import ndimage

NAVY = np.array([39, 51, 83])


def detect(a):
    """a: HxWx3 uint8 frame. returns [(x0,y0,x1,y1)] in frame pixels."""
    s = a[::2, ::2].astype(np.int16)
    m = (np.abs(s - NAVY).max(axis=2) <= 6)
    if m.mean() < 0.01:
        return []
    m = ndimage.binary_closing(m, iterations=3)
    lab, n = ndimage.label(m)
    out = []
    for i, sl in enumerate(ndimage.find_objects(lab), 1):
        if sl is None:
            continue
        h = sl[0].stop - sl[0].start; w = sl[1].stop - sl[1].start
        if w < 20 or h < 24:
            continue
        r = h / w
        if not 0.85 <= r <= 1.7:
            continue
        fill = (lab[sl] == i).mean()
        if fill < 0.7:
            continue
        out.append((sl[1].start * 2, sl[0].start * 2, sl[1].stop * 2, sl[0].stop * 2))
    return out
