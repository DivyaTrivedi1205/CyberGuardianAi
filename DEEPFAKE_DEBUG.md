# Deepfake Analysis Failure — Root Cause Analysis

## HTTP 400 Rejection Paths in `analyze_deepfake_endpoint`

### Path 1: Content-Type Validation (Line 471-475)
```python
if content_type not in allowed_image_types + allowed_video_types:
    raise HTTPException(status_code=400, detail="Unsupported content type: ...")
```
**Trigger:** Browser doesn't send MIME type OR sends incorrect type (e.g., `application/octet-stream`)
**Expected:** `image/jpeg`, `image/png`, `image/webp`, `image/tiff`, `image/bmp`, `video/mp4`, `video/quicktime`, `video/x-msvideo`, `video/webm`

### Path 2: File Size Validation (Line 480-484)
```python
if len(content) > max_size_bytes:
    raise HTTPException(status_code=413, detail="File too large...")
```
**Trigger:** File exceeds `settings.MAX_UPLOAD_SIZE` (default: 10 MB)
**Status Code:** 413 (not 400, so not this)

### Path 3: Filename Validation (Line 489-493)
```python
if not re.match(r"^[a-zA-Z0-9._-]+$", safe_filename):
    raise HTTPException(status_code=400, detail="Invalid filename...")
```
**Trigger:** Filename contains special characters (spaces, unicode, etc.)
**Example:** `my photo.jpg` → ✗ (space not allowed)
**Example:** `photo_2024-10-23.jpg` → ✓ (underscore and hyphen allowed)

---

## Frontend Request Inspection

### Current Frontend Code (App.jsx:367-372)
```javascript
const formData = new FormData()
formData.append('file', deepfakeFile)
const response = await fetch(`${API_BASE_URL}/security/analyze-deepfake`, {
  method: 'POST',
  headers: { Authorization: `Bearer ${window.localStorage.getItem(AUTH_TOKEN_KEY) || ''}` },
  body: formData,
})
```

**Field Name:** `file` ✓ (matches backend `file: UploadFile = File(...)`)
**FormData Handling:** ✓ (correct, not setting Content-Type manually)
**File Object:** `deepfakeFile` — a File object from `<input type="file">`

### Problem: Browser's File MIME Type Detection

When a file is selected via `<input type="file">`, the browser assigns `file.type`:
- **JPG/JPEG:** `image/jpeg` ✓
- **PNG:** `image/png` ✓
- **WEBP:** `image/webp` (sometimes blank ⚠️)
- **MOV/QUICKTIME:** `video/quicktime` ✓
- **MP4:** `video/mp4` ✓
- **Custom extension or unknown format:** `` (empty string)

**Issue:** If browser can't detect MIME type, `file.type` is empty → defaults to `application/octet-stream` → rejected.

---

## Reproduction Steps

1. **Test 1 - Standard JPEG (should work):**
   - Upload a `.jpg` file → Browser sets `content_type = "image/jpeg"` → ✓ passes Path 1

2. **Test 2 - File with spaces in name:**
   - Upload `my photo.jpg` → Filename validation fails at Path 3 → **400 Bad Request**

3. **Test 3 - Unknown format or WebP:**
   - Upload `.webp` or custom format → `file.type = ""` → Backend receives `application/octet-stream` → **400 Bad Request**

---

## Solution

### Root Cause
**Primary:** Filename contains spaces or special characters
**Secondary:** File MIME type not recognized by browser (empty string → `application/octet-stream`)

### Frontend Fix
Add filename sanitization before sending:
```javascript
// Sanitize filename to match backend regex: ^[a-zA-Z0-9._-]+$
const sanitizedName = deepfakeFile.name
  .replace(/\s+/g, '_')  // spaces → underscores
  .replace(/[^a-zA-Z0-9._\-]/g, '')  // remove special chars
  
// Create new File object with sanitized name
const sanitizedFile = new File([deepfakeFile], sanitizedName, { 
  type: deepfakeFile.type 
})

const formData = new FormData()
formData.append('file', sanitizedFile)  // use sanitized file
```

### Backend Fix
Add fallback MIME type detection using file extension:
```python
# If browser didn't detect MIME type, infer from extension
if content_type == "application/octet-stream":
    ext_to_mime = {
        '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
        '.png': 'image/png', '.webp': 'image/webp',
        '.gif': 'image/gif', '.bmp': 'image/bmp',
        '.tiff': 'image/tiff',
        '.mp4': 'video/mp4', '.webm': 'video/webm',
        '.mov': 'video/quicktime', '.avi': 'video/x-msvideo',
    }
    ext = os.path.splitext(safe_filename)[1].lower()
    content_type = ext_to_mime.get(ext, content_type)
```

---

## Files to Change

1. **frontend/src/App.jsx** — Add filename sanitization in `runDeepfakeAnalyzer()`
2. **backend/routes/security.py** — Add MIME type fallback in `analyze_deepfake_endpoint()`
3. **Test file** — Create `test_deepfake_upload.py` with:
   - Valid JPEG upload (should analyze)
   - File with spaces in name (should work after sanitization)
   - Unsupported MIME type (should reject with proper message)

