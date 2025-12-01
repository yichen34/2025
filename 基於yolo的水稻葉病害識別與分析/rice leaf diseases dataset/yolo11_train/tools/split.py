import os
import shutil
from sklearn.model_selection import train_test_split

# 路徑設定
src_img_dir = r'C:\Users\user\PycharmProjects\rice leaf diseases dataset\yolo11_train\train\images'
src_lbl_dir = r'C:\Users\user\PycharmProjects\rice leaf diseases dataset\yolo11_train\train\labels'
dst_val_img_dir = r'C:\Users\user\PycharmProjects\rice leaf diseases dataset\yolo11_train\val\images'
dst_val_lbl_dir = r'C:\Users\user\PycharmProjects\rice leaf diseases dataset\yolo11_train\val\labels'
test_size = 0.2  # 20% 當驗證集

# 建立 val 資料夾
for d in [dst_val_img_dir, dst_val_lbl_dir]:
    os.makedirs(d, exist_ok=True)

# 支援多種副檔名
exts = ('.jpg', '.jpeg', '.png')
all_imgs = [f for f in os.listdir(src_img_dir) if f.lower().endswith(exts)]

# 分割
train_imgs, val_imgs = train_test_split(all_imgs, test_size=test_size, random_state=42)
print(f"總共圖片數: {len(all_imgs)}，驗證集: {len(val_imgs)}")

# 複製驗證集資料
for img in val_imgs:
    shutil.copy(os.path.join(src_img_dir, img), os.path.join(dst_val_img_dir, img))
    label = os.path.splitext(img)[0] + '.txt'
    label_path = os.path.join(src_lbl_dir, label)
    if os.path.exists(label_path):
        shutil.copy(label_path, os.path.join(dst_val_lbl_dir, label))

print("分割完成！（複製模式，不刪除原檔）")
