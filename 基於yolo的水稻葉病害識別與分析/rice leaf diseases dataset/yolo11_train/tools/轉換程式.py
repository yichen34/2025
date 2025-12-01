# yolo11_train/tools/relabel_and_recount.py
from pathlib import Path
import os
import re

# === 1) 依檔名關鍵字重標籤 (不分大小寫) ===
# 類別定義：0=Bacterialblight, 1=Brownspot, 2=Blast
KEYWORD_MAP = [
    # 長關鍵字先放前面，避免 "brownspot" 被 "brown" 提早匹配
    ("bacterialblight", 0),
    ("brownspot", 1),
    ("blast", 2),

    # 可選的備援關鍵字（若你的命名有用到才會生效）
    ("bacterial", 0),
    ("blight", 0),   # 注意：這是「Bacterial blight」，不要和 blast 混淆
    ("brown", 1),
    ("spot", 1),
]

ROOT = Path(__file__).resolve().parents[1]  # .../yolo11_train
LABEL_DIRS = [ROOT / "train" / "labels", ROOT / "val" / "labels"]

def guess_id_from_name(stem: str):
    name = stem.lower()
    for kw, cid in KEYWORD_MAP:
        if kw in name:
            return cid
    return None

def relabel_dir(d: Path):
    changed_files = 0
    changed_lines = 0
    skipped_files = 0
    unknown_files = []

    for p in sorted(d.glob("*.txt")):
        target = guess_id_from_name(p.stem)
        if target is None:
            unknown_files.append(p.name)
            continue

        lines = p.read_text(encoding="utf-8").splitlines()
        if not lines:
            skipped_files += 1
            continue

        new_lines = []
        file_changed = False
        for line in lines:
            parts = line.strip().split()
            if not parts:
                new_lines.append(line)
                continue
            # 只改第一欄(類別ID)，其餘座標/點位保留
            if parts[0] != str(target):
                parts[0] = str(target)
                file_changed = True
                changed_lines += 1
            new_lines.append(" ".join(parts))

        if file_changed:
            p.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            changed_files += 1

    print(f"\n📂 {d}")
    print(f"  變更檔案：{changed_files}  |  變更行數：{changed_lines}  |  空/略過檔：{skipped_files}")
    if unknown_files:
        print("  ⚠️ 無法從檔名判斷類別（請手動處理或擴充 KEYWORD_MAP）：")
        preview = 20
        for n in unknown_files[:preview]:
            print("   -", n)
        if len(unknown_files) > preview:
            print(f"   ... 其餘 {len(unknown_files)-preview} 個省略")

# === 2) 刪除 Ultralytics 建立的 labels.cache，讓下次訓練強制重掃 ===
def remove_caches():
    removed = 0
    for c in [ROOT / "train" / "labels.cache", ROOT / "val" / "labels.cache"]:
        if c.exists():
            try:
                c.unlink()
                print(f"🧹 已刪除 cache：{c}")
                removed += 1
            except Exception as e:
                print(f"⚠️ 刪除失敗 {c}: {e}")
    if removed == 0:
        print("ℹ️ 未發現可刪除的 cache。")

# === 3) 統計 0/1/2 類別的標註總數 ===
def count_classes(d: Path):
    counts = {0: 0, 1: 0, 2: 0}
    total_files = 0
    for p in d.glob("*.txt"):
        total_files += 1
        for line in p.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\s*(\d+)\b", line)
            if not m:
                continue
            cid = int(m.group(1))
            if cid in counts:
                counts[cid] += 1
    print(f"\n📊 統計：{d}")
    print(f"  檔案數：{total_files}")
    for cid, n in counts.items():
        print(f"  類別 {cid}: {n} 個標註")
    return counts

def main():
    print("=== 依檔名重標籤 ===")
    for d in LABEL_DIRS:
        if not d.exists():
            print(f"❌ 找不到資料夾：{d}")
            continue
        relabel_dir(d)

    print("\n=== 刪除 labels.cache ===")
    remove_caches()

    print("\n=== 重新統計 0/1/2 類別數 ===")
    for d in LABEL_DIRS:
        if d.exists():
            count_classes(d)

    print("\n✅ 完成。下一次訓練時 Ultralytics 會重新掃描標籤。")

if __name__ == "__main__":
    main()
