import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { AustralianState, RiskLevel } from '@/types'

// Utility for combining class names
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Format file size
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes'
  
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// Format currency (Australian dollars)
export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-AU', {
    style: 'currency',
    currency: 'AUD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)
}

// Format percentage
export function formatPercentage(value: number, decimals: number = 1): string {
  return `${(value * 100).toFixed(decimals)}%`
}

// Format date
export function formatDate(date: string | Date): string {
  return new Intl.DateTimeFormat('en-AU', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(date))
}

// Format relative time
export function formatRelativeTime(date: string | Date): string {
  const now = new Date()
  const target = new Date(date)
  const diffInSeconds = (now.getTime() - target.getTime()) / 1000
  
  if (diffInSeconds < 60) return 'Just now'
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`
  if (diffInSeconds < 2592000) return `${Math.floor(diffInSeconds / 86400)}d ago`
  
  return formatDate(date)
}

// Australian state helpers
export const australianStates: Array<{ value: AustralianState; label: string; fullName: string }> = [
  { value: 'NSW', label: 'NSW', fullName: 'New South Wales' },
  { value: 'VIC', label: 'VIC', fullName: 'Victoria' },
  { value: 'QLD', label: 'QLD', fullName: 'Queensland' },
  { value: 'SA', label: 'SA', fullName: 'South Australia' },
  { value: 'WA', label: 'WA', fullName: 'Western Australia' },
  { value: 'TAS', label: 'TAS', fullName: 'Tasmania' },
  { value: 'NT', label: 'NT', fullName: 'Northern Territory' },
  { value: 'ACT', label: 'ACT', fullName: 'Australian Capital Territory' },
]

export function getStateFullName(state: AustralianState): string {
  return australianStates.find(s => s.value === state)?.fullName || state
}

// Risk level helpers
export function getRiskLevelColor(level: RiskLevel): string {
  switch (level) {
    case 'low':
      return 'text-success-600 bg-success-50 border-success-200'
    case 'medium':
      return 'text-warning-600 bg-warning-50 border-warning-200'
    case 'high':
      return 'text-danger-600 bg-danger-50 border-danger-200'
    case 'critical':
      return 'text-danger-700 bg-danger-100 border-danger-300'
    default:
      return 'text-neutral-600 bg-neutral-50 border-neutral-200'
  }
}

export function getRiskLevelIcon(level: RiskLevel): string {
  switch (level) {
    case 'low':
      return '🟢'
    case 'medium':
      return '🟡'
    case 'high':
      return '🟠'
    case 'critical':
      return '🔴'
    default:
      return '⚪'
  }
}

// Document status helpers
export function getDocumentStatusColor(status: string): string {
  switch (status) {
    case 'uploaded':
      return 'text-primary-600 bg-primary-50 border-primary-200'
    case 'processing':
      return 'text-warning-600 bg-warning-50 border-warning-200'
    case 'processed':
      return 'text-success-600 bg-success-50 border-success-200'
    case 'failed':
      return 'text-danger-600 bg-danger-50 border-danger-200'
    default:
      return 'text-neutral-600 bg-neutral-50 border-neutral-200'
  }
}

// Analysis progress helpers
export function getProgressColor(progress: number): string {
  if (progress < 25) return 'bg-danger-500'
  if (progress < 50) return 'bg-warning-500'
  if (progress < 75) return 'bg-primary-500'
  return 'bg-success-500'
}

// URL helpers
export function isValidUrl(string: string): boolean {
  try {
    new URL(string)
    return true
  } catch (_) {
    return false
  }
}

// File validation
export function validateFileType(file: File, allowedTypes: string[]): boolean {
  const fileExtension = file.name.split('.').pop()?.toLowerCase()
  return fileExtension ? allowedTypes.includes(fileExtension) : false
}

export function validateFileSize(file: File, maxSizeInMB: number): boolean {
  const maxSizeInBytes = maxSizeInMB * 1024 * 1024
  return file.size <= maxSizeInBytes
}

// Text helpers
export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

export function capitalizeFirst(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1)
}

// Array helpers
export function groupBy<T>(array: T[], key: keyof T): Record<string, T[]> {
  return array.reduce((groups, item) => {
    const group = (item[key] as unknown as string) || 'Other'
    groups[group] = groups[group] || []
    groups[group].push(item)
    return groups
  }, {} as Record<string, T[]>)
}

// Debounce function
export function debounce<T extends (...args: never[]) => unknown>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | undefined
  return (...args: Parameters<T>) => {
    clearTimeout(timeout)
    timeout = setTimeout(() => func(...args), wait)
  }
}

// Local storage helpers
export function getFromStorage<T = unknown>(key: string): T | null {
  try {
    const item = localStorage.getItem(key)
    return item ? (JSON.parse(item) as T) : null
  } catch (error) {
    console.error('Error reading from localStorage:', error)
    return null
  }
}

export function setToStorage(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch (error) {
    console.error('Error writing to localStorage:', error)
  }
}

export function removeFromStorage(key: string): void {
  try {
    localStorage.removeItem(key)
  } catch (error) {
    console.error('Error removing from localStorage:', error)
  }
}

// Error helpers
export function getErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message
  if (typeof error === 'string') return error
  return 'An unexpected error occurred'
}

// Accessibility helpers
export function generateId(prefix: string = 'id'): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}

// Australian-specific helpers
export function formatABN(abn: string): string {
  // Format ABN with spaces: 12 345 678 901
  return abn.replace(/(\d{2})(\d{3})(\d{3})(\d{3})/, '$1 $2 $3 $4')
}

export function validateABN(abn: string): boolean {
  // Basic ABN validation (simplified)
  const cleanABN = abn.replace(/\s/g, '')
  return /^\d{11}$/.test(cleanABN)
}

// Contract-specific helpers
export function getContractTypeLabel(type: string): string {
  switch (type) {
    case 'purchase_agreement':
      return 'Purchase Agreement'
    case 'lease_agreement':
      return 'Lease Agreement'
    case 'off_plan':
      return 'Off the Plan'
    case 'auction':
      return 'Auction Contract'
    default:
      return capitalizeFirst(type.replace('_', ' '))
  }
}

export function getUserTypeLabel(type: string): string {
  switch (type) {
    case 'buyer':
      return 'Property Buyer'
    case 'investor':
      return 'Property Investor'
    case 'agent':
      return 'Real Estate Agent'
    default:
      return capitalizeFirst(type)
  }
}