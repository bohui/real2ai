/**
 * Evaluation Job Creation Form Component
 * 
 * Multi-step form for creating evaluation jobs with:
 * - Basic job configuration
 * - Prompt template selection
 * - Dataset selection  
 * - Model configuration
 * - Metrics configuration
 */

import React, { useState, useEffect } from 'react';
import Button from '../ui/Button';
import Input from '../ui/Input';
import { Card } from '../ui/Card';
import Alert from '../ui/Alert';
import Loading from '../ui/Loading';
import { useJobCreation } from '../../store/evaluationStore';
import type { ModelConfig, MetricsConfig } from '../../services/evaluationApi';

interface EvaluationJobFormProps {
  onSuccess?: (jobId: string) => void;
  onCancel?: () => void;
}

interface FormData {
  name: string;
  description: string;
  prompt_template_id: string;
  dataset_id: string;
  model_configs: ModelConfig[];
  metrics_config: MetricsConfig;
  priority: number;
}

const INITIAL_METRICS_CONFIG: MetricsConfig = {
  bleu_enabled: false,
  rouge_enabled: false,
  semantic_similarity_enabled: true,
  faithfulness_enabled: true,
  relevance_enabled: true,
  coherence_enabled: true,
  custom_metrics: [],
  metric_weights: {
    semantic_similarity: 0.3,
    faithfulness: 0.3,
    relevance: 0.2,
    coherence: 0.2,
  },
};

const MODEL_PROVIDERS = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'gemini', label: 'Google Gemini' },
];

const OPENAI_MODELS = [
  'gpt-4o',
  'gpt-4o-mini',
  'gpt-4-turbo',
  'gpt-3.5-turbo',
];

const GEMINI_MODELS = [
  'gemini-pro',
  'gemini-pro-vision',
  'gemini-1.5-pro',
  'gemini-1.5-flash',
];

