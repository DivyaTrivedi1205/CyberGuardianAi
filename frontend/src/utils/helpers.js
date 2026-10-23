export function scorePassword(value) {
  if (!value) return { score: 0, grade: 'Critical', feedback: [] }

  let score = 0
  const feedback = []

  if (value.length >= 12) score += 20
  else if (value.length > 8) { score += 10; feedback.push('Use at least 12 characters for better resilience.') }
  else feedback.push('Use at least 12 characters for better resilience.')

  if (/[A-Z]/.test(value)) score += 20
  else { feedback.push('Add uppercase letters.') }

  if (/[a-z]/.test(value)) score += 20
  else { feedback.push('Add lowercase letters.') }

  if (/[0-9]/.test(value)) score += 20
  else { feedback.push('Add numbers.') }

  if (/[^A-Za-z0-9]/.test(value)) score += 20
  else { feedback.push('Add a symbol or punctuation mark.') }

  const clamped = Math.min(100, score)
  const grade = clamped >= 80 ? 'Strong' : clamped >= 55 ? 'Moderate' : clamped >= 30 ? 'Weak' : 'Critical'

  return {
    score: clamped,
    grade,
    feedback: feedback.length > 0 ? feedback : ['No obvious weaknesses detected.'],
  }
}

export function generatePassword(length = 16) {
  const charset = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+~`|}{[]:;?><,./-='
  let password = ''
  let hasUpper = false
  let hasLower = false
  let hasNumber = false
  let hasSymbol = false

  while (!(hasUpper && hasLower && hasNumber && hasSymbol)) {
    password = ''
    hasUpper = false
    hasLower = false
    hasNumber = false
    hasSymbol = false

    for (let i = 0; i < length; i++) {
        const char = charset[Math.floor(Math.random() * charset.length)]
        password += char
        if (/[A-Z]/.test(char)) hasUpper = true
        else if (/[a-z]/.test(char)) hasLower = true
        else if (/[0-9]/.test(char)) hasNumber = true
        else hasSymbol = true
    }
  }
  return password
}

export function getPasswordSuggestions(password) {
  const suggestions = []
  if (!password) return []
  if (password.length < 12) suggestions.push('Use at least 12 characters')
  if (!/[A-Z]/.test(password)) suggestions.push('Add uppercase letters')
  if (!/[a-z]/.test(password)) suggestions.push('Add lowercase letters')
  if (!/[0-9]/.test(password)) suggestions.push('Add numbers')
  if (!/[^A-Za-z0-9]/.test(password)) suggestions.push('Add special characters')
  return suggestions
}
