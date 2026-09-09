const grandfatheredSubjects = new Set([
  'test: capture ECC release security contracts',
  'ci: secure Aethos release workflow',
])

module.exports = {
  extends: ['@commitlint/config-conventional'],
  // These two commits predate enforcement on #550 and cannot be rewritten.
  // Keep the exception exact so all future subjects remain lowercase.
  ignores: [(message) => grandfatheredSubjects.has(message.trim())],
  rules: {
    'type-enum': [2, 'always', [
      'feat', 'fix', 'refactor', 'docs', 'style', 'test',
      'chore', 'perf', 'ci', 'build', 'revert', 'security'
    ]],
    'scope-case': [2, 'always', 'lowerCase'],
    'subject-case': [2, 'always', 'lower-case'],
    'subject-empty': [2, 'never'],
    'subject-full-stop': [2, 'never', '.'],
    'header-max-length': [2, 'always', 72],
  },
}