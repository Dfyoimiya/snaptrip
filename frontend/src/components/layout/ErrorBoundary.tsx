import { Component, type ReactNode } from "react"

interface Props {
  children: ReactNode
  fallback?: string
}

interface State {
  hasError: boolean
  errorMsg: string
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, errorMsg: "" }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, errorMsg: error.message }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex items-center justify-center h-full bg-zinc-950 text-zinc-400 p-4">
          <div className="text-center">
            <p className="text-sm text-red-400 mb-1">
              {this.props.fallback ?? "Component Error"}
            </p>
            <p className="text-xs font-mono text-zinc-600">{this.state.errorMsg}</p>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
