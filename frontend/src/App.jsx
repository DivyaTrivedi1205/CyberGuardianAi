import React, { useEffect, useState } from 'react'
import { apiRequest, readJsonResponse, API_BASE_URL, AUTH_TOKEN_KEY, AUTH_USER_KEY } from './api/client'
import { scorePassword, generatePassword, getPasswordSuggestions } from './utils/helpers'
import { PasswordAnalyzer } from './features/PasswordAnalyzer'

const quickStats = [
  { label: 'Protected sessions', value: '1.8k', detail: '+14% this week' },
  { label: 'Threat detections', value: '94', detail: 'Phishing, SMS, and URLs' },
  { label: 'Risk model uptime', value: '99.98%', detail: 'Last 30 days' },
]

const signals = [
  'Checks password length, complexity, and repetition',
  'Flags common patterns used in credential stuffing',
  'Produces a plain-language risk summary for users',
]

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [showGuestShell, setShowGuestShell] = useState(false)
  const [activePage, setActivePage] = useState('dashboard')
  const [authTab, setAuthTab] = useState('login')
  const [contactMode, setContactMode] = useState('email')
  const [authMethod, setAuthMethod] = useState('Google')
  const [currentUser, setCurrentUser] = useState(null)
  const [identityValue, setIdentityValue] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [authMessage, setAuthMessage] = useState('')
  const [otpSent, setOtpSent] = useState(false)
  const [otpValue, setOtpValue] = useState('')

  // Scan history (all types) — fetched once after login and refreshed after each scan
  const [scanHistory, setScanHistory] = useState([])
  const [urlScanHistory, setUrlScanHistory] = useState([])
  const [messageScanHistory, setMessageScanHistory] = useState([])
  const [deepfakeScanHistory, setDeepfakeScanHistory] = useState([])

  // URL Analyzer States
  const [urlInput, setUrlInput] = useState('')
  const [urlResult, setUrlResult] = useState(null)
  const [isScanningUrl, setIsScanningUrl] = useState(false)

  // Message Analyzer States
  const [messageInput, setMessageInput] = useState('')
  const [messageResult, setMessageResult] = useState(null)
  const [isScanningMessage, setIsScanningMessage] = useState(false)

  // CrowdShield (Community Intelligence) States
  const [communityReports, setCommunityReports] = useState([])
  const [reportType, setReportType] = useState('url')
  const [reportValue, setReportValue] = useState('')
  const [reportDescription, setReportDescription] = useState('')
  const [isReporting, setIsReporting] = useState(false)
  const [communitySearchQuery, setCommunitySearchQuery] = useState('')
  const [communityLookupResult, setCommunityLookupResult] = useState(null)
  const [isCommunityLookingUp, setIsCommunityLookingUp] = useState(false)

  // Deepfake Analyzer States
  const [deepfakeFile, setDeepfakeFile] = useState(null)
  const [deepfakePreviewUrl, setDeepfakePreviewUrl] = useState(null)
  const [deepfakeResult, setDeepfakeResult] = useState(null)
  const [isScanningDeepfake, setIsScanningDeepfake] = useState(false)

  async function fetchCommunityReports() {
    try {
      const data = await apiRequest('/community/reports')
      setCommunityReports(data)
    } catch (error) {
      console.error('Failed to fetch community reports:', error)
    }
  }

  async function submitCommunityReport(e) {
    if (e) e.preventDefault()
    if (!reportValue.trim()) return

    setIsReporting(true)
    try {
      await apiRequest('/community/report', {
        method: 'POST',
        body: JSON.stringify({
          indicator_type: reportType,
          indicator_value: reportValue,
          description: reportDescription
        })
      })
      setReportValue('')
      setReportDescription('')
      fetchCommunityReports()
    } catch (error) {
      console.error('Failed to submit community report:', error)
    } finally {
      setIsReporting(false)
    }
  }

  async function handleVerifyReport(id) {
    try {
      await apiRequest(`/community/verify/${id}`, { method: 'POST' })
      fetchCommunityReports()
    } catch (error) {
      console.error('Failed to verify community report:', error)
    }
  }

  async function runCommunityLookup() {
    if (!communitySearchQuery.trim()) return
    setIsCommunityLookingUp(true)
    setCommunityLookupResult(null)
    try {
      const match = communityReports.find(r =>
        r.indicator_value.toLowerCase().includes(communitySearchQuery.toLowerCase()) ||
        communitySearchQuery.toLowerCase().includes(r.indicator_value.toLowerCase())
      )
      setCommunityLookupResult(match ?? { status: 'clean', indicator_value: communitySearchQuery })
    } catch (error) {
      console.error('Reputation lookup failed:', error)
    } finally {
      setIsCommunityLookingUp(false)
    }
  }

  async function fetchHistories(token) {
    const storedToken = token || window.localStorage.getItem(AUTH_TOKEN_KEY)
    if (!storedToken) return
    try {
      const [passHist, urlHist, msgHist, dfHist] = await Promise.all([
        apiRequest('/security/password-scans').catch(() => []),
        apiRequest('/security/url-scans').catch(() => []),
        apiRequest('/security/message-scans').catch(() => []),
        apiRequest('/security/deepfake-scans').catch(() => [])
      ])
      setScanHistory(passHist)
      setUrlScanHistory(urlHist)
      setMessageScanHistory(msgHist)
      setDeepfakeScanHistory(dfHist)
    } catch (error) {
      console.error('Failed to fetch scan histories:', error)
    }
  }

  useEffect(() => {
    fetchCommunityReports()
    const storedToken = window.localStorage.getItem(AUTH_TOKEN_KEY)
    const storedUser = window.localStorage.getItem(AUTH_USER_KEY)

    if (!storedToken) {
      if (storedUser) window.localStorage.removeItem(AUTH_USER_KEY)
      return
    }

    async function restoreSession() {
      try {
        const user = await apiRequest('/auth/me')
        setIsAuthenticated(true)
        setCurrentUser(user)
        setDisplayName(user.name)
        setAuthMethod(user.auth_provider === 'google' ? 'Google' : user.identifier_type === 'phone' ? 'Phone OTP' : 'Email OTP')
        setActivePage('dashboard')
        fetchHistories(storedToken)
      } catch {
        window.localStorage.removeItem(AUTH_TOKEN_KEY)
        window.localStorage.removeItem(AUTH_USER_KEY)
      }
    }

    restoreSession()
  }, [])

  async function handleGoogleCredentialResponse(response) {
    if (!response || !response.credential) return
    try {
      const result = await apiRequest('/auth/google', {
        method: 'POST',
        body: JSON.stringify({ credential: response.credential }),
      })
      await persistSession(result.access_token, result.user, 'Google')
    } catch (error) {
      setAuthMessage(error.message)
    }
  }

  useEffect(() => {
    if (!isAuthenticated && !showGuestShell && window.google) {
      const timer = setTimeout(() => {
        const btnEl = document.getElementById('google-signin-btn')
        if (btnEl) {
          window.google.accounts.id.initialize({
            client_id: '48190723181-pf48lpee9226voi06h554qq5r93hchbb.apps.googleusercontent.com',
            callback: handleGoogleCredentialResponse,
          })
          window.google.accounts.id.renderButton(btnEl, { theme: 'outline', size: 'large', width: '100%' })
        }
      }, 150)
      return () => clearTimeout(timer)
    }
  }, [isAuthenticated, showGuestShell])

  async function persistSession(accessToken, user, methodLabel) {
    setIsAuthenticated(true)
    setCurrentUser(user)
    setAuthMethod(methodLabel)
    setDisplayName(user.name)
    setAuthMessage('')
    setOtpSent(false)
    setOtpValue('')
    setActivePage('dashboard')
    window.localStorage.setItem(AUTH_TOKEN_KEY, accessToken)
    window.localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user))
    fetchHistories(accessToken)
  }

  async function handleGoogleClick() {
    try {
      const response = await apiRequest('/auth/google-demo', {
        method: 'POST',
        body: JSON.stringify({
          display_name: displayName.trim() || undefined,
          email: contactMode === 'email' && identityValue.trim() ? identityValue.trim() : undefined,
        }),
      })
      await persistSession(response.access_token, response.user, 'Google')
    } catch (error) {
      setAuthMessage(error.message)
    }
  }

  async function requestOtp() {
    if (authTab === 'signup' && !displayName.trim()) {
      setAuthMessage('Add your name before requesting an OTP.')
      return false
    }
    if (!identityValue.trim()) {
      setAuthMessage(`Enter your ${contactMode === 'phone' ? 'phone number' : 'email address'} first.`)
      return false
    }
    try {
      const response = await apiRequest('/auth/request-otp', {
        method: 'POST',
        body: JSON.stringify({
          identifier: identityValue.trim(),
          contact_mode: contactMode,
          purpose: authTab,
          display_name: authTab === 'signup' ? displayName.trim() : undefined,
        }),
      })
      setAuthMessage(response.message)
      setOtpSent(true)
      return true
    } catch (error) {
      setAuthMessage(error.message)
      return false
    }
  }

  async function handleAuthSubmit(event) {
    event.preventDefault()
    if (!otpSent) {
      await requestOtp()
      return
    }
    if (!otpValue.trim()) {
      setAuthMessage('Enter the OTP you received to continue.')
      return
    }
    try {
      const response = await apiRequest('/auth/verify-otp', {
        method: 'POST',
        body: JSON.stringify({
          identifier: identityValue.trim(),
          contact_mode: contactMode,
          purpose: authTab,
          otp_code: otpValue.trim(),
          display_name: authTab === 'signup' ? displayName.trim() : undefined,
        }),
      })
      await persistSession(response.access_token, response.user, contactMode === 'phone' ? 'Phone OTP' : 'Email OTP')
    } catch (error) {
      setAuthMessage(error.message)
    }
  }

  function switchToLogin() { setAuthTab('login'); setAuthMessage(''); setOtpSent(false); setOtpValue('') }
  function switchToSignup() { setAuthTab('signup'); setAuthMessage(''); setOtpSent(false); setOtpValue('') }
  function handleContinueAsGuest() { setShowGuestShell(true); setAuthMessage('Guest mode is active. Sign in to unlock the protected features.') }
  function returnToDashboard() { setActivePage('dashboard') }

  function signOut() {
    window.localStorage.removeItem(AUTH_TOKEN_KEY)
    window.localStorage.removeItem(AUTH_USER_KEY)
    setIsAuthenticated(false)
    setCurrentUser(null)
    setActivePage('dashboard')
  }

  async function runUrlAnalyzer() {
    if (!urlInput.trim()) return
    setIsScanningUrl(true)
    try {
      const result = await apiRequest('/security/analyze-url', {
        method: 'POST',
        body: JSON.stringify({ url: urlInput }),
      })
      setUrlResult({
        prediction: result.prediction,
        risk_score: result.risk_score,
        features: result.features,
        feedback: result.feedback,
        scam_psychology: result.scam_psychology,
      })
      if (isAuthenticated) fetchHistories()
    } catch (error) {
      console.error('Failed to analyze URL via backend:', error)
      setUrlResult({
        prediction: 'Legitimate',
        risk_score: 15,
        features: {},
        feedback: ['Error performing backend scan. Displaying local fallback safe status.']
      })
    } finally {
      setIsScanningUrl(false)
    }
  }

  async function runMessageAnalyzer() {
    if (!messageInput.trim()) return
    setIsScanningMessage(true)
    try {
      const result = await apiRequest('/security/analyze-message', {
        method: 'POST',
        body: JSON.stringify({ message: messageInput }),
      })
      setMessageResult({
        prediction: result.prediction,
        risk_score: result.risk_score,
        feedback: result.feedback,
        scam_psychology: result.scam_psychology,
      })
      if (isAuthenticated) fetchHistories()
    } catch (error) {
      console.error('Failed to analyze message via backend:', error)
      setMessageResult({
        prediction: 'Legitimate',
        risk_score: 10,
        feedback: ['Error performing backend scan. Displaying local fallback safe status.']
      })
    } finally {
      setIsScanningMessage(false)
    }
  }

  async function runDeepfakeAnalyzer() {
    if (!deepfakeFile) return
    setIsScanningDeepfake(true)
    try {
      const formData = new FormData()
      formData.append('file', deepfakeFile)
      const response = await fetch(`${API_BASE_URL}/security/analyze-deepfake`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${window.localStorage.getItem(AUTH_TOKEN_KEY) || ''}` },
        body: formData,
      })
      const result = await readJsonResponse(response)
      if (!response.ok) throw new Error(result?.detail || result?.message || 'Deepfake analysis failed.')
      setDeepfakeResult({
        file_name: result.file_name,
        file_type: result.file_type,
        prediction: result.prediction,
        risk_score: result.risk_score,
        features: result.features,
        feedback: result.feedback,
        metadata: result.metadata
      })
      if (isAuthenticated) fetchHistories()
    } catch (error) {
      console.error('Failed to analyze deepfake via backend:', error)
      setDeepfakeResult({
        file_name: deepfakeFile.name,
        file_type: deepfakeFile.type.includes('video') ? 'video' : 'image',
        prediction: 'Authentic',
        risk_score: 12,
        features: {},
        feedback: ['Error executing backend deepfake scan. Displaying local authentic status.'],
        metadata: { file_size_bytes: deepfakeFile.size }
      })
    } finally {
      setIsScanningDeepfake(false)
    }
  }

  function handleContactModeChange(mode) { setContactMode(mode); setAuthMessage(''); setOtpSent(false); setOtpValue('') }

  function handleDeepfakeFileChange(file) {
    if (!file) return
    setDeepfakeFile(file)
    setDeepfakeResult(null)
    if (deepfakePreviewUrl) URL.revokeObjectURL(deepfakePreviewUrl)
    setDeepfakePreviewUrl(URL.createObjectURL(file))
  }

  // ── Navigation ───────────────────────────────────────────────────────────

  function renderSidebarNav() {
    return (
      <nav className="sidebar-nav" aria-label="Primary">
        <button type="button" className={`sidebar-nav-button ${activePage === 'dashboard' ? 'active' : ''}`} onClick={() => setActivePage('dashboard')}>Dashboard</button>
        <button type="button" className={`sidebar-nav-button ${activePage === 'password-analyzer' ? 'active' : ''}`} onClick={() => setActivePage('password-analyzer')}>Password Analyzer</button>
        <button type="button" className={`sidebar-nav-button ${activePage === 'url-analyzer' ? 'active' : ''}`} onClick={() => setActivePage('url-analyzer')}>URL Risk Analyzer</button>
        <button type="button" className={`sidebar-nav-button ${activePage === 'message-analyzer' ? 'active' : ''}`} onClick={() => setActivePage('message-analyzer')}>Message Analyzer</button>
        <button type="button" className={`sidebar-nav-button ${activePage === 'deepfake-analyzer' ? 'active' : ''}`} onClick={() => setActivePage('deepfake-analyzer')}>Deepfake Analyzer</button>
        <button type="button" className={`sidebar-nav-button ${activePage === 'crowdshield' ? 'active' : ''}`} onClick={() => { setActivePage('crowdshield'); fetchCommunityReports() }}>CrowdShield Feed</button>
        <button type="button" className="sidebar-nav-button" onClick={signOut}>Sign out</button>
      </nav>
    )
  }

  function renderTopNavbar(isGuest = false) {
    return (
      <nav className="top-navbar" aria-label="Primary Navigation">
        <div className="top-navbar-brand">
          <span className="top-navbar-mark">CG</span>
          <span className="top-navbar-title">CyberGuardian AI</span>
        </div>

        <div className="top-navbar-links">
          {isGuest ? (
            <>
              <a href="#dashboard" className="top-navbar-link active">Dashboard</a>
              <button type="button" className="top-navbar-link" onClick={() => setShowGuestShell(false)}>Authentication</button>
            </>
          ) : (
            <>
              <button type="button" className={`top-navbar-link ${activePage === 'dashboard' ? 'active' : ''}`} onClick={() => setActivePage('dashboard')}>Dashboard</button>
              <button type="button" className={`top-navbar-link ${activePage === 'password-analyzer' ? 'active' : ''}`} onClick={() => setActivePage('password-analyzer')}>Password Analyzer</button>
              <button type="button" className={`top-navbar-link ${activePage === 'url-analyzer' ? 'active' : ''}`} onClick={() => setActivePage('url-analyzer')}>URL Risk Analyzer</button>
              <button type="button" className={`top-navbar-link ${activePage === 'message-analyzer' ? 'active' : ''}`} onClick={() => setActivePage('message-analyzer')}>Message Analyzer</button>
              <button type="button" className={`top-navbar-link ${activePage === 'deepfake-analyzer' ? 'active' : ''}`} onClick={() => setActivePage('deepfake-analyzer')}>Deepfake Analyzer</button>
              <button type="button" className={`top-navbar-link ${activePage === 'crowdshield' ? 'active' : ''}`} onClick={() => { setActivePage('crowdshield'); fetchCommunityReports() }}>CrowdShield Feed</button>
            </>
          )}
        </div>

        <div className="top-navbar-right">
          {isGuest ? (
            <button type="button" className="primary-button" style={{ padding: '8px 16px' }} onClick={() => setShowGuestShell(false)}>Back to Sign In</button>
          ) : (
            <>
              <div className="top-navbar-user">
                <span className="top-navbar-user-name">{currentUser?.name || displayName || 'User'}</span>
                <span className="top-navbar-user-status">● {authMethod} Unlocked</span>
              </div>
              <button type="button" className="top-navbar-signout" onClick={signOut}>Sign Out</button>
            </>
          )}
        </div>
      </nav>
    )
  }

  // ── Views ────────────────────────────────────────────────────────────────

  function renderDashboardView() {
    const liveStats = [
      { label: 'Password Scans Run', value: scanHistory.length, detail: 'Total active checks' },
      { label: 'URL Threats Inspected', value: urlScanHistory.length, detail: 'Total active checks' },
      { label: 'SMS & Texts Analyzed', value: messageScanHistory.length, detail: 'Total active checks' },
    ]

    return (
      <>
        {!isAuthenticated && showGuestShell && (
          <div className="guest-banner">
            <strong>Protected features are disabled.</strong>
            <span>Sign in or register to activate password analysis, scans, and dashboard controls.</span>
          </div>
        )}

        <header className="topbar">
          <div>
            <p className="eyebrow">{!isAuthenticated ? 'Guest mode' : 'Security operations'}</p>
            <h2>{!isAuthenticated ? 'Sign in to unlock the tools' : 'Dark enterprise dashboard'}</h2>
          </div>
          {isAuthenticated && (
            <div style={{ display: 'flex', gap: '8px' }}>
              <button type="button" className="primary-button" onClick={() => setActivePage('url-analyzer')}>Scan URL</button>
              <button type="button" className="secondary-button" onClick={() => setActivePage('message-analyzer')}>Analyze SMS</button>
            </div>
          )}
        </header>

        <section className="hero-card">
          <div>
            <p className="eyebrow">What this platform does</p>
            <h3>Detect phishing, risky credentials, and social engineering with clear explanations.</h3>
            <p className="hero-copy">
              CyberGuardian AI combines machine learning, rules, and risk explanations so users understand the why behind each alert.
            </p>
          </div>
          <div className="hero-panel">
            {signals.map((signal) => (
              <div key={signal} className="signal-row">
                <span className="signal-dot" />
                <span>{signal}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="stats-grid" aria-label="Key metrics">
          {liveStats.map((stat) => (
            <article className="metric-card" key={stat.label}>
              <p>{stat.label}</p>
              <strong>{stat.value}</strong>
              <span>{stat.detail}</span>
            </article>
          ))}
        </section>

        <section className="content-grid">
          <article className="panel auth-panel" id="auth">
            <p className="eyebrow">Authentication</p>
            {isAuthenticated ? (
              <>
                <h3>Signed in and ready.</h3>
                <p>Authenticated as {authMethod}. The protected experience is now available.</p>
                <div className="auth-note">
                  <strong>Access granted</strong>
                  <span>Signed in as {currentUser?.name ?? 'the current user'}. All Phase 2 controls are active.</span>
                </div>
              </>
            ) : (
              <>
                <h3>Go back to the login page.</h3>
                <p>Complete sign-in or registration to unlock the platform.</p>
                <div className="auth-actions">
                  <button type="button" className="primary-button" onClick={() => setShowGuestShell(false)}>Sign in</button>
                  <button type="button" className="secondary-button" onClick={() => setShowGuestShell(false)}>Create account</button>
                </div>
              </>
            )}
          </article>

          <article className="panel history-panel">
            <p className="eyebrow">Recent Activity Log</p>
            <h3>Recent Scans Overview</h3>

            <div style={{ display: 'grid', gap: '10px' }}>
              {urlScanHistory.length > 0 && (
                <div className="history-item" style={{ cursor: 'pointer' }} onClick={() => isAuthenticated && setActivePage('url-analyzer')}>
                  <div className="history-meta">
                    <span className="history-text">{urlScanHistory[0].url}</span>
                    <span className="history-length">Recent URL Scan</span>
                  </div>
                  <div className="history-stats">
                    <span className={`status-pill status-${urlScanHistory[0].prediction.toLowerCase()}`}>{urlScanHistory[0].prediction}</span>
                    <span className="history-score">{urlScanHistory[0].risk_score}/100</span>
                  </div>
                </div>
              )}

              {messageScanHistory.length > 0 && (
                <div className="history-item" style={{ cursor: 'pointer' }} onClick={() => isAuthenticated && setActivePage('message-analyzer')}>
                  <div className="history-meta">
                    <span className="history-text">{messageScanHistory[0].message}</span>
                    <span className="history-length">Recent SMS Scan</span>
                  </div>
                  <div className="history-stats">
                    <span className={`status-pill status-${messageScanHistory[0].prediction.toLowerCase().replace('phishing/spam', 'spam')}`}>{messageScanHistory[0].prediction}</span>
                    <span className="history-score">{messageScanHistory[0].risk_score}/100</span>
                  </div>
                </div>
              )}

              {scanHistory.length > 0 && (
                <div className="history-item" style={{ cursor: 'pointer' }} onClick={() => isAuthenticated && setActivePage('password-analyzer')}>
                  <div className="history-meta">
                    <span className="history-text">•••••••••••• ({scanHistory[0].password_length} chars)</span>
                    <span className="history-length">Recent Password Scan</span>
                  </div>
                  <div className="history-stats">
                    <span className={`status-pill status-${scanHistory[0].grade.toLowerCase()}`}>{scanHistory[0].grade}</span>
                    <span className="history-score">{scanHistory[0].score}/100</span>
                  </div>
                </div>
              )}

              {scanHistory.length === 0 && urlScanHistory.length === 0 && messageScanHistory.length === 0 && (
                <p className="hero-copy">No previous scans found. Select an analyzer to run a check.</p>
              )}
            </div>
          </article>
        </section>
      </>
    )
  }

  function renderUrlAnalyzerView() {
    return (
      <div className="analyzer-page-view">
        <header className="topbar">
          <div>
            <p className="eyebrow">Security tools</p>
            <h2>URL Risk Analyzer</h2>
          </div>
          <button type="button" className="primary-button" onClick={returnToDashboard}>Back to dashboard</button>
        </header>

        <section className="hero-card">
          <div>
            <p className="eyebrow">Check URL Risks</p>
            <h3>Analyze links for phishing, brand spoofs, and redirection traps.</h3>
            <p className="hero-copy">Our machine learning classifier scans the address bar composition and page content to estimate risk scores.</p>
          </div>
          <div className="hero-panel">
            <div className="signal-row"><span className="signal-dot" /><span>Parses IP usage, shortening services, and subdomains.</span></div>
            <div className="signal-row"><span className="signal-dot" /><span>Queries DNS and inspects HTML resources if reachable.</span></div>
          </div>
        </section>

        <section className="analyzer-grid">
          <article className="panel analyzer-form-card">
            <p className="eyebrow">URL Scanner</p>
            <h3>Submit a URL to analyze</h3>

            <label className="field-label" htmlFor="url-input">Web Address / URL</label>
            <input
              id="url-input"
              type="text"
              className="password-input"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              placeholder="https://login.example-security.com/signin"
            />

            <div className="auth-actions">
              <button type="button" className="primary-button" onClick={runUrlAnalyzer} disabled={isScanningUrl}>
                {isScanningUrl ? <span className="loading-spinner" /> : 'Scan URL'}
              </button>
              <button type="button" className="secondary-button" onClick={() => setUrlInput('http://signin-paypal-login.security-verification.com/webapps')}>
                Load Phishing Demo
              </button>
            </div>
          </article>

          <article className="panel analyzer-result-card">
            <p className="eyebrow">Risk Classification</p>
            <h3>{urlResult ? `${urlResult.prediction} Risk` : 'No scan run yet'}</h3>

            {urlResult ? (
              <>
                <div className="score-row analyzer-score-row">
                  <div>
                    <p className="score-label">Risk score</p>
                    <strong className="score-value">{urlResult.risk_score}/100</strong>
                  </div>
                  <div className="score-meter">
                    <span style={{ width: `${urlResult.risk_score}%`, background: urlResult.risk_score >= 70 ? '#ef4444' : urlResult.risk_score >= 35 ? '#f59e0b' : '#22c55e' }} />
                  </div>
                </div>

                <p className="score-label">Explainable risk signals:</p>
                <ul className="feedback-list">
                  {urlResult.feedback.map((item, idx) => (
                    <li key={idx} style={{ color: urlResult.risk_score >= 35 ? '#fca5a5' : '#cbd5e1' }}>{item}</li>
                  ))}
                </ul>

                {urlResult.scam_psychology?.scores && Object.values(urlResult.scam_psychology.scores).some(v => v > 0) && (
                  <div style={{ marginTop: '12px', display: 'grid', gap: '8px' }}>
                    <p className="score-label">Spoofing & Scam Triggers in URL:</p>
                    {Object.entries(urlResult.scam_psychology.scores).map(([trigger, score]) => {
                      if (score === 0) return null
                      const label = trigger.charAt(0).toUpperCase() + trigger.slice(1)
                      return (
                        <div key={trigger} style={{ display: 'grid', gap: '4px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
                            <span>{label} Bait</span>
                            <strong style={{ color: '#fcd34d' }}>{score}%</strong>
                          </div>
                          <div className="score-meter" style={{ height: '6px' }}>
                            <span style={{ width: `${score}%`, background: '#f59e0b' }} />
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}

                {urlResult.features && Object.keys(urlResult.features).length > 0 && (
                  <>
                    <p className="score-label" style={{ marginTop: '10px' }}>Extracted Feature Flags (30 metrics):</p>
                    <div className="features-grid">
                      {Object.entries(urlResult.features).map(([name, val]) => {
                        const statusClass = val === -1 ? 'threat' : val === 0 ? 'suspicious' : 'safe'
                        return (
                          <div key={name} className={`feature-badge ${statusClass}`} title={`${name}: ${val}`}>
                            <span className={`feature-indicator ${statusClass}`} />
                            <span>{name.replace(/_/g, ' ')}</span>
                          </div>
                        )
                      })}
                    </div>
                  </>
                )}
              </>
            ) : (
              <p className="hero-copy">Enter a web link and click Scan URL to display results.</p>
            )}
          </article>
        </section>

        <section className="panel history-panel">
          <p className="eyebrow">Scan History</p>
          <h3>Previous URL Scans</h3>
          {urlScanHistory.length > 0 ? (
            <div className="history-list">
              {urlScanHistory.map((scan) => {
                const dateStr = new Date(scan.created_at * 1000).toLocaleString()
                return (
                  <div key={scan.id} className="history-item" style={{ cursor: 'pointer' }} onClick={() => {
                    setUrlInput(scan.url)
                    setUrlResult({
                      prediction: scan.prediction,
                      risk_score: scan.risk_score,
                      feedback: [scan.scam_explanations || 'Loaded from scan history.'],
                      features: scan.features || {},
                      scam_psychology: scan.scam_psychology || {}
                    })
                  }}>
                    <div className="history-meta">
                      <span className="history-text" title={scan.url}>{scan.url}</span>
                      <span className="history-date">{dateStr}</span>
                    </div>
                    <div className="history-stats">
                      <span className={`status-pill status-${scan.prediction.toLowerCase()}`}>{scan.prediction} Risk</span>
                      <span className="history-score">{scan.risk_score}/100</span>
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <p className="hero-copy">No previous URL scans found. Run a URL scan above to see history.</p>
          )}
        </section>
      </div>
    )
  }

  function renderMessageAnalyzerView() {
    return (
      <div className="analyzer-page-view">
        <header className="topbar">
          <div>
            <p className="eyebrow">Security tools</p>
            <h2>Message Analyzer</h2>
          </div>
          <button type="button" className="primary-button" onClick={returnToDashboard}>Back to dashboard</button>
        </header>

        <section className="hero-card">
          <div>
            <p className="eyebrow">SMS & Mail Scan</p>
            <h3>Verify message copy for phishing triggers, urgent baits, and scam intent.</h3>
            <p className="hero-copy">Our explainable model checks SMS, email copy, and verification alerts to locate dangerous social engineering hooks.</p>
          </div>
          <div className="hero-panel">
            <div className="signal-row"><span className="signal-dot" /><span>Flags request structure cues, credential verification, and spoof links.</span></div>
            <div className="signal-row"><span className="signal-dot" /><span>Translates underlying scam psychology indicators.</span></div>
          </div>
        </section>

        <section className="analyzer-grid">
          <article className="panel analyzer-form-card">
            <p className="eyebrow">Message Body</p>
            <h3>Analyze text patterns</h3>

            <label className="field-label" htmlFor="message-input">Message Copy</label>
            <textarea
              id="message-input"
              className="analyzer-textarea"
              value={messageInput}
              onChange={(e) => setMessageInput(e.target.value)}
              placeholder="Paste SMS text message body..."
              rows={5}
            />

            <div className="auth-actions">
              <button type="button" className="primary-button" onClick={runMessageAnalyzer} disabled={isScanningMessage}>
                {isScanningMessage ? <span className="loading-spinner" /> : 'Analyze Message'}
              </button>
              <button type="button" className="secondary-button" onClick={() => setMessageInput('URGENT: Your Netflix account will be suspended in 24 hours. Please verify billing details immediately at http://reported-spam-portal-phish-7226.net/login')}>
                Load Urgent Spam Demo
              </button>
            </div>
          </article>

          <article className="panel analyzer-result-card">
            <p className="eyebrow">Risk Classification</p>
            <h3>{messageResult ? `${messageResult.prediction} Risk` : 'No analysis run yet'}</h3>

            {messageResult ? (
              <>
                <div className="score-row analyzer-score-row">
                  <div>
                    <p className="score-label">Risk score</p>
                    <strong className="score-value">{messageResult.risk_score}/100</strong>
                  </div>
                  <div className="score-meter">
                    <span style={{ width: `${messageResult.risk_score}%`, background: messageResult.risk_score >= 70 ? '#ef4444' : messageResult.risk_score >= 35 ? '#f59e0b' : '#22c55e' }} />
                  </div>
                </div>

                <p className="score-label">Explainable risk signals:</p>
                <ul className="feedback-list">
                  {messageResult.feedback.map((item, idx) => (
                    <li key={idx} style={{ color: messageResult.risk_score >= 35 ? '#fca5a5' : '#cbd5e1' }}>{item}</li>
                  ))}
                </ul>

                {messageResult.scam_psychology?.scores && Object.values(messageResult.scam_psychology.scores).some(v => v > 0) && (
                  <div style={{ marginTop: '12px', display: 'grid', gap: '8px' }}>
                    <p className="score-label">Social Engineering triggers:</p>
                    {Object.entries(messageResult.scam_psychology.scores).map(([trigger, score]) => {
                      if (score === 0) return null
                      const label = trigger.charAt(0).toUpperCase() + trigger.slice(1)
                      return (
                        <div key={trigger} style={{ display: 'grid', gap: '4px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
                            <span>{label} Pressure</span>
                            <strong style={{ color: '#fcd34d' }}>{score}%</strong>
                          </div>
                          <div className="score-meter" style={{ height: '6px' }}>
                            <span style={{ width: `${score}%`, background: '#f59e0b' }} />
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </>
            ) : (
              <p className="hero-copy">Enter text copy and click Analyze Message to display results.</p>
            )}
          </article>
        </section>

        <section className="panel history-panel">
          <p className="eyebrow">Scan History</p>
          <h3>Previous Message Scans</h3>
          {messageScanHistory.length > 0 ? (
            <div className="history-list">
              {messageScanHistory.map((scan) => {
                const dateStr = new Date(scan.created_at * 1000).toLocaleString()
                return (
                  <div key={scan.id} className="history-item" style={{ cursor: 'pointer' }} onClick={() => {
                    setMessageInput(scan.message)
                    setMessageResult({
                      prediction: scan.prediction,
                      risk_score: scan.risk_score,
                      feedback: [scan.scam_explanations || 'Loaded from history log.'],
                      scam_psychology: scan.scam_psychology || {}
                    })
                  }}>
                    <div className="history-meta">
                      <span className="history-text" title={scan.message}>{scan.message}</span>
                      <span className="history-date">{dateStr}</span>
                    </div>
                    <div className="history-stats">
                      <span className={`status-pill status-${scan.prediction.toLowerCase().replace('phishing/spam', 'spam')}`}>{scan.prediction} Risk</span>
                      <span className="history-score">{scan.risk_score}/100</span>
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <p className="hero-copy">No previous message scans found. Run an SMS scan above to see history.</p>
          )}
        </section>
      </div>
    )
  }

  function renderDeepfakeAnalyzerView() {
    return (
      <div className="analyzer-page-view">
        <header className="topbar">
          <div>
            <p className="eyebrow">Security tools</p>
            <h2>AI Deepfake Image & Video Identifier</h2>
          </div>
          <button type="button" className="primary-button" onClick={returnToDashboard}>Back to dashboard</button>
        </header>

        <section className="hero-card">
          <div>
            <p className="eyebrow">Media Authenticity Check</p>
            <h3>Identify synthetic images and video manipulations.</h3>
            <p className="hero-copy">Our explainable checker inspects binary metadata signatures and performs visual-temporal consistency checks to identify GAN/Diffusion generations and face swaps.</p>
          </div>
          <div className="hero-panel">
            <div className="signal-row"><span className="signal-dot" /><span>Detects embedded AI tool headers (Midjourney, DALL-E, etc.).</span></div>
            <div className="signal-row"><span className="signal-dot" /><span>Validates camera EXIF structures and temporal frame rate continuity.</span></div>
          </div>
        </section>

        <section className="analyzer-grid">
          <article className="panel analyzer-form-card" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <p className="eyebrow">Media Uploader</p>
            <h3>Select Image or Video file</h3>

            <div
              className="dropzone-container"
              style={{ border: '2px dashed #334155', borderRadius: '12px', padding: '24px', textAlign: 'center', background: '#0f172a', cursor: 'pointer', position: 'relative', overflow: 'hidden', minHeight: '200px', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => { e.preventDefault(); const file = e.dataTransfer.files?.[0]; if (file) handleDeepfakeFileChange(file) }}
              onClick={() => document.getElementById('deepfake-file-input').click()}
            >
              <input
                id="deepfake-file-input"
                type="file"
                accept="image/*,video/*"
                style={{ display: 'none' }}
                onChange={(e) => { const file = e.target.files?.[0]; if (file) handleDeepfakeFileChange(file) }}
              />

              {deepfakePreviewUrl ? (
                <div style={{ position: 'relative', width: '100%', maxWidth: '280px', maxHeight: '200px', overflow: 'hidden', borderRadius: '8px' }}>
                  {deepfakeFile.type.includes('video') ? (
                    <video src={deepfakePreviewUrl} style={{ width: '100%', height: 'auto', borderRadius: '8px' }} muted loop playsInline autoPlay />
                  ) : (
                    <img src={deepfakePreviewUrl} alt="Preview" style={{ width: '100%', height: 'auto', borderRadius: '8px' }} />
                  )}
                  {isScanningDeepfake && (
                    <div className="scan-beam" style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '4px', background: 'linear-gradient(90deg, transparent, #ef4444, transparent)', boxShadow: '0 0 8px #ef4444', animation: 'scanMotion 1.5s infinite ease-in-out' }} />
                  )}
                </div>
              ) : (
                <div style={{ pointerEvents: 'none' }}>
                  <svg style={{ width: '48px', height: '48px', color: '#64748b', marginBottom: '8px' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                  </svg>
                  <p style={{ fontSize: '0.9rem', color: '#cbd5e1', fontWeight: 'bold' }}>Drag & Drop file here</p>
                  <p style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '4px' }}>Supports JPG, PNG, WEBP, MP4, MOV, WEBM</p>
                </div>
              )}
            </div>

            {deepfakeFile && (
              <div style={{ fontSize: '0.8rem', color: '#94a3b8', background: '#1e293b', padding: '10px', borderRadius: '8px' }}>
                <div style={{ textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}><strong>Name:</strong> {deepfakeFile.name}</div>
                <div><strong>Size:</strong> {(deepfakeFile.size / 1024 / 1024).toFixed(2)} MB</div>
                <div><strong>Format:</strong> {deepfakeFile.type || 'unknown'}</div>
              </div>
            )}

            <div className="auth-actions">
              <button type="button" className="primary-button" onClick={runDeepfakeAnalyzer} disabled={!deepfakeFile || isScanningDeepfake} style={{ flex: 1 }}>
                {isScanningDeepfake ? <span className="loading-spinner" /> : 'Analyze Media'}
              </button>
              {deepfakeFile && (
                <button type="button" className="secondary-button" onClick={() => {
                  setDeepfakeFile(null)
                  setDeepfakeResult(null)
                  if (deepfakePreviewUrl) URL.revokeObjectURL(deepfakePreviewUrl)
                  setDeepfakePreviewUrl(null)
                }}>
                  Clear File
                </button>
              )}
            </div>
          </article>

          <article className="panel analyzer-result-card">
            <p className="eyebrow">Authenticity Verdict</p>
            <h3>{deepfakeResult ? `${deepfakeResult.prediction}` : 'No scan run yet'}</h3>

            {deepfakeResult ? (
              <>
                <div className="score-row analyzer-score-row">
                  <div>
                    <p className="score-label">Deepfake Risk Probability</p>
                    <strong className="score-value">{deepfakeResult.risk_score}%</strong>
                  </div>
                  <div className="score-meter">
                    <span style={{ width: `${deepfakeResult.risk_score}%`, background: deepfakeResult.risk_score >= 60 ? '#ef4444' : deepfakeResult.risk_score >= 30 ? '#f59e0b' : '#22c55e' }} />
                  </div>
                </div>

                <p className="score-label">Explainable Detection Signals:</p>
                <ul className="feedback-list">
                  {deepfakeResult.feedback.map((item, idx) => (
                    <li key={idx} style={{ color: deepfakeResult.risk_score >= 30 ? '#fca5a5' : '#cbd5e1' }}>{item}</li>
                  ))}
                </ul>

                {deepfakeResult.features && Object.keys(deepfakeResult.features).length > 0 && (
                  <div style={{ marginTop: '14px', display: 'grid', gap: '8px' }}>
                    <p className="score-label">Anomalies Breakdown:</p>
                    {Object.entries(deepfakeResult.features).map(([metric, score]) => (
                      <div key={metric} style={{ display: 'grid', gap: '4px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
                          <span>{metric} anomaly</span>
                          <strong style={{ color: score >= 60 ? '#f87171' : score >= 30 ? '#fbbf24' : '#34d399' }}>{score}%</strong>
                        </div>
                        <div className="score-meter" style={{ height: '6px' }}>
                          <span style={{ width: `${score}%`, background: score >= 60 ? '#ef4444' : score >= 30 ? '#f59e0b' : '#10b981' }} />
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                <div style={{ marginTop: '16px', background: '#0f172a', padding: '12px', borderRadius: '8px', border: '1px solid #1e293b' }}>
                  <p className="score-label" style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#60a5fa', marginBottom: '6px' }}>
                    💡 Verification Recommendations:
                  </p>
                  <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '0.8rem', color: '#94a3b8', display: 'grid', gap: '4px' }}>
                    {deepfakeResult.file_type === 'video' ? (
                      <>
                        <li>Verify the identity of the sender through a separate channel before taking action.</li>
                        <li>Examine eye blink rate; real humans average 15-20 blinks per minute.</li>
                        <li>Look for temporal artifacting and border inconsistencies around the jaw and neck line.</li>
                      </>
                    ) : (
                      <>
                        <li>Look for details that are difficult for current AI models (e.g., mismatched earrings, asymmetric pupils).</li>
                        <li>Perform a reverse image search (e.g., Google Images) to find the original camera source.</li>
                        <li>Look for warped background perspective lines, particularly close to hair or face contours.</li>
                      </>
                    )}
                  </ul>
                </div>
              </>
            ) : (
              <p className="hero-copy">Upload a media file and click Analyze Media to view the authenticity report.</p>
            )}
          </article>
        </section>

        <section className="panel history-panel" style={{ marginTop: '24px' }}>
          <p className="eyebrow">Deepfake Scan History</p>
          <h3>Previous Media Scans</h3>
          {deepfakeScanHistory.length > 0 ? (
            <div className="history-list">
              {deepfakeScanHistory.map((scan) => {
                const dateStr = new Date(scan.created_at * 1000).toLocaleString()
                return (
                  <div key={scan.id} className="history-item" style={{ cursor: 'pointer' }} onClick={() => {
                    setDeepfakeFile({ name: scan.file_name, size: 0, type: scan.file_type === 'video' ? 'video/mp4' : 'image/jpeg' })
                    setDeepfakePreviewUrl(null)
                    setDeepfakeResult({
                      file_name: scan.file_name,
                      file_type: scan.file_type,
                      prediction: scan.prediction,
                      risk_score: scan.risk_score,
                      features: scan.features || {},
                      feedback: ['Loaded from deepfake scan logs history.'],
                      metadata: { file_size_bytes: 0 }
                    })
                  }}>
                    <div className="history-meta">
                      <span className="history-text" title={scan.file_name}>{scan.file_type === 'video' ? '🎥' : '🖼️'} {scan.file_name}</span>
                      <span className="history-date">{dateStr}</span>
                    </div>
                    <div className="history-stats">
                      <span className={`status-pill status-${scan.prediction.toLowerCase().replace(' ', '-')}`}>{scan.prediction}</span>
                      <span className="history-score">{scan.risk_score}% Risk</span>
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <p className="hero-copy">No previous deepfake scans found. Run a check above to see history.</p>
          )}
        </section>
      </div>
    )
  }

  function renderCrowdShieldView() {
    return (
      <div className="analyzer-page-view">
        <header className="topbar">
          <div>
            <p className="eyebrow">Crowdsourced Threat Intel</p>
            <h2>CrowdShield Feed & Registry</h2>
          </div>
          <button type="button" className="primary-button" onClick={returnToDashboard}>Back to dashboard</button>
        </header>

        <section className="hero-card">
          <div>
            <p className="eyebrow">Defending Together</p>
            <h3>Report scams, blacklist phishing links, and upvote verification alerts.</h3>
            <p className="hero-copy">CrowdShield is our shared reputation repository. Reported indicators instantly trigger automated 100/100 score blocklist alerts across our URL and Message scanners.</p>
          </div>
          <div className="hero-panel">
            <div className="signal-row"><span className="signal-dot" /><span>Submit suspicious text structures or domain links below.</span></div>
            <div className="signal-row"><span className="signal-dot" /><span>Promote pending threat items to verified blocklists.</span></div>
          </div>
        </section>

        <section className="analyzer-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
          <article className="panel analyzer-form-card">
            <p className="eyebrow">Report Threat</p>
            <h3>Share malicious indicator</h3>

            <form onSubmit={submitCommunityReport} style={{ display: 'grid', gap: '14px' }}>
              <div>
                <label className="field-label" htmlFor="report-type">Threat Type</label>
                <select id="report-type" value={reportType} onChange={(e) => setReportType(e.target.value)}
                  style={{ width: '100%', background: '#1e293b', border: '1px solid #334155', color: '#cbd5e1', padding: '10px', borderRadius: '8px', outline: 'none', fontSize: '0.9rem' }}>
                  <option value="url">Malicious URL / Link</option>
                  <option value="message">SMS / Email Message Text</option>
                </select>
              </div>

              <div>
                <label className="field-label" htmlFor="report-value">Suspicious Value</label>
                {reportType === 'url' ? (
                  <input id="report-value" type="text" className="password-input" value={reportValue} onChange={(e) => setReportValue(e.target.value)} placeholder="e.g. http://login-paypal-security-verification.com" />
                ) : (
                  <textarea id="report-value" className="analyzer-textarea" value={reportValue} onChange={(e) => setReportValue(e.target.value)} placeholder="Paste suspicious text message body..." rows={4} />
                )}
              </div>

              <div>
                <label className="field-label" htmlFor="report-desc">Description / Notes</label>
                <input id="report-desc" type="text" className="password-input" value={reportDescription} onChange={(e) => setReportDescription(e.target.value)} placeholder="e.g. Netflix login spoof spoofing customer billing details" />
              </div>

              <button type="submit" className="primary-button" style={{ width: '100%' }} disabled={isReporting}>
                {isReporting ? 'Submitting...' : 'Report Threat to CrowdShield'}
              </button>
            </form>
          </article>

          <article className="panel analyzer-form-card">
            <p className="eyebrow">Reputation Lookup</p>
            <h3>Lookup indicator status</h3>

            <div style={{ display: 'grid', gap: '14px' }}>
              <div style={{ display: 'flex', gap: '8px' }}>
                <input
                  type="text"
                  className="password-input"
                  value={communitySearchQuery}
                  onChange={(e) => setCommunitySearchQuery(e.target.value)}
                  placeholder="Enter URL or message snippet to verify..."
                  style={{ flex: 1 }}
                />
                <button type="button" className="primary-button" onClick={runCommunityLookup} disabled={isCommunityLookingUp}>Check Reputation</button>
              </div>

              {communityLookupResult && (
                <div style={{
                  padding: '14px', borderRadius: '8px',
                  background: communityLookupResult.status === 'verified_threat' ? '#451a03' : communityLookupResult.status === 'pending' ? '#3b2203' : '#064e3b',
                  border: '1px solid ' + (communityLookupResult.status === 'verified_threat' ? '#ea580c' : communityLookupResult.status === 'pending' ? '#d97706' : '#059669')
                }}>
                  <strong style={{ display: 'block', fontSize: '0.95rem', color: '#f8fafc' }}>
                    {communityLookupResult.status === 'verified_threat' ? '🚫 BLOCKED THREAT' : communityLookupResult.status === 'pending' ? '⚠️ SUSPICIOUS (Pending Verification)' : '✅ NO ACTIVE BLOCKLIST MATCH'}
                  </strong>
                  <span style={{ fontSize: '0.85rem', color: '#cbd5e1', display: 'block', marginTop: '4px' }}>
                    {communityLookupResult.status === 'clean'
                      ? 'No match in community blocklist feed. Run standard scan to analyze.'
                      : `Description: ${communityLookupResult.description || 'No comments'} | Reports: ${communityLookupResult.reports_count}`}
                  </span>
                </div>
              )}
            </div>
          </article>
        </section>

        <section className="panel history-panel" style={{ marginTop: '24px' }}>
          <p className="eyebrow">Live Feed</p>
          <h3>Recent Blocklist Submissions</h3>

          {communityReports.length > 0 ? (
            <div style={{ overflowX: 'auto', marginTop: '10px' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #334155', color: '#94a3b8' }}>
                    <th style={{ padding: '10px' }}>Type</th>
                    <th style={{ padding: '10px' }}>Indicator Value</th>
                    <th style={{ padding: '10px' }}>Description</th>
                    <th style={{ padding: '10px' }}>Reports</th>
                    <th style={{ padding: '10px' }}>Status</th>
                    <th style={{ padding: '10px', textAlign: 'right' }}>Corroborate</th>
                  </tr>
                </thead>
                <tbody>
                  {communityReports.map((report) => (
                    <tr key={report.id} style={{ borderBottom: '1px solid #1e293b', color: '#cbd5e1' }}>
                      <td style={{ padding: '10px', textTransform: 'uppercase' }}>
                        <span style={{ padding: '3px 8px', borderRadius: '4px', background: report.indicator_type === 'url' ? '#1e1b4b' : '#311042', color: report.indicator_type === 'url' ? '#818cf8' : '#e879f9', fontSize: '0.75rem', fontWeight: 'bold' }}>
                          {report.indicator_type}
                        </span>
                      </td>
                      <td style={{ padding: '10px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '240px' }} title={report.indicator_value}>
                        <code>{report.indicator_value}</code>
                      </td>
                      <td style={{ padding: '10px' }}>{report.description || 'No notes'}</td>
                      <td style={{ padding: '10px', fontWeight: 'bold' }}>{report.reports_count}</td>
                      <td style={{ padding: '10px' }}>
                        <span className={`status-pill status-${report.status === 'verified_threat' ? 'phishing' : 'suspicious'}`}>
                          {report.status === 'verified_threat' ? 'Verified Threat' : 'Pending Verification'}
                        </span>
                      </td>
                      <td style={{ padding: '10px', textAlign: 'right' }}>
                        {report.status === 'pending' ? (
                          <button type="button" onClick={() => handleVerifyReport(report.id)}
                            style={{ padding: '4px 10px', background: '#ea580c', border: 'none', color: '#fff', borderRadius: '4px', cursor: 'pointer', fontSize: '0.75rem', fontWeight: 'bold' }}>
                            Verify Phish
                          </button>
                        ) : (
                          <span style={{ color: '#ef4444', fontWeight: 'bold' }}>✓ Blacklisted</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="hero-copy">No community reports found. Report a threat above to start protecting your community.</p>
          )}
        </section>
      </div>
    )
  }

  // ── Auth page ─────────────────────────────────────────────────────────────

  const authCopy = authTab === 'signup'
    ? { eyebrow: 'Create profile', title: 'Join CyberGuardian AI', copy: 'Create your profile, then verify with OTP or Google to unlock the dashboard.' }
    : { eyebrow: 'Sign in', title: 'Welcome back', copy: 'Enter your email or phone number and we will send a one-time code.' }

  if (!isAuthenticated && !showGuestShell) {
    return (
      <div className="auth-page">
        <section className="auth-hero">
          <div className="auth-hero-brand">
            <p className="eyebrow">CyberGuardian AI</p>
            <div className="auth-brand-row">
              <span className="auth-brand-mark">CG</span>
              <span className="auth-brand-name">CyberGuardian AI</span>
            </div>
            <h1>Sign in to unlock your security dashboard.</h1>
            <p>Use Google, email, phone number, or register a profile. The protected experience stays locked until you authenticate.</p>
          </div>

          <div className="auth-hero-cards">
            <article><strong>Protected scans</strong><span>Unlock password analysis, risk scoring, and future threat tools.</span></article>
            <article><strong>Explainable results</strong><span>See the reason behind every alert and recommendation.</span></article>
            <article><strong>Private sessions</strong><span>Access stays gated until you complete sign-in or registration.</span></article>
          </div>
        </section>

        <section className="auth-panel-shell">
          <div className="auth-panel-card">
            <div className="auth-tab-row" role="tablist" aria-label="Authentication tabs">
              <button type="button" className={`auth-tab ${authTab === 'login' ? 'active' : ''}`} onClick={switchToLogin}>Login</button>
              <button type="button" className={`auth-tab ${authTab === 'signup' ? 'active' : ''}`} onClick={switchToSignup}>Sign up</button>
            </div>

            <div className="auth-panel-header">
              <div className="auth-panel-header-top">
                <p className="eyebrow">{authCopy.eyebrow}</p>
                <h2>{authCopy.title}</h2>
                <p>{authCopy.copy}</p>
              </div>
            </div>

            <div id="google-signin-btn" style={{ marginBottom: '16px', display: 'flex', justifyContent: 'center' }}></div>

            <form className="auth-form" onSubmit={handleAuthSubmit}>
              {authTab === 'signup' && (
                <label className="auth-field">
                  Your name
                  <input type="text" value={displayName} onChange={(event) => setDisplayName(event.target.value)} placeholder="Full name as shown on your profile" autoComplete="name" />
                </label>
              )}

              <div className="auth-contact-switch" role="tablist" aria-label="Contact method">
                <button type="button" className={`auth-mini-switch ${contactMode === 'email' ? 'active' : ''}`} onClick={() => handleContactModeChange('email')}>Email</button>
                <button type="button" className={`auth-mini-switch ${contactMode === 'phone' ? 'active' : ''}`} onClick={() => handleContactModeChange('phone')}>Phone</button>
              </div>

              <label className="auth-field">
                {contactMode === 'phone' ? 'Phone number' : 'Email address'}
                <input
                  type={contactMode === 'phone' ? 'tel' : 'email'}
                  value={identityValue}
                  onChange={(event) => setIdentityValue(event.target.value)}
                  placeholder={contactMode === 'phone' ? '+1 555 010 2040' : 'name@example.com'}
                  autoComplete={contactMode === 'phone' ? 'tel' : 'email'}
                />
              </label>

              {otpSent && (
                <label className="auth-field">
                  OTP
                  <input type="text" value={otpValue} onChange={(event) => setOtpValue(event.target.value)} placeholder="Enter the one-time code" inputMode="numeric" />
                </label>
              )}

              <div className="auth-actions-row">
                <button type="submit" className="primary-button auth-submit-button">{otpSent ? 'Verify OTP' : 'Send OTP'}</button>
                <button type="button" className="ghost-button" onClick={handleContinueAsGuest}>Skip for now</button>
              </div>

              <div className="auth-footer-links">
                <button type="button" className="link-button" onClick={switchToLogin}>Login</button>
                <button type="button" className="link-button" onClick={switchToSignup}>Sign up</button>
              </div>

              {authMessage && <p className="auth-modal-message">{authMessage}</p>}
            </form>
          </div>
        </section>
      </div>
    )
  }

  if (!isAuthenticated && showGuestShell) {
    return (
      <div className="app-shell app-shell--topnav">
        {renderTopNavbar(true)}
        <main className="main-content">{renderDashboardView()}</main>
      </div>
    )
  }

  return (
    <div className="app-shell app-shell--topnav">
      {renderTopNavbar(false)}
      <main className="main-content">
        {activePage === 'dashboard' && renderDashboardView()}
        {activePage === 'password-analyzer' && (
          <PasswordAnalyzer
            onReturn={returnToDashboard}
            onFetchHistory={fetchHistories}
            scanHistory={scanHistory}
          />
        )}
        {activePage === 'url-analyzer' && renderUrlAnalyzerView()}
        {activePage === 'message-analyzer' && renderMessageAnalyzerView()}
        {activePage === 'deepfake-analyzer' && renderDeepfakeAnalyzerView()}
        {activePage === 'crowdshield' && renderCrowdShieldView()}
      </main>
    </div>
  )
}
