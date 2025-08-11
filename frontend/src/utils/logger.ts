/**
 * Development logger utility
 * Provides conditional logging based on environment
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LogContext {
  component?: string;
  documentId?: string;
  [key: string]: unknown;
}

class Logger {
  private isDev = import.meta.env.DEV;

  debug(message: string, context?: LogContext): void {
    if (this.isDev) {
      console.log(`🔍 ${message}`, context || '');
    }
  }

  info(message: string, context?: LogContext): void {
    if (this.isDev) {
      console.log(`ℹ️ ${message}`, context || '');
    }
  }

  warn(message: string, context?: LogContext): void {
    console.warn(`⚠️ ${message}`, context || '');
  }

  error(message: string, context?: LogContext): void {
    console.error(`❌ ${message}`, context || '');
  }

  websocket(message: string, context?: LogContext): void {
    if (this.isDev) {
      console.log(`🔌 ${message}`, context || '');
    }
  }

  upload(message: string, context?: LogContext): void {
    if (this.isDev) {
      console.log(`📤 ${message}`, context || '');
    }
  }

  api(message: string, context?: LogContext): void {
    if (this.isDev) {
      console.log(`📡 ${message}`, context || '');
    }
  }
}

export const logger = new Logger();