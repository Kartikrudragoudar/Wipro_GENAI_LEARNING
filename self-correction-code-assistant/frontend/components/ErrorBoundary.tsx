"use client";

import { Component, type ReactNode } from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";

type Props = {
  children: ReactNode;
  fallbackLabel?: string;
};

type State = {
  hasError: boolean;
  error?: Error;
};

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  handleReset = () => {
    this.setState({ hasError: false, error: undefined });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex h-full flex-col items-center justify-center gap-3 p-6 text-center">
          <AlertTriangle size={32} className="text-[var(--danger)]" />
          <p className="text-sm text-[var(--text)]">
            {this.props.fallbackLabel ?? "Something went wrong"} in this panel.
          </p>
          <p className="max-w-xs text-xs text-[var(--muted)]">{this.state.error?.message}</p>
          <button
            onClick={this.handleReset}
            className="flex items-center gap-2 rounded border border-[var(--line)] px-3 py-1.5 text-sm text-[var(--text)] hover:bg-[var(--panel-3)]"
          >
            <RotateCcw size={14} /> Try again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