export const EvaluationJobForm: React.FC<EvaluationJobFormProps> = ({
  onSuccess,
  onCancel,
}) => {
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState<FormData>({
    name: '',
    description: '',
    prompt_template_id: '',
    dataset_id: '',
    model_configs: [],
    metrics_config: INITIAL_METRICS_CONFIG,
    priority: 5,
  });
  
  const [newModelConfig, setNewModelConfig] = useState<ModelConfig>({
    model_name: '',
    provider: 'openai',
    parameters: {
      temperature: 0.7,
      max_tokens: 1000,
    },
  });

  const {
    promptTemplates,
    testDatasets,
    loading,
    error,
    actions,
  } = useJobCreation();

  useEffect(() => {
    actions.fetchPromptTemplates();
    actions.fetchTestDatasets();
  }, [actions]);

  const updateFormData = (field: keyof FormData, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const addModelConfig = () => {
    if (!newModelConfig.model_name || !newModelConfig.provider) {
      return;
    }
    
    setFormData(prev => ({
      ...prev,
      model_configs: [...prev.model_configs, { ...newModelConfig }],
    }));
    
    setNewModelConfig({
      model_name: '',
      provider: 'openai',
      parameters: { temperature: 0.7, max_tokens: 1000 },
    });
  };

  const removeModelConfig = (index: number) => {
    setFormData(prev => ({
      ...prev,
      model_configs: prev.model_configs.filter((_, i) => i !== index),
    }));
  };

  const updateMetricsConfig = (field: keyof MetricsConfig, value: any) => {
    setFormData(prev => ({
      ...prev,
      metrics_config: {
        ...prev.metrics_config,
        [field]: value,
      },
    }));
  };

  const updateMetricWeight = (metric: string, weight: number) => {
    setFormData(prev => ({
      ...prev,
      metrics_config: {
        ...prev.metrics_config,
        metric_weights: {
          ...prev.metrics_config.metric_weights,
          [metric]: weight,
        },
      },
    }));
  };

  const canProceedToStep = (step: number): boolean => {
    switch (step) {
      case 1:
        return formData.name.trim() !== '';
      case 2:
        return formData.prompt_template_id !== '';
      case 3:
        return formData.dataset_id !== '';
      case 4:
        return formData.model_configs.length > 0;
      default:
        return true;
    }
  };

  const handleSubmit = async () => {
    try {
      const job = await actions.createJob(formData);
      onSuccess?.(job.id);
    } catch (error) {
      console.error('Failed to create job:', error);
    }
  };

  const renderBasicInfo = () => (
    <Card className="p-6">
      <h3 className="text-lg font-semibold mb-4">Basic Information</h3>
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-2">Job Name *</label>
          <Input
            value={formData.name}
            onChange={(e) => updateFormData('name', e.target.value)}
            placeholder="Enter evaluation job name"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-2">Description</label>
          <textarea
            className="w-full p-3 border border-gray-300 rounded-md resize-none"
            rows={3}
            value={formData.description}
            onChange={(e) => updateFormData('description', e.target.value)}
            placeholder="Optional description for this evaluation"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-2">Priority (1-10)</label>
          <Input
            type="number"
            min={1}
            max={10}
            value={formData.priority}
            onChange={(e) => updateFormData('priority', parseInt(e.target.value))}
          />
        </div>
      </div>
    </Card>
  );

  const renderPromptTemplateSelection = () => (
    <Card className="p-6">
      <h3 className="text-lg font-semibold mb-4">Select Prompt Template</h3>
      <div className="space-y-4">
        <select
          className="w-full p-3 border border-gray-300 rounded-md"
          value={formData.prompt_template_id}
          onChange={(e) => updateFormData('prompt_template_id', e.target.value)}
        >
          <option value="">Select a prompt template</option>
          {promptTemplates.map((template) => (
            <option key={template.id} value={template.id}>
              {template.name} v{template.version}
            </option>
          ))}
        </select>
        
        {formData.prompt_template_id && (
          <div className="p-4 bg-gray-50 rounded-md">
            {(() => {
              const selected = promptTemplates.find(t => t.id === formData.prompt_template_id);
              return selected ? (
                <div>
                  <h4 className="font-medium">{selected.name}</h4>
                  <p className="text-sm text-gray-600 mt-1">{selected.description}</p>
                  <div className="mt-2">
                    <pre className="text-xs bg-white p-2 rounded border max-h-32 overflow-y-auto">
                      {selected.template_content}
                    </pre>
                  </div>
                </div>
              ) : null;
            })()}
          </div>
        )}
      </div>
    </Card>
  );

  const renderDatasetSelection = () => (
    <Card className="p-6">
      <h3 className="text-lg font-semibold mb-4">Select Test Dataset</h3>
      <div className="space-y-4">
        <select
          className="w-full p-3 border border-gray-300 rounded-md"
          value={formData.dataset_id}
          onChange={(e) => updateFormData('dataset_id', e.target.value)}
        >
          <option value="">Select a test dataset</option>
          {testDatasets.map((dataset) => (
            <option key={dataset.id} value={dataset.id}>
              {dataset.name} ({dataset.size} test cases)
            </option>
          ))}
        </select>
        
        {formData.dataset_id && (
          <div className="p-4 bg-gray-50 rounded-md">
            {(() => {
              const selected = testDatasets.find(d => d.id === formData.dataset_id);
              return selected ? (
                <div>
                  <h4 className="font-medium">{selected.name}</h4>
                  <p className="text-sm text-gray-600 mt-1">{selected.description}</p>
                  <div className="text-sm mt-2">
                    <span className="text-blue-600 font-medium">{selected.size} test cases</span>
                    {selected.domain && (
                      <span className="ml-4 text-gray-600">Domain: {selected.domain}</span>
                    )}
                  </div>
                </div>
              ) : null;
            })()}
          </div>
        )}
      </div>
    </Card>
  );

  const renderModelConfiguration = () => (
    <Card className="p-6">
      <h3 className="text-lg font-semibold mb-4">Model Configuration</h3>
      
      {/* Existing Models */}
      {formData.model_configs.length > 0 && (
        <div className="mb-6">
          <h4 className="font-medium mb-3">Selected Models</h4>
          <div className="space-y-2">
            {formData.model_configs.map((config, index) => (
              <div key={index} className="flex items-center justify-between p-3 border rounded-md">
                <div>
                  <span className="font-medium">{config.provider}/{config.model_name}</span>
                  <span className="text-sm text-gray-600 ml-2">
                    temp: {config.parameters.temperature}, tokens: {config.parameters.max_tokens}
                  </span>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => removeModelConfig(index)}
                >
                  Remove
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Add New Model */}
      <div className="border-t pt-4">
        <h4 className="font-medium mb-3">Add Model</h4>
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium mb-2">Provider</label>
            <select
              className="w-full p-3 border border-gray-300 rounded-md"
              value={newModelConfig.provider}
              onChange={(e) => 
                setNewModelConfig(prev => ({ 
                  ...prev, 
                  provider: e.target.value as 'openai' | 'gemini',
                  model_name: '' // Reset model selection
                }))
              }
            >
              {MODEL_PROVIDERS.map((provider) => (
                <option key={provider.value} value={provider.value}>
                  {provider.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Model</label>
            <select
              className="w-full p-3 border border-gray-300 rounded-md"
              value={newModelConfig.model_name}
              onChange={(e) => 
                setNewModelConfig(prev => ({ ...prev, model_name: e.target.value }))
              }
            >
              <option value="">Select model</option>
              {(newModelConfig.provider === 'openai' ? OPENAI_MODELS : GEMINI_MODELS).map((model) => (
                <option key={model} value={model}>
                  {model}
                </option>
              ))}
            </select>
          </div>
        </div>
        
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium mb-2">Temperature</label>
            <Input
              type="number"
              min={0}
              max={2}
              step={0.1}
              value={newModelConfig.parameters.temperature}
              onChange={(e) => 
                setNewModelConfig(prev => ({
                  ...prev,
                  parameters: { ...prev.parameters, temperature: parseFloat(e.target.value) }
                }))
              }
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Max Tokens</label>
            <Input
              type="number"
              min={1}
              max={4000}
              value={newModelConfig.parameters.max_tokens}
              onChange={(e) => 
                setNewModelConfig(prev => ({
                  ...prev,
                  parameters: { ...prev.parameters, max_tokens: parseInt(e.target.value) }
                }))
              }
            />
          </div>
        </div>
        
        <Button onClick={addModelConfig} disabled={!newModelConfig.model_name}>
          Add Model
        </Button>
      </div>
    </Card>
  );

  const renderMetricsConfiguration = () => (
    <Card className="p-6">
      <h3 className="text-lg font-semibold mb-4">Metrics Configuration</h3>
      
      <div className="space-y-6">
        {/* Metric Toggles */}
        <div>
          <h4 className="font-medium mb-3">Enabled Metrics</h4>
          <div className="grid grid-cols-2 gap-4">
            {Object.entries({
              bleu_enabled: 'BLEU Score',
              rouge_enabled: 'ROUGE Score',
              semantic_similarity_enabled: 'Semantic Similarity',
              faithfulness_enabled: 'Faithfulness',
              relevance_enabled: 'Relevance',
              coherence_enabled: 'Coherence',
            }).map(([key, label]) => (
              <label key={key} className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={formData.metrics_config[key as keyof MetricsConfig] as boolean}
                  onChange={(e) => updateMetricsConfig(key as keyof MetricsConfig, e.target.checked)}
                  className="rounded"
                />
                <span className="text-sm">{label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Metric Weights */}
        <div>
          <h4 className="font-medium mb-3">Metric Weights</h4>
          <div className="space-y-3">
            {Object.entries(formData.metrics_config.metric_weights).map(([metric, weight]) => (
              <div key={metric} className="flex items-center space-x-4">
                <span className="w-32 text-sm capitalize">{metric.replace('_', ' ')}</span>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.1}
                  value={weight}
                  onChange={(e) => updateMetricWeight(metric, parseFloat(e.target.value))}
                  className="flex-1"
                />
                <span className="w-12 text-sm">{weight.toFixed(1)}</span>
              </div>
            ))}
          </div>
          <div className="mt-2 text-xs text-gray-600">
            Total weight: {Object.values(formData.metrics_config.metric_weights).reduce((a, b) => a + b, 0).toFixed(1)}
          </div>
        </div>
      </div>
    </Card>
  );

  const STEPS = [
    { number: 1, title: 'Basic Info', component: renderBasicInfo },
    { number: 2, title: 'Prompt Template', component: renderPromptTemplateSelection },
    { number: 3, title: 'Test Dataset', component: renderDatasetSelection },
    { number: 4, title: 'Models', component: renderModelConfiguration },
    { number: 5, title: 'Metrics', component: renderMetricsConfiguration },
  ];

  return (
    <div className="max-w-4xl mx-auto p-6">
      {/* Step Indicator */}
      <div className="flex items-center justify-between mb-8">
        {STEPS.map((step, index) => (
          <div key={step.number} className="flex items-center">
            <div className={`
              w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium
              ${currentStep >= step.number 
                ? 'bg-blue-600 text-white' 
                : 'bg-gray-200 text-gray-600'
              }
            `}>
              {step.number}
            </div>
            <span className={`ml-2 text-sm ${currentStep >= step.number ? 'text-blue-600' : 'text-gray-500'}`}>
              {step.title}
            </span>
            {index < STEPS.length - 1 && (
              <div className={`mx-4 h-0.5 w-16 ${currentStep > step.number ? 'bg-blue-600' : 'bg-gray-200'}`} />
            )}
          </div>
        ))}
      </div>

      {/* Error Alert */}
      {error && (
        <Alert type="danger" className="mb-6">
          {error}
        </Alert>
      )}

      {/* Current Step Content */}
      <div className="mb-8">
        {STEPS[currentStep - 1].component()}
      </div>

      {/* Navigation */}
      <div className="flex justify-between">
        <div className="space-x-3">
          {onCancel && (
            <Button variant="outline" onClick={onCancel}>
              Cancel
            </Button>
          )}
          {currentStep > 1 && (
            <Button
              variant="outline"
              onClick={() => setCurrentStep(currentStep - 1)}
            >
              Previous
            </Button>
          )}
        </div>

        <div className="space-x-3">
          {currentStep < STEPS.length ? (
            <Button
              onClick={() => setCurrentStep(currentStep + 1)}
              disabled={!canProceedToStep(currentStep)}
            >
              Next
            </Button>
          ) : (
            <Button
              onClick={handleSubmit}
              disabled={loading || !canProceedToStep(currentStep)}
            >
              {loading ? <Loading size="sm" /> : 'Create Evaluation Job'}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};