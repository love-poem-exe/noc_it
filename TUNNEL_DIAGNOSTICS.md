# 🔧 Poradnik Diagnostyki Tunelu SSH

## Problem: "Tunel mówi CONNECTED ale faktycznie leży"

To typowy problem - plik statusu (`tunnel_status.json`) mówi `CONNECTED`, ale proces `tunnel_runner.py` padł i port nie nasłuchuje.

---

## ✅ Rozwiązania

### 1. **Automatyczne - Health Check**

Nowy przycisk **⚕️ Health Check** w panelu Ustawień → Tunneling:
- Sprawdza czy port faktycznie nasłuchuje
- Jeśli tunel leży, automatycznie go restartuje
- Wymaga ~5 sekund

```javascript
// Frontend - klik na przycisk
await invoke('run_script', {
  script: 'settings-tunnel_controller',
  method: 'healthcheck_tunnel'
})
```

### 2. **Diagnozowanie - Przycisk Diagnoza**

Nowy przycisk **🔍 Diagnoza** w panelu Ustawień → Tunneling:
- Pokazuje dokładny stan tunelu
- Raportuje każdy komponent
- Podaje konkretne rekomendacje

**Możliwe wyniky:**
```
✅ OK - Tunel działa
    ├─ Status plik: CONNECTED
    ├─ Port nasłuchuje: TAK ✅
    └─ SSH odpowiada: TAK ✅

⚠️  CZĘŚCIOWO - Port nasłuchuje ale nie testuje
    ├─ Status plik: CONNECTED
    ├─ Port nasłuchuje: TAK ✅
    └─ SSH odpowiada: NIE ❌
    
❌ BŁĄD - Status CONNECTED ale port nie nasłuchuje
    ├─ Status plik: CONNECTED
    ├─ Port nasłuchuje: NIE ❌
    └─ SSH odpowiada: NIE ❌
    💡 Rozwiązanie: toggle_tunnel()
```

---

## 🔍 Co Diagnoza Sprawdza

| Komponent | Test | Co Oznacza |
|-----------|------|-----------|
| **Status File** | Czyta `tunnel_status.json` | Jaki status aplikacja myśli że ma |
| **Port Listening** | `socket.connect(127.0.0.1:port)` | Czy proces `tunnel_runner.py` żyje |
| **SSH Connection** | Wysyła test header przez tunel | Czy SSH na zdalnym hoście dostępny |

---

## 🚀 Automatyczne Healthcheck na Starcie

Na każde uruchomienie aplikacji:
1. Załaduje się `Main.vue`
2. Wywoła `autoHealthcheckTunnel()` w `onMounted`
3. Jeśli tunel leży - automatycznie go restartuje
4. Zaloguje wynik do console

```
[Main] ✅ Tunel OK na starcie!
[Main] 🔧 Tunel został naprawiony na starcie!
[Main] ℹ️  Tunel status na starcie: NOT_CONNECTED
```

---

## 🛠️ Ręczne Diagnostyki - PowerShell

### Sprawdź czy port nasłuchuje
```powershell
netstat -ano | Select-String "57568"
# Powinno być: TCP    127.0.0.1:57568    0.0.0.0:0    LISTENING
```

### Sprawdź status pliku
```powershell
Get-Content "src\data\tunnel_status.json" | ConvertFrom-Json
# Powinno być: status = "CONNECTED", port = 57568
```

### Spróbuj połączyć na port
```powershell
$socket = New-Object Net.Sockets.TcpClient
$socket.Connect("127.0.0.1", 57568)
$socket.Connected  # True = OK, False = NIE

# Jeśli nie: tunel leży!
```

### Zrestartuj tunel
```powershell
# 1. Rozłącz
curl "http://localhost:5173/api/tunnel/disconnect"

# 2. Czekaj
Start-Sleep -Seconds 2

# 3. Połącz
curl "http://localhost:5173/api/tunnel/connect"

# 4. Czekaj na ustabilizowanie
Start-Sleep -Seconds 3
```

---

## 🔴 Możliwe Błędy

| Błąd | Przyczyna | Rozwiązanie |
|------|-----------|------------|
| Port nie nasłuchuje | `tunnel_runner.py` padł | Health Check + Reconnect |
| Auth failed | Zły login/hasło | Sprawdź `tunnel.json` |
| Connection timeout | SSH na hoście down | Sprawdzić dostęp do `100.124.95.19` |
| CONNECTED ale NIE ODPOWIADA | SSH na zdalnym hoście down | Sprawdzić dostęp do urządzenia |

---

## 📝 Konfiguracja

**Tunel nasłuchuje na**: `127.0.0.1:PORT` (losowy port 10000-60000)

**Procedura nawiązania**:
```
1. Client → localhost:PORT
2. Wysyła JSON: {"target_ip": "192.168.1.1", "target_port": 22}
3. Tunel otwiera kanał SSH: open_channel("direct-tcpip", (192.168.1.1, 22))
4. Dwukierunkowa transmisja (pipe)
```

---

## 💡 Tips & Tricks

### Szybki Test - Czy Tunel Żyje?
```javascript
// W konsoli przeglądarki
fetch('http://127.0.0.1:57568', { method: 'OPTIONS' })
  .then(() => console.log('✅ Port nasłuchuje'))
  .catch(() => console.log('❌ Port nie nasłuchuje'))
```

### Monitorowanie Tunelu
```javascript
// Automat healthcheck co 30 sekund
setInterval(() => {
  invoke('run_script', {
    script: 'settings-tunnel_controller',
    method: 'healthcheck_tunnel'
  })
}, 30000)
```

### Logi Debug
Sprawdź konsolę Tauri:
```
[TunnelRunner] Połączono z 100.124.95.19
[TunnelRunner] Otwarto tunel lokalny: 127.0.0.1:57568
[TunnelRunner] Nasłuchiwanie na localhost:57568 – gotowe do proxy
```

---

## 📊 Status Check - Procedura

1. **Otwórz Ustawienia → Tunneling**
2. **Kliknij 🔍 Diagnoza**
3. **Przeczytaj wynik**
4. **Jeśli ❌ BŁĄD:**
   - Kliknij ⚕️ Health Check (automat)
   - LUB ręcznie: Disconnect → wait 2s → Connect
5. **Czekaj 3 sekundy na ustabilizowanie**
6. **Kliknij 🔍 Diagnoza** ponownie - powinno być ✅

---

## 🎯 Checklist Weryfikacji

- [ ] Status pliku = `CONNECTED`
- [ ] Port nasłuchuje (socket test OK)
- [ ] SSH na hoście dostępny
- [ ] Diagnoza mówi `✅ OK`
- [ ] Można się połączyć do urządzeń

Jeśli wszystkie punkty ✅ - tunel jest OK!

---

## 🔗 Pliki Konfiguracyjne

| Plik | Zawartość | Edytować? |
|------|-----------|----------|
| `tunnel.json` | Adres, login, hasło SSH | ✏️ Tak |
| `tunnel_status.json` | Status, port | ❌ Auto |
| `tunnel_runner.py` | Logika tunelowania | ⚙️ Rzadko |
| `tunnel_controller.py` | API kontroli tunelu | ⚙️ Rzadko |

