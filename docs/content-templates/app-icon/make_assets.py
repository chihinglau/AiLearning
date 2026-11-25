import numpy as np
from PIL import Image, ImageDraw

SRC = 'icon_user.png'
a = np.array(Image.open(SRC).convert('RGB')).astype(np.float32)
H, W, _ = a.shape
white = a.mean(axis=2) > 235

# region that held the original "x"
x0, y0, x1, y1 = 993, 362, 1123, 487
pad = 8


def erase(out):
    for y in range(y0 - pad, y1 + pad + 1):
        lp = rp = None
        for x in range(x0 - pad, x0):
            if not white[y, x]:
                lp = a[y, x]; break
        for x in range(x1 + pad, min(W, x1 + pad + 40)):
            if not white[y, x]:
                rp = a[y, x]; break
        if lp is None or rp is None:
            continue
        d = (x1 + pad) - (x0 - pad)
        for x in range(x0 - pad, x1 + pad + 1):
            t = (x - (x0 - pad)) / d
            out[y, x] = lp * (1 - t) + rp * t
    return out


def draw_star(base, cfac, R, cx=1057, cy=424):
    SS = 4
    L = Image.new('L', (W * SS, H * SS), 0)
    d = ImageDraw.Draw(L)
    tips = [(0, -R), (R, 0), (0, R), (-R, 0)]
    pts = []
    for i in range(4):
        t0 = np.array(tips[i], float); t1 = np.array(tips[(i + 1) % 4], float)
        ctrl = (t0 + t1) * cfac
        for j in range(90):
            t = j / 90
            pt = (1 - t) ** 2 * t0 + 2 * (1 - t) * t * ctrl + t ** 2 * t1
            pts.append(((cx + pt[0]) * SS, (cy + pt[1]) * SS))
    d.polygon(pts, fill=255)
    L = L.resize((W, H), Image.LANCZOS)
    gm = (np.array(L).astype(np.float32) / 255.0)[..., None]
    GW = np.array([252, 251, 253], np.float32)
    return base * (1 - gm) + GW * gm


base = erase(a.copy())
master = Image.fromarray(np.clip(draw_star(base.copy(), 0.07, 78), 0, 255).astype(np.uint8))
master.save('icon_master_1536.png')

small = Image.fromarray(np.clip(draw_star(base.copy(), 0.22, 78), 0, 255).astype(np.uint8))
small.save('icon_master_small_1536.png')

# density exports (Android: mdpi48 hdpi72 xhdpi96 xxhdpi144 xxxhdpi192)
sizes = [(48, small), (72, small), (96, master), (144, master), (192, master)]
for s, src in sizes:
    src.resize((s, s), Image.LANCZOS).save(f'exp_{s}.png')

for s in (1024, 512):
    master.resize((s, s), Image.LANCZOS).save(f'exp_{s}.png')

# preview sheet
sheet = Image.new('RGB', (48 + 72 + 96 + 144 + 192 + 1024 + 70, 1024 + 40), (18, 12, 26))
x = 10
for s, _ in sizes:
    im = Image.open(f'exp_{s}.png')
    sheet.paste(im, (x, 1024 - s))
    x += s + 10
sheet.save('preview_all_sizes.png')
print('done', master.size)
