// 單張圖片預覽
(function () {
  const input = document.getElementById('file-input');
  const imgEl = document.getElementById('preview-img');
  if (!input || !imgEl) return;

  const box = imgEl.parentElement;
  let currentUrl = null;

  input.addEventListener('change', () => {
    const file = input.files && input.files[0];
    if (!file) { resetPreview(); return; }

    if (!file.type.startsWith('image/')) { alert('請選擇圖片檔'); resetPreview(); return; }
    if (file.size > 5 * 1024 * 1024) { alert('圖片請小於 5MB'); resetPreview(); return; }

    if (currentUrl) URL.revokeObjectURL(currentUrl);
    currentUrl = URL.createObjectURL(file);
    imgEl.src = currentUrl;
    box.classList.add('preview--has-img');
  });

  function resetPreview() {
    if (currentUrl) URL.revokeObjectURL(currentUrl);
    currentUrl = null;
    imgEl.removeAttribute('src');
    box.classList.remove('preview--has-img');
  }

  // 若需要：頁面離開前釋放 URL（避免記憶體浪費）
  window.addEventListener('beforeunload', resetPreview);
})();
