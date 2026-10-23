# CyberGuardian AI Browser Extension

## Overview

The CyberGuardian AI Browser Extension brings real-time security analysis to your browsing experience. Analyze URLs and messages directly from your browser popup without leaving the page you're on.

## Features

- **URL Analysis**: Check links for phishing, malicious content, and suspicious indicators
- **Message Analysis**: Analyze email or SMS text for scam psychology and fraud indicators
- **Instant Results**: Get risk scores, explanations, and detailed threat signals
- **Local Backend Connection**: Configure your CyberGuardian backend server URL
- **Explainable AI**: Understand why each URL or message is flagged with detailed breakdowns

## Installation (Chrome/Chromium)

### Prerequisites
- Chrome, Edge, or another Chromium-based browser
- CyberGuardian AI backend running (default: http://127.0.0.1:8000)

### Steps

1. Extract the extension folder to a location on your computer
2. Open your browser and go to `chrome://extensions/` (or `edge://extensions/`)
3. Enable **Developer mode** (toggle in the top right)
4. Click **Load unpacked**
5. Select the `extension` folder from this repository
6. The CyberGuardian AI icon should now appear in your browser toolbar

### Configuration

1. Click the extension icon in your toolbar
2. Scroll to the bottom of the popup
3. Enter your backend URL (default: `http://127.0.0.1:8000`)
4. Click **Save**

If the backend is running locally and available on the default port, no configuration is needed.

## Usage

### Analyze a URL

1. Click the extension icon
2. The current page's URL will be automatically populated
3. Or manually enter any URL
4. Click **Analyze URL**
5. View results including:
   - Risk score (0-100)
   - Risk category (Legitimate, Suspicious, Phishing)
   - Explainable risk signals
   - Scam psychology triggers

### Analyze a Message

1. Click the extension icon
2. Click the **Message** tab
3. Paste email, SMS, or other text content
4. Click **Analyze Message**
5. Review results with detailed psychological analysis

## Permissions

The extension requests only the minimum necessary permissions:

- **activeTab**: To read the current page URL
- **scripting**: Not used; included for potential future features
- **storage**: To save your backend URL configuration
- **Host permissions**: `http://127.0.0.1:8000/*` and `http://localhost:8000/*` to communicate with the backend

No browsing history is collected. No data is transmitted except explicit analysis requests you initiate.

## Data Privacy

- **No tracking**: The extension does not track your browsing
- **No history collection**: Only URLs and messages you explicitly submit are sent to the backend
- **Local configuration**: Your backend URL is stored locally in the browser
- **No third-party requests**: All requests go to your configured backend only

## Troubleshooting

### "Error: Backend unreachable"

**Solution**: 
1. Ensure the CyberGuardian backend is running
2. Check the backend URL in the extension settings
3. Verify your firewall allows local connections
4. Try `http://localhost:8000` instead of `http://127.0.0.1:8000`

### "Invalid URL format"

**Solution**: Ensure the URL includes the scheme (http:// or https://)

### Icon not appearing

**Solution**: 
1. Check that Developer Mode is enabled
2. Reload the extension (toggle off and on, or close/open settings)
3. Try removing and re-adding the extension

### Backend connection times out

**Solution**:
1. Verify the backend URL is correct in settings
2. Check if the backend server is running: `curl http://127.0.0.1:8000/`
3. Increase timeout by running the backend with higher resource allocation
4. Check local firewall/security software blocking connections

## Limitations

- Backend must be running locally or on an accessible network
- Analysis quality depends on backend model availability
- Large URLs or messages may take longer to analyze
- No authentication support in current version (backend should be on trusted network)

## File Structure

```
extension/
├── manifest.json          # Extension configuration (Manifest V3)
├── popup.html             # Extension popup UI
├── popup.css              # Styling
├── popup.js               # Main extension logic
├── background.js          # Service worker for background tasks
├── icons/
│   ├── icon-16.png
│   ├── icon-48.png
│   └── icon-128.png
├── README.md              # This file
└── generate_icons.py      # Icon generator script
```

## Development

### Modifying the Extension

1. Edit files in the `extension/` folder
2. In Chrome, click the reload button on the extension card in `chrome://extensions/`
3. Changes take effect immediately

### Common Modifications

**Change backend URL default**:
Edit `popup.js` line 4:
```javascript
const DEFAULT_BACKEND_URL = 'http://your-server:8000';
```

**Add new analysis mode**:
1. Add button in `popup.html`
2. Add mode handler in `popup.js`
3. Add display function for results

## Performance

- First analysis: ~500ms - 2s (depends on backend)
- Subsequent identical analyses: ~200ms - 500ms
- Results are not cached between sessions

## Security Considerations

- The extension communicates only with your configured backend
- No authentication is implemented; ensure backend is on a trusted network
- Submitted data includes URLs and message text; treat as potentially sensitive
- Extension does not store analysis results permanently

## Future Enhancements

- Automatic URL checking on page load
- Right-click context menu for quick analysis
- Dark mode toggle
- Analysis history in extension storage
- Batch analysis of multiple URLs

## Support

For issues or feature requests:
1. Check troubleshooting section above
2. Verify backend is running and accessible
3. Check browser console for error messages (F12 → Console)
4. Review backend logs for analysis errors

## License

Part of the CyberGuardian AI project. See main repository for license details.
