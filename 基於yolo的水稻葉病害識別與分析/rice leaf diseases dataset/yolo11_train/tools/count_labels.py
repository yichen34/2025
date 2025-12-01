# yolo11_train/tools/count_labels.py
from pathlib import Path
import sys
from collections import Counter, defaultdict

def count_dir(label_dir: Path):
    counts = Counter()
    files = list(label_dir.glob("*.txt"))
    per_class_files = defaultdict(set)  # 每個類別出現過的檔案數（以影像 stem 計）
    total_lines = 0
    bad_lines = 0
    for txt in files:
        stem = txt.stem
        for line in txt.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            # 第一欄應該是 class id
            try:
                cls = int(float(parts[0]))
            except Exception:
                bad_lines += 1
                continue
            counts[cls] += 1
            per_class_files[cls].add(stem)
            total_lines += 1
    return files, counts, per_class_files, total_lines, bad_lines

def pretty_print(root: Path, label_sub="train/labels"):
    d = (root / label_sub).resolve()
    if not d.exists():
        print(f"❌ 找不到資料夾：{d}")
        return
    files, counts, per_file_sets, total, bad = count_dir(d)
    print(f"\n📊 統計：{d}")
    print(f"  標籤檔數：{len(files)}")
    if bad:
        print(f"  ⚠️ 無法解析的行數：{bad}")

    if total == 0:
        print("  （沒有可統計的標註行）")
        return

    # 依 class 排序輸出（0,1,2,...）
    for cls in sorted(counts.keys()):
        inst = counts[cls]
        imgN = len(per_file_sets[cls])
        print(f"  類別 {cls}: {inst} 個標註  | 出現於 {imgN} 張影像")

    # 若發現超出 0/1/2 的類別也列出
    extras = [c for c in counts.keys() if c not in (0,1,2)]
    if extras:
        print("  ⚠️ 發現非 0/1/2 的類別 ID：", sorted(extras))

def main():
    """
    用法：
      1) 直接在專案根目錄下執行（會掃描預設 train/labels、val/labels）
         python yolo11_train/tools/count_labels.py
      2) 或自訂要掃的標籤資料夾：
         python yolo11_train/tools/count_labels.py "C:/path/to/labels"
    """
    if len(sys.argv) > 1:
        # 指定單一路徑時，僅統計該資料夾
        d = Path(sys.argv[1])
        if d.is_dir():
            files, counts, per_file_sets, total, bad = count_dir(d)
            print(f"\n📊 統計：{d.resolve()}")
            print(f"  標籤檔數：{len(files)}")
            if bad:
                print(f"  ⚠️ 無法解析的行數：{bad}")
            if total == 0:
                print("  （沒有可統計的標註行）")
                return
            for cls in sorted(counts.keys()):
                inst = counts[cls]
                imgN = len(per_file_sets[cls])
                print(f"  類別 {cls}: {inst} 個標註  | 出現於 {imgN} 張影像")
            extras = [c for c in counts.keys() if c not in (0,1,2)]
            if extras:
                print("  ⚠️ 發現非 0/1/2 的類別 ID：", sorted(extras))
        else:
            print("❌ 指定的路徑不是資料夾：", d)
        return

    # 預設：掃描專案根目錄下的 train/labels 與 val/labels
    root = Path(__file__).resolve().parents[1]
    pretty_print(root, "train/labels")
    pretty_print(root, "val/labels")

if __name__ == "__main__":
    main()
