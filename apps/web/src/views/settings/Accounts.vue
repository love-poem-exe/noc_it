<template>
    <div class="accounts-container">
      <div class="left-panel">
        <h2>Dodaj konto</h2>
        <input v-model="name" placeholder="Nazwa" />
        <input v-model="login" placeholder="Login" />
        <input v-model="password" placeholder="Hasło" type="password" />
        <button @click="submit">Dodaj</button>
      </div>
  
      <div class="right-panel">
        <h2>Lista kont</h2>
        <table v-if="accounts.length > 0">
          <thead>
            <tr>
              <th>Nazwa</th>
              <th>Login</th>
              <th>Hasło</th>
              <th>Akcje</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(account, index) in accounts" :key="account.id">
              <td>{{ account.name }}</td>
              <td>{{ account.login }}</td>
              <td>
                <span>
                  {{ visiblePasswords[index] ? account.password : '••••••••' }}
                </span>
                <button
                  class="eye-btn"
                  @mousedown="togglePassword(index, true)"
                  @mouseup="togglePassword(index, false)"
                  @mouseleave="togglePassword(index, false)"
                >
                  👁
                </button>
              </td>
              <td>
                <button @click="moveUp(index)" :disabled="index === 0">⬆️</button>
                <button @click="moveDown(index)" :disabled="index === accounts.length - 1">⬇️</button>
                <button @click="removeAccount(account.id)">❌</button>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-else>Brak kont do wyświetlenia.</p>
      </div>
    </div>
  </template>
  
  <script setup lang="ts">
import { ref, onMounted } from 'vue'
import { requestJson } from '../../services/ApiClient'
import useData from '../../composables/useData'
import type { Account } from '../../composables/useData'

// Użyj cache dla kont
const {
  accounts,
  loadAccounts,
  addAccount: addAccountToCache,
  removeAccount: removeAccountFromCache
} = useData()
  
  const name = ref('')
  const login = ref('')
  const password = ref('')
  const visiblePasswords = ref<boolean[]>([])
  
  const submit = async () => {
    await addAccountToCache(name.value, login.value, password.value)
    name.value = ''
    login.value = ''
    password.value = ''
    // Po dodaniu konta, zaktualizuj widoczne hasła
    visiblePasswords.value = accounts.value.map(() => false)
  }
  
  const togglePassword = (index: number, show: boolean): void => {
    visiblePasswords.value[index] = show
  }
  
  const removeAccount = async (id: string): Promise<void> => {
    await removeAccountFromCache(id)
    // Po usunięciu konta, zaktualizuj widoczne hasła
    visiblePasswords.value = accounts.value.map(() => false)
  }
  
  const moveUp = async (index: number): Promise<void> => {
    if (index > 0) {
      const reordered = [...accounts.value]
      ;[reordered[index - 1], reordered[index]] = [reordered[index], reordered[index - 1]]
      await saveReorderedAccounts(reordered)
    }
  }
  
  const moveDown = async (index: number): Promise<void> => {
    if (index < accounts.value.length - 1) {
      const reordered = [...accounts.value]
      ;[reordered[index + 1], reordered[index]] = [reordered[index], reordered[index + 1]]
      await saveReorderedAccounts(reordered)
    }
  }
  
  const saveReorderedAccounts = async (newList: Account[]): Promise<void> => {
    await requestJson('/api/accounts/reorder', {
      method: 'POST',
      body: { accounts: newList },
      timeoutMs: 30000
    })
    await loadAccounts()
  }
  
  onMounted(async () => {
    console.log('[Accounts.vue] Loading accounts with cache...')
    await loadAccounts()
    // Inicjalizuj widoczne hasła po załadowaniu kont
    visiblePasswords.value = accounts.value.map(() => false)
    console.log('[Accounts.vue] Accounts loaded from cache')
  })
  </script>
  
  <style scoped>
.accounts-container {
  display: flex; width: 100%; height: 100%;
  gap: 1.25rem; padding: 1rem; box-sizing: border-box;
  background: #0d1117; color: #e6edf3;
}

.left-panel {
  width: 28%; flex-shrink: 0;
  display: flex; flex-direction: column; gap: 10px;
  background: #161b22; border: 1px solid #30363d;
  border-radius: 8px; padding: 1rem;
}

.left-panel h2 { font-size: 13px; font-weight: 600; color: #8b949e; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }

.right-panel {
  flex: 1; overflow-x: auto;
  display: flex; flex-direction: column; gap: 0.5rem;
}

.right-panel h2 { font-size: 13px; font-weight: 600; color: #8b949e; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }

input {
  width: 100%; padding: 7px 10px;
  background: #0d1117; border: 1px solid #30363d;
  border-radius: 6px; color: #e6edf3;
  font-size: 13px; font-family: inherit; outline: none;
  transition: border-color 0.15s; box-sizing: border-box;
}
input::placeholder { color: #484f58; }
input:focus { border-color: #388bfd; }

button {
  padding: 7px 14px; background: #1f6feb;
  color: #fff; border: 1px solid #1f6feb;
  border-radius: 6px; font-size: 13px; font-weight: 500;
  font-family: inherit; cursor: pointer; width: 100%;
  transition: background 0.15s;
}
button:hover { background: #388bfd; border-color: #388bfd; }

.eye-btn {
  padding: 2px 6px; width: auto;
  background: transparent; border: none; color: #8b949e;
  font-size: 12px; cursor: pointer; margin-left: 6px;
}
.eye-btn:hover { color: #e6edf3; }

table { width: 100%; border-collapse: collapse; }

th, td {
  border-bottom: 1px solid #21262d;
  padding: 9px 14px; text-align: left;
  color: #e6edf3; font-size: 13px;
}

th {
  background: #161b22; color: #8b949e;
  font-weight: 600; font-size: 11.5px;
  text-transform: uppercase; letter-spacing: 0.05em;
  border-bottom: 1px solid #30363d;
}

tr { background: #0d1117; }
tr:nth-child(even) { background: #0f1318; }
tr:hover { background: #161b22; }

td button {
  width: auto; padding: 4px 8px;
  background: transparent; color: #8b949e;
  border: 1px solid #30363d; border-radius: 5px; font-size: 13px;
}
td button:hover { background: #21262d; color: #e6edf3; }
td button:disabled { opacity: 0.3; cursor: not-allowed; }
</style>
