import React, { useEffect, useState } from 'react'

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

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'
const AUTH_TOKEN_KEY = 'cyberguardian-auth-token'
const AUTH_USER_KEY = 'cyberguardian-auth-user'

async function readJsonResponse(response) {
  const text = await response.text()

  if (!text) {
    return null
  }

  try {
    return JSON.parse(text)
  } catch {
    return { detail: text }
  }
}

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers ?? {}),
    },
  })

  const payload = await readJsonResponse(response)

  if (!response.ok) {
    const message = payload?.detail || payload?.message || 'Something went wrong.'
    throw new Error(message)
  }

  return payload
}

function scorePassword(value) {
  let score = 0
  const feedback = []

  if (value.length >= 12) score += 30
  else if (value.length >= 8) score += 18
  else if (value.length > 0) feedback.push('Use at least 12 characters for better resilience.')

  if (/[a-z]/.test(value)) score += 10
  else if (value.length > 0) feedback.push('Add lowercase letters.')

  if (/[A-Z]/.test(value)) score += 10
  else if (value.length > 0) feedback.push('Add uppercase letters.')

  if (/\d/.test(value)) score += 15
  else if (value.length > 0) feedback.push('Add numbers.')

  if (/[^A-Za-z0-9]/.test(value)) score += 15
  else if (value.length > 0) feedback.push('Add a symbol or punctuation mark.')

  if (/(.)\1\1/.test(value)) {
    score -= 10
    feedback.push('Avoid repeated characters or obvious patterns.')
  }

  if (/password|welcome|admin|qwerty|letmein/i.test(value)) {
    score -= 20
    feedback.push('This contains a very common password pattern.')
  }

  const clamped = Math.max(0, Math.min(100, score))
  const grade = clamped >= 80 ? 'Strong' : clamped >= 55 ? 'Moderate' : clamped >= 30 ? 'Weak' : 'Critical'

  return {
    score: clamped,
    grade,
    feedback: feedback.length > 0 ? feedback : ['No obvious weaknesses detected in this quick check.'],
  }
}

function generatePassword(length = 16) {
  const lowercase = 'abcdefghijkmnopqrstuvwxyz'
  const uppercase = 'ABCDEFGHJKLMNPQRSTUVWXYZ'
  const numbers = '23456789'
  const symbols = '!@#$%^&*()-_=+[]{};:,.?'
  const allCharacters = lowercase + uppercase + numbers + symbols

  const requiredCharacters = [
    lowercase[Math.floor(Math.random() * lowercase.length)],
    uppercase[Math.floor(Math.random() * uppercase.length)],
    numbers[Math.floor(Math.random() * numbers.length)],
    symbols[Math.floor(Math.random() * symbols.length)],
  ]

  const remainingCharacters = Array.from({ length: Math.max(length - requiredCharacters.length, 0) }, () => {
    return allCharacters[Math.floor(Math.random() * allCharacters.length)]
  })

  return [...requiredCharacters, ...remainingCharacters].sort(() => Math.random() - 0.5).join('')
}

