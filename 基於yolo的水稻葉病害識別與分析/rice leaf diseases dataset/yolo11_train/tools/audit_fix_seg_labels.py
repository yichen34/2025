# yolo11_train/tools/audit_fix_seg_labels.py
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
LABEL_DIRS = [ROOT / "train" / "labels", ROOT / "val" / "labels"]
IMG_DIRS   = [ROOT / "train" / "images", ROOT / "val" / "images"]

IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

def find_image_for_label(label_path: Path, img_root: Path):
    stem = label_path.stem  # 不帶副檔名
    # 嘗試各種常見影像副檔名
    for ext in IMG_EXTS:
        p = (img_root / f"{stem}{ext}")
        if p.exists():
            return p
    # Roboflow 可能把副檔名轉大寫或大小寫混用
    for ext in list(IMG_EXTS):
        p = (img_root / f"{stem}{ext.upper()}")
        if p.exists():
            return p
    return None

def bbox_to_poly(cx, cy, w, h):
    # cx, cy, w, h (0~1) -> 4 點矩形 (順時鐘)
    x1, y1 = cx - w/2, cy - h/2
    x2, y2 = cx + w/2, cy - h/2
    x3, y3 = cx + w/2, cy + h/2
    x4, y4 = cx - w/2, cy + h/2
    return [x1, y1, x2, y2, x3, y3, x4, y4]

def clip01(xs):
    return [min(1.0, max(0.0, v)) for v in xs]

def audit_and_fix_dir(labels_dir: Path, images_dir: Path, target_cls: int = 2):
    fixed_lines = 0
    dropped_lines = 0
    valid_lines = 0
    files_seen = 0

    for txt in sorted(labels_dir.glob("*.txt")):
        files_seen += 1
        img_path = find_image_for_label(txt, images_dir)
        img_w = img_h = None
        if img_path is not None:
            try:
                with Image.open(img_path) as im:
                    img_w, img_h = im.size
            except Exception:
                pass

        lines = txt.read_text(encoding="utf-8").splitlines()
        new_lines = []
        changed = False

        for line in lines:
            parts = line.strip().split()
            if not parts:
                # 空行丟掉
                continue
            try:
                cls = int(float(parts[0]))
            except ValueError:
                # 首欄不是數字，丟掉
                dropped_lines += 1
                continue

            nums = [float(x) for x in parts[1:]]

            if cls != target_cls:
                # 非 Blast，原樣保留
                new_lines.append(line.strip())
                continue

            # 嘗試修 Blast 行
            repaired = None

            if len(nums) == 4:
                # 可能是 DET: cx cy w h
                cx, cy, w, h = nums
                # 如果像素座標，先正規化
                if (img_w and img_h) and (cx > 1 or cy > 1 or w > 1 or h > 1):
                    cx, cy, w, h = cx / img_w, cy / img_h, w / img_w, h / img_h
                poly = bbox_to_poly(cx, cy, w, h)
                poly = clip01(poly)
                repaired = [cls] + poly

            elif len(nums) >= 6 and len(nums) % 2 == 0:
                # 看起來像多邊形
                # 如果發現有 >1 的值而且有影像尺寸，用像素->0~1 正規化
                if any(v > 1.0 for v in nums) and img_w and img_h:
                    nums = [nums[i] / (img_w if i % 2 == 0 else img_h) for i in range(len(nums))]
                nums = clip01(nums)
                repaired = [cls] + nums

            else:
                # 不合法的 Blast 行，丟棄
                dropped_lines += 1
                continue

            # 檢查最後是否仍為合法多邊形（至少 3 對）
            if len(repaired) >= 1 + 6 and (len(repaired) - 1) % 2 == 0:
                new_lines.append(" ".join(f"{x:.6f}" if i else str(int(x)) for i, x in enumerate(repaired)))
                valid_lines += 1
                changed = True
            else:
                dropped_lines += 1

        if changed:
            txt.write_text("\n".join(new_lines) + ("\n" if new_lines else ""), encoding="utf-8")

    print(f"\n📂 {labels_dir}")
    print(f"  檔案數：{files_seen}")
    print(f"  ✅ 有效 Blast 行：{valid_lines}")
    print(f"  🔧 修復行數：{fixed_lines}（*含上面統計的有效行*）")
    print(f"  ❌ 丟棄行數：{dropped_lines}")
    return valid_lines

def main():
    for ld, idr in zip(LABEL_DIRS, IMG_DIRS):
        if not ld.exists():
            print("❌ 找不到標籤資料夾：", ld)
            continue
        if not idr.exists():
            print("⚠️ 找不到影像資料夾（將無法像素→0~1）：", idr)
        audit_and_fix_dir(ld, idr, target_cls=2)

    # 提醒清 cache
    for c in [ROOT / "train" / "labels.cache", ROOT / "val" / "labels.cache"]:
        if c.exists():
            try:
                c.unlink()
                print("🧹 已刪除 cache：", c)
            except Exception as e:
                print("⚠️ 無法刪除 cache：", c, e)

if __name__ == "__main__":
    main()
