/**
 * Test DocumentUpload component
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@/test/utils'
import { DocumentUpload } from '../DocumentUpload'
import { createMockFile } from '@/test/utils'

// Mock API service
vi.mock('@/services/api', () => ({
  default: {
    uploadDocument: vi.fn(),
  },
}))

describe('DocumentUpload Component', () => {
  const mockOnUploadComplete = vi.fn()
  const mockOnUploadError = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders upload dropzone', () => {
    render(<DocumentUpload onUploadComplete={mockOnUploadComplete} />)
    
    expect(screen.getByText(/drag & drop your contract/i)).toBeInTheDocument()
    expect(screen.getByText(/browse files/i)).toBeInTheDocument()
    expect(screen.getByText(/pdf, doc, docx up to 10mb/i)).toBeInTheDocument()
  })

  it('accepts file drop', async () => {
    const mockUpload = vi.fn().mockResolvedValue({
      document_id: 'test-doc-id',
      filename: 'test-contract.pdf',
      upload_status: 'uploaded',
    })
    
    vi.mocked(vi.importActual('@/services/api')).default.uploadDocument = mockUpload
    
    render(<DocumentUpload onUploadComplete={mockOnUploadComplete} />)
    
    const dropzone = screen.getByRole('button', { name: /upload area/i })
    const file = createMockFile('test-contract.pdf', 1024000, 'application/pdf')
    
    fireEvent.drop(dropzone, {
      dataTransfer: {
        files: [file],
      },
    })
    
    await waitFor(() => {
      expect(mockUpload).toHaveBeenCalledWith(file, expect.any(Object))
    })
  })

  it('accepts file selection via browse', async () => {
    const mockUpload = vi.fn().mockResolvedValue({
      document_id: 'test-doc-id',
      filename: 'test-contract.pdf',
      upload_status: 'uploaded',
    })
    
    vi.mocked(vi.importActual('@/services/api')).default.uploadDocument = mockUpload
    
    render(<DocumentUpload onUploadComplete={mockOnUploadComplete} />)
    
    const fileInput = screen.getByLabelText(/file upload/i)
    const file = createMockFile('test-contract.pdf', 1024000, 'application/pdf')
    
    fireEvent.change(fileInput, { target: { files: [file] } })
    
    await waitFor(() => {
      expect(mockUpload).toHaveBeenCalledWith(file, expect.any(Object))
    })
  })

  it('shows upload progress', async () => {
    const mockUpload = vi.fn().mockImplementation(() => 
      new Promise(resolve => setTimeout(() => resolve({
        document_id: 'test-doc-id',
        filename: 'test-contract.pdf',
        upload_status: 'uploaded',
      }), 1000))
    )
    
    vi.mocked(vi.importActual('@/services/api')).default.uploadDocument = mockUpload
    
    render(<DocumentUpload onUploadComplete={mockOnUploadComplete} />)
    
    const fileInput = screen.getByLabelText(/file upload/i)
    const file = createMockFile('test-contract.pdf', 1024000, 'application/pdf')
    
    fireEvent.change(fileInput, { target: { files: [file] } })
    
    await waitFor(() => {
      expect(screen.getByText(/uploading/i)).toBeInTheDocument()
      expect(screen.getByRole('progressbar')).toBeInTheDocument()
    })
  })

  it('calls onUploadComplete on successful upload', async () => {
    const uploadResponse = {
      document_id: 'test-doc-id',
      filename: 'test-contract.pdf',
      upload_status: 'uploaded',
    }
    
    const mockUpload = vi.fn().mockResolvedValue(uploadResponse)
    vi.mocked(vi.importActual('@/services/api')).default.uploadDocument = mockUpload
    
    render(<DocumentUpload onUploadComplete={mockOnUploadComplete} />)
    
    const fileInput = screen.getByLabelText(/file upload/i)
    const file = createMockFile('test-contract.pdf', 1024000, 'application/pdf')
    
    fireEvent.change(fileInput, { target: { files: [file] } })
    
    await waitFor(() => {
      expect(mockOnUploadComplete).toHaveBeenCalledWith(uploadResponse)
    })
  })

  it('handles upload errors', async () => {
    const mockUpload = vi.fn().mockRejectedValue(new Error('Upload failed'))
    vi.mocked(vi.importActual('@/services/api')).default.uploadDocument = mockUpload
    
    render(<DocumentUpload onUploadError={mockOnUploadError} />)
    
    const fileInput = screen.getByLabelText(/file upload/i)
    const file = createMockFile('test-contract.pdf', 1024000, 'application/pdf')
    
    fireEvent.change(fileInput, { target: { files: [file] } })
    
    await waitFor(() => {
      expect(mockOnUploadError).toHaveBeenCalledWith(expect.any(Error))
    })
  })

  it('rejects invalid file types', async () => {
    render(<DocumentUpload onUploadError={mockOnUploadError} />)
    
    const fileInput = screen.getByLabelText(/file upload/i)
    const file = createMockFile('test.txt', 1024, 'text/plain')
    
    fireEvent.change(fileInput, { target: { files: [file] } })
    
    await waitFor(() => {
      expect(screen.getByText(/file type not supported/i)).toBeInTheDocument()
    })
  })

  it('rejects files that are too large', async () => {
    render(<DocumentUpload onUploadError={mockOnUploadError} />)
    
    const fileInput = screen.getByLabelText(/file upload/i)
    const file = createMockFile('large-file.pdf', 20 * 1024 * 1024, 'application/pdf') // 20MB
    
    fireEvent.change(fileInput, { target: { files: [file] } })
    
    await waitFor(() => {
      expect(screen.getByText(/file size too large/i)).toBeInTheDocument()
    })
  })

  it('shows contract type selection', () => {
    render(<DocumentUpload onUploadComplete={mockOnUploadComplete} />)
    
    expect(screen.getByLabelText(/contract type/i)).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /purchase agreement/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /lease agreement/i })).toBeInTheDocument()
  })

  it('shows Australian state selection', () => {
    render(<DocumentUpload onUploadComplete={mockOnUploadComplete} />)
    
    expect(screen.getByLabelText(/australian state/i)).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /nsw/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /vic/i })).toBeInTheDocument()
  })

  it('includes contract type and state in upload', async () => {
    const mockUpload = vi.fn().mockResolvedValue({
      document_id: 'test-doc-id',
      filename: 'test-contract.pdf',
      upload_status: 'uploaded',
    })
    
    vi.mocked(vi.importActual('@/services/api')).default.uploadDocument = mockUpload
    
    render(<DocumentUpload onUploadComplete={mockOnUploadComplete} />)
    
    // Select contract type and state
    const contractTypeSelect = screen.getByLabelText(/contract type/i)
    const stateSelect = screen.getByLabelText(/australian state/i)
    
    fireEvent.change(contractTypeSelect, { target: { value: 'lease_agreement' } })
    fireEvent.change(stateSelect, { target: { value: 'VIC' } })
    
    const fileInput = screen.getByLabelText(/file upload/i)
    const file = createMockFile('test-contract.pdf', 1024000, 'application/pdf')
    
    fireEvent.change(fileInput, { target: { files: [file] } })
    
    await waitFor(() => {
      expect(mockUpload).toHaveBeenCalledWith(file, {
        contract_type: 'lease_agreement',
        australian_state: 'VIC',
      })
    })
  })

  it('can be reset after upload', async () => {
    const mockUpload = vi.fn().mockResolvedValue({
      document_id: 'test-doc-id',
      filename: 'test-contract.pdf',
      upload_status: 'uploaded',
    })
    
    vi.mocked(vi.importActual('@/services/api')).default.uploadDocument = mockUpload
    
    render(<DocumentUpload onUploadComplete={mockOnUploadComplete} />)
    
    const fileInput = screen.getByLabelText(/file upload/i)
    const file = createMockFile('test-contract.pdf', 1024000, 'application/pdf')
    
    fireEvent.change(fileInput, { target: { files: [file] } })
    
    await waitFor(() => {
      expect(screen.getByText(/upload successful/i)).toBeInTheDocument()
    })
    
    const resetButton = screen.getByRole('button', { name: /upload another/i })
    fireEvent.click(resetButton)
    
    expect(screen.getByText(/drag & drop your contract/i)).toBeInTheDocument()
  })

  it('has proper accessibility attributes', () => {
    render(<DocumentUpload onUploadComplete={mockOnUploadComplete} />)
    
    const dropzone = screen.getByRole('button', { name: /upload area/i })
    const fileInput = screen.getByLabelText(/file upload/i)
    
    expect(dropzone).toHaveAttribute('aria-describedby')
    expect(fileInput).toHaveAttribute('accept', '.pdf,.doc,.docx')
    expect(fileInput).toHaveAttribute('multiple', 'false')
  })
})