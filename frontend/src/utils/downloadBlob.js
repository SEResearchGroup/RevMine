// Browser-only helper: given a Blob (usually from an axios { responseType: 'blob' }
// request), trigger a file download with the provided filename.
export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

// When `responseType: 'blob'` is used, axios wraps error-response bodies as
// Blobs too — so err.response.data.error is always undefined. This helper
// reads the blob, tries to parse a JSON { error } payload, and returns a
// user-readable message.
export async function readBlobError(error, fallback = "Download failed") {
  try {
    const blob = error?.response?.data;
    if (!blob) return error?.message || fallback;
    if (typeof blob === "string") return blob;
    if (blob.text) {
      const text = await blob.text();
      try {
        const parsed = JSON.parse(text);
        return parsed.error || parsed.detail || text || fallback;
      } catch {
        return text || fallback;
      }
    }
    return error?.message || fallback;
  } catch {
    return fallback;
  }
}
