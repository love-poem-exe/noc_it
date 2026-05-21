// eslint.config.js
import vue from 'eslint-plugin-vue'
import vueParser from 'vue-eslint-parser'

export default [
  {
    ignores: ['node_modules/**', 'dist/**', 'coverage/**', '**/*.ts']
  },
  {
    files: ['**/*.vue'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      parser: vueParser,
      parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module',
        parser: false
      }
    },
    plugins: { vue },
    rules: {
      'no-unused-vars': 'warn',
      'vue/no-unused-vars': 'warn',
      'vue/multi-word-component-names': 'off'
    }
  },
  {
    files: ['**/*.js', '**/*.ts'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module'
    },
    rules: {
      'no-unused-vars': 'warn'
    }
  }
]
