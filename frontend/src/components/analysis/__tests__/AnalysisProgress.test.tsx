import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';
import AnalysisProgress from '../AnalysisProgress';

// Mock the analysis store
const mockAnalysisStore = {
  isAnalyzing: false,
  analysisProgress: null,
  currentAnalysis: null,
  wsService: null,
  analysisError: null,
  triggerAnalysisRetry: vi.fn(),
  cacheStatus: null,
};

vi.mock('@/store/analysisStore', () => ({
  useAnalysisStore: (selector: any) => selector(mockAnalysisStore),
}));

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: any) => children,
}));

// Mock utils
vi.mock('@/utils', () => ({
  cn: (...args: any[]) => args.filter(Boolean).join(' '),
  formatRelativeTime: (date: any) => 'a few minutes ago',
}));

describe('AnalysisProgress', () => {
  it('should render default state when no analysis', () => {
    render(<AnalysisProgress />);
    
    expect(screen.getByText('Contract Analysis')).toBeInTheDocument();
    expect(screen.getByText('Ready for Analysis')).toBeInTheDocument();
    expect(screen.getByText('Upload a document to begin contract analysis.')).toBeInTheDocument();
  });

  it('should show correct steps with new progress structure', () => {
    // Mock store with progress data
    const progressStore = {
      ...mockAnalysisStore,
      isAnalyzing: true,
      analysisProgress: {
        current_step: 'validate_input',
        progress_percent: 7,
        step_description: 'Initialize analysis',
      },
    };

    vi.mocked(require('@/store/analysisStore').useAnalysisStore).mockImplementation(
      (selector: any) => selector(progressStore)
    );

    render(<AnalysisProgress />);
    
    // Check that the new steps are present per PRD
    expect(screen.getByText('Upload document')).toBeInTheDocument();      // 5%
    expect(screen.getByText('Initialize analysis')).toBeInTheDocument();  // 7%
    expect(screen.getByText('Extract text & diagrams')).toBeInTheDocument(); // 7-30%
    expect(screen.getByText('Validate document quality')).toBeInTheDocument(); // 34% (conditional)
    expect(screen.getByText('Extract contract terms')).toBeInTheDocument(); // 42%
    expect(screen.getByText('Validate terms completeness')).toBeInTheDocument(); // 50%
    expect(screen.getByText('Analyze compliance')).toBeInTheDocument(); // 57%
    expect(screen.getByText('Assess risks')).toBeInTheDocument(); // 71%
    expect(screen.getByText('Generate recommendations')).toBeInTheDocument(); // 85%
    expect(screen.getByText('Compile report')).toBeInTheDocument(); // 98%
  });

  it('should hide validate_document_quality step when disabled', () => {
    // Mock store with progress that skipped quality validation (jumped from 30% to 42%)
    const progressStore = {
      ...mockAnalysisStore,
      isAnalyzing: true,
      analysisProgress: {
        current_step: 'extract_terms',
        progress_percent: 42,
        step_description: 'Extracting key contract terms using Australian tools',
      },
    };

    vi.mocked(require('@/store/analysisStore').useAnalysisStore).mockImplementation(
      (selector: any) => selector(progressStore)
    );

    render(<AnalysisProgress />);
    
    // The validate_document_quality step should be filtered out
    const qualityStep = screen.queryByText('Validate document quality');
    expect(qualityStep).not.toBeInTheDocument();
    
    // But other steps should still be visible
    expect(screen.getByText('Extract contract terms')).toBeInTheDocument();
  });

  it('should show progress percentage correctly', () => {
    const progressStore = {
      ...mockAnalysisStore,
      isAnalyzing: true,
      analysisProgress: {
        current_step: 'document_processing',
        progress_percent: 25,
        step_description: 'Extract text & diagrams',
      },
    };

    vi.mocked(require('@/store/analysisStore').useAnalysisStore).mockImplementation(
      (selector: any) => selector(progressStore)
    );

    render(<AnalysisProgress />);
    
    expect(screen.getByText('25%')).toBeInTheDocument();
    expect(screen.getByText('Complete')).toBeInTheDocument();
  });
});