declare module "@novnc/novnc" {
  interface RFBOptions {
    credentials?: { username?: string; password?: string; target?: string }
    shared?: boolean
    repeaterID?: string
    wsProtocols?: string[]
  }

  export default class RFB {
    constructor(target: HTMLElement, url: string, options?: RFBOptions)
    scaleViewport: boolean
    resizeSession: boolean
    background: string
    viewOnly: boolean
    capabilities: { power?: boolean }
    addEventListener(type: string, listener: (e: any) => void): void
    removeEventListener(type: string, listener: (e: any) => void): void
    disconnect(): void
    sendCredentials(creds: { username?: string; password?: string }): void
    sendKey(keysym: number, code: string, down?: boolean): void
    sendCtrlAltDel(): void
    focus(): void
  }
}
