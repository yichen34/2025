from pathlib import Path

def convert_detect_to_seg(label_dir):
    label_dir = Path(label_dir)
    fixed = 0
    for txt_file in label_dir.glob("*.txt"):
        lines = txt_file.read_text().strip().splitlines()
        new_lines = []
        for line in lines:
            parts = line.strip().split()
            if len(parts) == 5:
                cls, cx, cy, w, h = parts
                cx, cy, w, h = map(float, (cx, cy, w, h))
                # 計算四個角點 (x,y) → 注意要在 0~1 範圍內
                x1, y1 = cx - w/2, cy - h/2
                x2, y2 = cx + w/2, cy - h/2
                x3, y3 = cx + w/2, cy + h/2
                x4, y4 = cx - w/2, cy + h/2
                new_line = f"{cls} {x1:.6f} {y1:.6f} {x2:.6f} {y2:.6f} {x3:.6f} {y3:.6f} {x4:.6f} {y4:.6f}"
                new_lines.append(new_line)
                fixed += 1
            else:
                new_lines.append(line)
        txt_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    print(f"已修正 {fixed} 個 detect-only 標籤 → segmentation 四邊形")

if __name__ == "__main__":
    root = Path(r"C:\Users\user\PycharmProjects\rice leaf diseases dataset\yolo11_train")
    for split in ["train", "val"]:
        convert_detect_to_seg(root / split / "labels")
