import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  // dist = Build-Output; src/modules/* = zur Build-Zeit aus dem separaten
  // hydrahive2-modules-Repo generiert (gitignored) — kein Quellcode dieses
  // Repos, daher nicht linten (hält lokalen Lint deckungsgleich mit CI).
  globalIgnores(['dist', 'src/modules/*/', 'src/modules/index.generated.ts']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
    },
    // Severity-Politik (Cleanup #5): eslint läuft ab jetzt in CI. Damit das
    // sinnvoll ist, ohne main mit Rauschen der neuen react-hooks-v7-Compiler-
    // Suite rot zu färben, staffeln wir bewusst:
    //  - error  = echte Fehler, die wir sauber halten (CI blockiert)
    //  - warn   = wertvoll aber (noch) viele Alt-Treffer ODER zu aggressiv
    rules: {
      // Findet echte Stale-Closure-Bugs, aber 38 Alt-Fälle → separater Fix-PR.
      'react-hooks/exhaustive-deps': 'warn',
      // Neue, sehr aggressive react-compiler-Regeln (v7) mit vielen
      // False-Positives auf legitime Muster — sichtbar als warn, nicht blockierend.
      'react-hooks/set-state-in-effect': 'warn',
      'react-hooks/refs': 'warn',
      'react-hooks/immutability': 'warn',
      'react-hooks/purity': 'warn',
      'react-hooks/static-components': 'warn',
      // HMR-Hygiene — kein Laufzeitfehler.
      'react-refresh/only-export-components': 'warn',
      // Bewusst annotierte any bleiben erlaubt (unter TS-strict abgedeckt),
      // implizite any fängt bereits der Compiler.
      '@typescript-eslint/no-explicit-any': 'warn',
      // Unterstrich-Präfix = bewusst ungenutzt (API-Signaturen, Platzhalter-
      // Parameter). Etablierte Konvention — nicht als Fehler werten.
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_', caughtErrorsIgnorePattern: '^_' },
      ],
    },
  },
])
