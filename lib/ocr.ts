/** Resize + compress image to stay under Vercel's 4.5MB body limit */
async function compressImage(file: File, maxPx = 1600, quality = 0.82): Promise<Blob> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const url = URL.createObjectURL(file);

    img.onload = () => {
      URL.revokeObjectURL(url);

      let { width, height } = img;
      if (width > maxPx || height > maxPx) {
        if (width > height) { height = Math.round((height * maxPx) / width); width = maxPx; }
        else                { width  = Math.round((width  * maxPx) / height); height = maxPx; }
      }

      const canvas = document.createElement('canvas');
      canvas.width = width;
      canvas.height = height;
      canvas.getContext('2d')!.drawImage(img, 0, 0, width, height);
      canvas.toBlob((blob) => blob ? resolve(blob) : reject(new Error('Canvas compression failed')), 'image/jpeg', quality);
    };

    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error('Failed to load image')); };
    img.src = url;
  });
}

export async function processImageWithOCR(imageFile: File): Promise<string> {
  const compressed = await compressImage(imageFile);

  const body = new FormData();
  body.append('image', compressed, 'label.jpg');

  const res = await fetch('/api/ocr', { method: 'POST', body });

  if (!res.ok) {
    // Try to parse error JSON; fall back to status text
    const text = await res.text();
    let message = `Server error ${res.status}`;
    try { message = JSON.parse(text).error ?? message; } catch { message = text.slice(0, 200) || message; }
    throw new Error(message);
  }

  const { text } = await res.json();
  return text as string;
}
