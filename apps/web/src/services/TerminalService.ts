/**
 * TerminalService — WebSocket client for SSH Gateway (port 3001).
 *
 * All session management and command I/O flows through one WebSocket connection.
 * Output is streamed in real-time from the gateway.
 */

type MessageHandler = (msg: any) => void

export interface ConnectPayload {
  deviceId: string
  hostname: string
  address: string
  port?: number
}

class TerminalService {
  private ws: WebSocket | null = null
  private handlers = new Set<MessageHandler>()
  private url: string
  private reconnectTimer = 0
  private shouldReconnect = true
  private pendingQueue: string[] = []

  constructor() {
    const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://'
    const hostname = window.location.hostname || 'localhost'
    this.url = `${protocol}${hostname}:3001`
  }

  /** Connect to SSH Gateway WebSocket */
  connect() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) return
    this.shouldReconnect = true
    this.ws = new WebSocket(this.url)

    this.ws.addEventListener('open', () => {
      console.info('[TerminalService] Connected to SSH Gateway:', this.url)
      this.reconnectTimer = 0
      // Flush queued messages
      while (this.pendingQueue.length > 0) {
        const msg = this.pendingQueue.shift()!
        this.ws!.send(msg)
      }
    })

    this.ws.addEventListener('message', (ev) => {
      let msg: any
      try {
        msg = typeof ev.data === 'string' ? JSON.parse(ev.data) : ev.data
      } catch {
        console.error('[TerminalService] Failed to parse:', ev.data)
        return
      }
      for (const h of this.handlers) {
        try { h(msg) } catch (e) { console.error('[TerminalService] handler error', e) }
      }
    })

    this.ws.addEventListener('close', () => {
      console.warn('[TerminalService] Disconnected from SSH Gateway')
      this.ws = null
      if (this.shouldReconnect) this.scheduleReconnect()
    })

    this.ws.addEventListener('error', (err) => {
      console.error('[TerminalService] Error', err)
    })
  }

  disconnect() {
    this.shouldReconnect = false
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  private scheduleReconnect() {
    this.reconnectTimer = Math.min(30000, this.reconnectTimer ? this.reconnectTimer * 2 : 1000)
    setTimeout(() => {
      console.info('[TerminalService] Reconnecting...')
      this.connect()
    }, this.reconnectTimer)
  }

  private send(obj: any) {
    const payload = JSON.stringify(obj)
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(payload)
    } else {
      this.pendingQueue.push(payload)
    }
  }

  /** Request new SSH session */
  connectDevice(payload: ConnectPayload) {
    this.send({
      action: 'connect',
      deviceId: payload.deviceId,
      hostname: payload.hostname,
      address: payload.address,
      port: payload.port || 22,
    })
  }

  /** Send command to an active session */
  sendCommand(sessionId: string, command: string) {
    this.send({ action: 'command', sessionId, command })
  }

  /** Send raw input to an active session (no newline appended) */
  sendRaw(sessionId: string, data: string) {
    this.send({ action: 'input', sessionId, data })
  }

  /** Close an SSH session */
  disconnectSession(sessionId: string) {
    this.send({ action: 'disconnect', sessionId })
  }

  /** Register message handler — returns unsubscribe function */
  onMessage(handler: MessageHandler): () => void {
    this.handlers.add(handler)
    return () => this.handlers.delete(handler)
  }

  isConnected() {
    return !!this.ws && this.ws.readyState === WebSocket.OPEN
  }
}

const terminalService = new TerminalService()
export default terminalService