function getPasswordSuggestions(password) {
  const suggestions = []

  if (password.length < 12) suggestions.push('Use at least 12 characters for stronger protection.')
  if (!/[a-z]/.test(password)) suggestions.push('Add lowercase letters.')
  if (!/[A-Z]/.test(password)) suggestions.push('Add uppercase letters.')
  if (!/\d/.test(password)) suggestions.push('Add numbers.')
  if (!/[^A-Za-z0-9]/.test(password)) suggestions.push('Add a symbol or punctuation mark.')
  if (/(.)\1\1/.test(password)) suggestions.push('Avoid repeated characters or obvious patterns.')
  if (/password|welcome|admin|qwerty|letmein/i.test(password)) suggestions.push('Remove common password words or keyboard patterns.')

  return suggestions.length > 0 ? suggestions : ['This password looks stronger than average in this quick check.']
}

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
  const [analyzerInput, setAnalyzerInput] = useState('')
  const [analyzerResult, setAnalyzerResult] = useState(null)
  const [generatedPassword, setGeneratedPassword] = useState('')

  useEffect(() => {
    const storedToken = window.localStorage.getItem(AUTH_TOKEN_KEY)
    const storedUser = window.localStorage.getItem(AUTH_USER_KEY)

    if (!storedToken) {
      if (storedUser) {
        window.localStorage.removeItem(AUTH_USER_KEY)
      }
      return
    }

    async function restoreSession() {
      try {
        const user = await apiRequest('/auth/me', {
          headers: {
            Authorization: `Bearer ${storedToken}`,
          },
        })

        setIsAuthenticated(true)
        setCurrentUser(user)
        setDisplayName(user.name)
        setAuthMethod(user.auth_provider === 'google' ? 'Google' : user.identifier_type === 'phone' ? 'Phone OTP' : 'Email OTP')
        setActivePage('dashboard')
      } catch {
        window.localStorage.removeItem(AUTH_TOKEN_KEY)
        window.localStorage.removeItem(AUTH_USER_KEY)
      }
    }

    restoreSession()
  }, [])

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

  function switchToLogin() {
    setAuthTab('login')
    setAuthMessage('')
    setOtpSent(false)
    setOtpValue('')
  }

  function switchToSignup() {
    setAuthTab('signup')
    setAuthMessage('')
    setOtpSent(false)
    setOtpValue('')
  }

  function handleContinueAsGuest() {
    setShowGuestShell(true)
    setAuthMessage('Guest mode is active. Sign in to unlock the protected features.')
  }

  function openPasswordAnalyzer() {
    setActivePage('password-analyzer')
  }

  function returnToDashboard() {
    setActivePage('dashboard')
  }

  function runAnalyzer() {
    const result = scorePassword(analyzerInput)
    setAnalyzerResult({
      score: result.score,
      grade: result.grade,
      suggestions: getPasswordSuggestions(analyzerInput),
      feedback: result.feedback,
    })
  }

  function handleGeneratePassword() {
    const nextPassword = generatePassword(16)
    setGeneratedPassword(nextPassword)
    setAnalyzerInput(nextPassword)
    setAnalyzerResult(null)
  }

  function handleContactModeChange(mode) {
    setContactMode(mode)
    setAuthMessage('')
    setOtpSent(false)
    setOtpValue('')
  }

  const authCopy = authTab === 'signup'
    ? {
        eyebrow: 'Create profile',
        title: 'Join CyberGuardian AI',
        copy: 'Create your profile, then verify with OTP or Google to unlock the dashboard.',
      }
    : {
        eyebrow: 'Sign in',
        title: 'Welcome back',
        copy: 'Enter your email or phone number and we will send a one-time code.',
      }

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
            <p>
              Use Google, email, phone number, or register a profile. The protected tools stay locked until you authenticate.
            </p>
          </div>

          <div className="auth-hero-cards">
            <article>
              <strong>Protected scans</strong>
              <span>Unlock password analysis, risk scoring, and future threat tools.</span>
            </article>
            <article>
              <strong>Explainable results</strong>
              <span>See the reason behind every alert and recommendation.</span>
            </article>
            <article>
              <strong>Private sessions</strong>
              <span>Access stays gated until you complete sign-in or registration.</span>
            </article>
          </div>
        </section>

        <section className="auth-panel-shell">
          <div className="auth-panel-card">
            <div className="auth-tab-row" role="tablist" aria-label="Authentication tabs">
              <button type="button" className={`auth-tab ${authTab === 'login' ? 'active' : ''}`} onClick={switchToLogin}>
                Login
              </button>
              <button type="button" className={`auth-tab ${authTab === 'signup' ? 'active' : ''}`} onClick={switchToSignup}>
                Sign up
              </button>
            </div>

            <div className="auth-panel-header">
              <div className="auth-panel-header-top">
                <p className="eyebrow">{authCopy.eyebrow}</p>
                <h2>{authCopy.title}</h2>
                <p>{authCopy.copy}</p>
              </div>
            </div>

            <button type="button" className="oauth-button oauth-button--google" onClick={handleGoogleClick}>
              Continue with Google demo
            </button>

            <form className="auth-form" onSubmit={handleAuthSubmit}>
              {authTab === 'signup' ? (
                <label className="auth-field">
                  Your name
                  <input
                    type="text"
                    value={displayName}
                    onChange={(event) => setDisplayName(event.target.value)}
                    placeholder="Full name as shown on your profile"
                    autoComplete="name"
                  />
                </label>
              ) : null}

              <div className="auth-contact-switch" role="tablist" aria-label="Contact method">
                <button type="button" className={`auth-mini-switch ${contactMode === 'email' ? 'active' : ''}`} onClick={() => handleContactModeChange('email')}>
                  Email
                </button>
                <button type="button" className={`auth-mini-switch ${contactMode === 'phone' ? 'active' : ''}`} onClick={() => handleContactModeChange('phone')}>
                  Phone
                </button>
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

              {otpSent ? (
                <label className="auth-field">
                  OTP
                  <input
                    type="text"
                    value={otpValue}
                    onChange={(event) => setOtpValue(event.target.value)}
                    placeholder="Enter the one-time code"
                    inputMode="numeric"
                  />
                </label>
              ) : null}

              <div className="auth-actions-row">
                <button type="submit" className="primary-button auth-submit-button">
                  {otpSent ? 'Verify OTP' : 'Send OTP'}
                </button>
                <button type="button" className="ghost-button" onClick={handleContinueAsGuest}>
                  Skip for now
                </button>
              </div>

              <div className="auth-footer-links">
                <button type="button" className="link-button" onClick={switchToLogin}>
                  Login
                </button>
                <button type="button" className="link-button" onClick={switchToSignup}>
                  Sign up
                </button>
              </div>

              {authMessage ? <p className="auth-modal-message">{authMessage}</p> : null}
            </form>
          </div>
        </section>
      </div>
    )
  }

  if (!isAuthenticated && showGuestShell) {
    return (
      <div className="app-shell">
        <aside className="sidebar">
          <div>
            <p className="eyebrow">CyberGuardian AI</p>
            <h1>Guest preview mode.</h1>
          </div>

          <nav className="sidebar-nav" aria-label="Primary">
            <a href="#dashboard">Dashboard</a>
            <a href="#password-analyzer">Password Analyzer</a>
            <a href="#auth">Authentication</a>
          </nav>

          <div className="sidebar-card">
            <p className="sidebar-card-label">Access status</p>
            <strong>Locked until sign-in</strong>
            <span>View the layout, but the protected tools stay disabled.</span>
          </div>
        </aside>

        <main className="main-content" id="dashboard">
          <header className="topbar">
            <div>
              <p className="eyebrow">Guest mode</p>
              <h2>Sign in to unlock the tools</h2>
            </div>
            <button type="button" className="primary-button" onClick={() => setShowGuestShell(false)}>
              Back to sign in
            </button>
          </header>

          <div className="guest-banner">
            <strong>Protected features are disabled.</strong>
            <span>Sign in or register to activate password analysis, scans, and dashboard controls.</span>
          </div>

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

          <section className="content-grid">
            <article className="panel auth-panel" id="auth">
              <p className="eyebrow">Authentication</p>
              <h3>Go back to the login page.</h3>
              <p>Complete sign-in or registration to unlock the platform.</p>

              <div className="auth-actions">
                <button type="button" className="primary-button" onClick={() => setShowGuestShell(false)}>
                  Sign in
                </button>
                <button type="button" className="secondary-button" onClick={() => setShowGuestShell(false)}>
                  Create account
                </button>
              </div>
            </article>
          </section>
        </main>
      </div>
    )
  }

  if (isAuthenticated && activePage === 'password-analyzer') {
    return (
      <div className="analyzer-page">
        <aside className="sidebar analyzer-sidebar">
          <div>
            <p className="eyebrow">CyberGuardian AI</p>
            <h1>Password Analyzer</h1>
          </div>

          <nav className="sidebar-nav" aria-label="Password analyzer navigation">
            <button type="button" className="sidebar-nav-button" onClick={returnToDashboard}>
              Back to dashboard
            </button>
            <button type="button" className="sidebar-nav-button active" onClick={openPasswordAnalyzer}>
              Password analyzer
            </button>
          </nav>

          <div className="sidebar-card">
            <p className="sidebar-card-label">Locked state</p>
            <strong>{isAuthenticated ? `${authMethod} unlocked` : 'Locked until sign-in'}</strong>
            <span>Use the analyzer to check strength and generate a safer password.</span>
          </div>
        </aside>

        <main className="main-content analyzer-main">
          <header className="topbar">
            <div>
              <p className="eyebrow">Security tools</p>
              <h2>Password Analyzer</h2>
            </div>
            <button type="button" className="primary-button" onClick={returnToDashboard}>
              Back to dashboard
            </button>
          </header>

          <section className="hero-card analyzer-hero">
            <div>
              <p className="eyebrow">Check and improve</p>
              <h3>Type a password, check the risk score, and generate a stronger one if needed.</h3>
              <p className="hero-copy">
                This page gives a simple risk score, human suggestions, and a built-in password generator to help users recover quickly.
              </p>
            </div>
            <div className="hero-panel">
              <div className="signal-row">
                <span className="signal-dot" />
                <span>Risk scoring and suggestions update after you press Check.</span>
              </div>
              <div className="signal-row">
                <span className="signal-dot" />
                <span>Generate a new password if you want a stronger starting point.</span>
              </div>
            </div>
          </section>

          <section className="analyzer-grid">
            <article className="panel analyzer-form-card">
              <p className="eyebrow">Password check</p>
              <h3>Try a password</h3>

              <label className="field-label" htmlFor="analyzer-input">
                Password
              </label>
              <textarea
                id="analyzer-input"
                className="analyzer-textarea"
                value={analyzerInput}
                onChange={(event) => setAnalyzerInput(event.target.value)}
                placeholder="Enter a password to check"
                rows={4}
              />

              <div className="auth-actions">
                <button type="button" className="primary-button" onClick={runAnalyzer}>
                  Check
                </button>
                <button type="button" className="secondary-button" onClick={handleGeneratePassword}>
                  Generate password
                </button>
              </div>

              {generatedPassword ? (
                <div className="generated-password-box">
                  <p className="field-label">Generated password</p>
                  <code>{generatedPassword}</code>
                </div>
              ) : null}
            </article>

            <article className="panel analyzer-result-card">
              <p className="eyebrow">Result</p>
              <h3>{analyzerResult ? `${analyzerResult.grade} risk` : 'No scan yet'}</h3>

              {analyzerResult ? (
                <>
                  <div className="score-row analyzer-score-row" aria-live="polite">
                    <div>
                      <p className="score-label">Risk score</p>
                      <strong className="score-value">{analyzerResult.score}/100</strong>
                    </div>
                    <div className="score-meter" aria-hidden="true">
                      <span style={{ width: `${analyzerResult.score}%` }} />
                    </div>
                  </div>

                  <ul className="feedback-list">
                    {analyzerResult.suggestions.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </>
              ) : (
                <p className="hero-copy">Press Check to see the risk score and suggestions.</p>
              )}
            </article>
          </section>
        </main>
      </div>
    )
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div>
          <p className="eyebrow">CyberGuardian AI</p>
          <h1>Explainable cyber risk, built for everyday decisions.</h1>
        </div>

        <nav className="sidebar-nav" aria-label="Primary">
          <a href="#dashboard">Dashboard</a>
          <button type="button" className="sidebar-nav-button" onClick={openPasswordAnalyzer}>
            Password Analyzer
          </button>
          <a href="#auth">Authentication</a>
        </nav>

        <div className="sidebar-card">
          <p className="sidebar-card-label">Phase 1 status</p>
          <strong>{isAuthenticated ? `${currentUser?.name ?? authMethod} unlocked` : 'Locked until sign-in'}</strong>
          <span>
            {isAuthenticated
              ? 'Password analysis and dashboard controls are available.'
              : 'You can browse, but the protected tools remain disabled until authentication.'}
          </span>
        </div>
      </aside>

      <main className="main-content" id="dashboard">
        <header className="topbar">
          <div>
            <p className="eyebrow">Security operations</p>
            <h2>Dark enterprise dashboard</h2>
          </div>
          <button type="button" className="primary-button" onClick={openPasswordAnalyzer} disabled={!isAuthenticated}>
            Run threat scan
          </button>
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
          {quickStats.map((stat) => (
            <article className={`metric-card ${isAuthenticated ? '' : 'locked-card'}`} key={stat.label}>
              <p>{stat.label}</p>
              <strong>{stat.value}</strong>
              <span>{stat.detail}</span>
              {!isAuthenticated ? <span className="locked-hint">Sign in to activate live data.</span> : null}
            </article>
          ))}
        </section>

        <section className="content-grid">
          <article className={`panel auth-panel ${isAuthenticated ? '' : 'locked-panel'}`} id="auth">
            <p className="eyebrow">Authentication</p>
            <h3>{isAuthenticated ? 'Signed in and ready.' : 'Prepare the login flow and protected dashboard shell.'}</h3>
            <p>
              {isAuthenticated
                ? `Authenticated as ${authMethod}. The protected experience is now available.`
                : 'The protected experience stays locked until the user signs in, registers, or continues with Google.'}
            </p>

            <div className="auth-actions">
              <button type="button" className="primary-button" onClick={() => setShowGuestShell(false)}>
                Sign in
              </button>
              <button type="button" className="secondary-button" onClick={() => setShowGuestShell(false)}>
                Create account
              </button>
            </div>

            <div className="auth-note">
              <strong>{isAuthenticated ? 'Access granted' : 'Access required'}</strong>
              <span>
                {isAuthenticated
                  ? `Signed in as ${currentUser?.name ?? 'the current user'}. All Phase 1 controls are available.`
                  : 'Sign-in is required before the interactive tools can be used.'}
              </span>
            </div>

            {!isAuthenticated ? <div className="locked-overlay">Authentication required to use protected features.</div> : null}
          </article>
        </section>
      </main>
    </div>
  )
}
