module.exports = {
  extends: ['@commitlint/config-conventional'],
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