import { Component, ErrorInfo, ReactNode } from 'react'

interface Props { children: ReactNode }
interface State { hasError: boolean; error?: Error }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[InvFlow] Error no controlado:', error, info.componentStack)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          justifyContent: 'center', height: '100vh', gap: '1rem',
          fontFamily: 'sans-serif', color: '#374151'
        }}>
          <div style={{ fontSize: '2rem' }}>⚠️</div>
          <h2 style={{ margin: 0 }}>Ha ocurrido un error inesperado</h2>
          <p style={{ margin: 0, color: '#6b7280' }}>
            Recarga la página para continuar. Si el problema persiste, contacta con soporte.
          </p>
          <button
            onClick={() => window.location.reload()}
            style={{
              padding: '0.5rem 1.5rem', background: '#2563eb', color: 'white',
              border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '1rem'
            }}
          >
            Recargar página
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
