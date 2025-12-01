# yolo11_train/tools/force_fix_blast_train.py
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
LBL_DIR = ROOT / "train" / "labels"
IMG_DIR = ROOT / "train" / "images"
IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

# 檔名關鍵字對應到 Blast（class 2）
BLAST_KEYS = ("blast", "leafsmut")

def find_img(stem: str):
    for ext in IMG_EXTS:
        p = IMG_DIR / f"{stem}{ext}"
        if p.exists():
            return p
        p2 = IMG_DIR / f"{stem}{ext.upper()}"
        if p2.exists():
            return p2
    return None

def bbox_to_poly(cx, cy, w, h):
    x1, y1 = cx - w/2, cy - h/2
    x2, y2 = cx + w/2, cy - h/2
    x3, y3 = cx + w/2, cy + h/2
    x4, y4 = cx - w/2, cy + h/2
    return [x1, y1, x2, y2, x3, y3, x4, y4]

def clip01(vals):
    return [max(0.0, min(1.0, v)) for v in vals]

def need_fix(filename_stem: str):
    s = filename_stem.lower()
    return any(k in s for k in BLAST_KEYS)

def main():
    if not LBL_DIR.exists():
        print("❌ 找不到訓練標籤資料夾：", LBL_DIR)
        return

    files = sorted(LBL_DIR.glob("*.txt"))
    fixed_files = 0
    fixed_lines = 0
    blast_lines_after = 0

    for txt in files:
        if not need_fix(txt.stem):
            # 不是 Blast 檔名，原樣保留
            continue

        img = find_img(txt.stem)
        img_w = img_h = None
        if img:
            try:
                with Image.open(img) as im:
                    img_w, img_h = im.size
            except Exception:
                pass

        lines = txt.read_text(encoding="utf-8").splitlines()
        new_lines = []
        changed = False

        for line in lines:
            parts = line.strip().split()
            if not parts:
                continue

            # 解析數字
            try:
                nums = [float(x) for x in parts]
            except ValueError:
                # 非法行跳過
                continue

            # 將類別強制為 2（Blast）
            cls = 2

            # 去掉首欄（原類別），取座標
            coords = nums[1:] if len(nums) > 1 else []

            if len(coords) == 4:
                # bbox -> polygon
                cx, cy, w, h = coords
                if (img_w and img_h) and (cx > 1 or cy > 1 or w > 1 or h > 1):
                    cx, cy, w, h = cx/img_w, cy/img_h, w/img_w, h/img_h
                poly = clip01(bbox_to_poly(cx, cy, w, h))
                coords = poly
                changed = True
                fixed_lines += 1

            elif len(coords) >= 6 and len(coords) % 2 == 0:
                # 看起來是多邊形；若座標 >1 嘗試像素->0~1
                if any(v > 1.0 for v in coords) and img_w and img_h:
                    coords = [coords[i] / (img_w if i % 2 == 0 else img_h) for i in range(len(coords))]
                    coords = clip01(coords)
                    changed = True
            else:
                # 無效座標，跳過
                continue

            # 最低要求：至少 3 對點（6 值），而且偶數個
            if len(coords) >= 6 and len(coords) % 2 == 0:
                blast_lines_after += 1
                new_line = " ".join([str(cls)] + [f"{v:.6f}" for v in coords])
                new_lines.append(new_line)

        if new_lines:
            txt.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            if changed:
                fixed_files += 1

    # 清掉 cache 讓 YOLO 重建
    cache = ROOT / "train" / "labels.cache"
    if cache.exists():
        try:
            cache.unlink()
            print("🧹 已刪除 cache：", cache)
        except Exception as e:
            print("⚠️ 無法刪除 cache：", e)

    print(f"\n📂 {LBL_DIR}")
    print(f"  受影響檔案：{fixed_files}")
    print(f"  修正行數（bbox/像素→多邊形0~1）：{fixed_lines}")
    print(f"  ✅ 修正後 Blast 行數（train）：{blast_lines_after}")

if __name__ == "__main__":
    main()
