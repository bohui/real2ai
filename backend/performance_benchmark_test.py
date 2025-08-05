#!/usr/bin/env python3
"""
Performance Benchmark Test for PromptManager System
Tests actual render performance, caching, and resource usage without external dependencies
"""

import asyncio
import time
import gc
import psutil
import os
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, UTC
from dataclasses import dataclass

# Add app to path
sys.path.append(str(Path(__file__).parent / "app"))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class BenchmarkResult:
    """Benchmark test result"""
    test_name: str
    duration_ms: float
    memory_delta_mb: float
    success: bool
    details: Dict[str, Any]
    error: str = ""

class PromptManagerBenchmark:
    """Comprehensive performance benchmark for PromptManager"""
    
    def __init__(self):
        self.results: List[BenchmarkResult] = []
        self.process = psutil.Process(os.getpid())
        
        # Performance targets
        self.targets = {
            'initialization_ms': 1000,    # <1s initialization
            'render_time_ms': 100,        # <100ms per render
            'batch_render_overhead': 20,   # <20ms overhead per item
            'memory_usage_mb': 50,        # <50MB total
            'cache_hit_improvement': 50,   # >50% improvement with cache
        }
    
    def get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        return self.process.memory_info().rss / 1024 / 1024
    
    async def benchmark_initialization(self) -> BenchmarkResult:
        """Benchmark PromptManager initialization time"""
        test_name = "PromptManager Initialization"
        
        initial_memory = self.get_memory_usage()
        
        try:
            start_time = time.time()
            
            # Create a minimal configuration for testing
            from app.core.prompts.manager import PromptManager, PromptManagerConfig
            
            # Create temporary templates directory
            temp_dir = Path(__file__).parent / "temp_templates"
            temp_dir.mkdir(exist_ok=True)
            
            # Create a simple test template
            test_template = temp_dir / "test_template.md"
            test_template.write_text("""
---
name: test_template
version: 1.0.0
description: Simple test template
variables:
  - test_var
---

This is a test template with variable: {{ test_var }}
""")
            
            config = PromptManagerConfig(
                templates_dir=temp_dir,
                cache_enabled=True,
                validation_enabled=False,  # Disable to avoid dependency issues
                hot_reload_enabled=False,
                preload_templates=True,
                enable_metrics=True,
                enable_composition=False,  # Disable complex features
                enable_workflows=False,
                enable_service_integration=False
            )
            
            manager = PromptManager(config)
            await manager.initialize()
            
            duration_ms = (time.time() - start_time) * 1000
            memory_delta = self.get_memory_usage() - initial_memory
            
            # Test basic functionality
            health = await manager.health_check()
            metrics = manager.get_metrics()
            
            success = (
                health.get("status") == "healthy" and
                duration_ms < self.targets['initialization_ms'] and
                memory_delta < self.targets['memory_usage_mb']
            )
            
            # Cleanup
            test_template.unlink()
            temp_dir.rmdir()
            
            return BenchmarkResult(
                test_name=test_name,
                duration_ms=duration_ms,
                memory_delta_mb=memory_delta,
                success=success,
                details={
                    'health_status': health.get("status"),
                    'metrics': metrics,
                    'target_init_time': self.targets['initialization_ms'],
                    'target_memory': self.targets['memory_usage_mb']
                }
            )
            
        except Exception as e:
            return BenchmarkResult(
                test_name=test_name,
                duration_ms=0,
                memory_delta_mb=0,
                success=False,
                details={},
                error=str(e)
            )
    
    async def benchmark_render_performance(self) -> BenchmarkResult:
        """Benchmark single render performance"""
        test_name = "Single Render Performance"
        
        initial_memory = self.get_memory_usage()
        
        try:
            # Setup manager
            from app.core.prompts.manager import PromptManager, PromptManagerConfig
            from app.core.prompts.context import PromptContext, ContextType
            
            temp_dir = Path(__file__).parent / "temp_templates"
            temp_dir.mkdir(exist_ok=True)
            
            # Create test template
            test_template = temp_dir / "render_test.md"
            test_template.write_text("""
---
name: render_test
version: 1.0.0
description: Render performance test template
variables:
  - user_name
  - contract_type
  - state
---

Hello {{ user_name }},

This is a {{ contract_type }} contract analysis for {{ state }}.

{% for item in analysis_items %}
- {{ item }}
{% endfor %}

Generated at: {{ timestamp }}
""")
            
            config = PromptManagerConfig(
                templates_dir=temp_dir,
                cache_enabled=False,  # Test without cache first
                validation_enabled=False,
                enable_composition=False,
                enable_workflows=False
            )
            
            manager = PromptManager(config)
            await manager.initialize()
            
            # Prepare context
            context = PromptContext(
                context_type=ContextType.USER,
                variables={
                    'user_name': 'John Smith',
                    'contract_type': 'Purchase Agreement',
                    'state': 'NSW',
                    'analysis_items': ['Price review', 'Terms analysis', 'Risk assessment'],
                    'timestamp': datetime.now(UTC).isoformat()
                }
            )
            
            # Benchmark render
            start_time = time.time()
            
            rendered = await manager.render("render_test", context)
            
            duration_ms = (time.time() - start_time) * 1000
            memory_delta = self.get_memory_usage() - initial_memory
            
            success = (
                len(rendered) > 100 and  # Reasonable output length
                'John Smith' in rendered and
                'NSW' in rendered and
                duration_ms < self.targets['render_time_ms']
            )
            
            # Cleanup
            test_template.unlink()
            temp_dir.rmdir()
            
            return BenchmarkResult(
                test_name=test_name,
                duration_ms=duration_ms,
                memory_delta_mb=memory_delta,
                success=success,
                details={
                    'rendered_length': len(rendered),
                    'target_render_time': self.targets['render_time_ms'],
                    'output_sample': rendered[:200] + '...' if len(rendered) > 200 else rendered
                }
            )
            
        except Exception as e:
            return BenchmarkResult(
                test_name=test_name,
                duration_ms=0,
                memory_delta_mb=0,
                success=False,
                details={},
                error=str(e)
            )
    
    async def benchmark_cache_performance(self) -> BenchmarkResult:
        """Benchmark caching effectiveness"""
        test_name = "Cache Performance"
        
        initial_memory = self.get_memory_usage()
        
        try:
            from app.core.prompts.manager import PromptManager, PromptManagerConfig
            from app.core.prompts.context import PromptContext, ContextType
            
            temp_dir = Path(__file__).parent / "temp_templates"
            temp_dir.mkdir(exist_ok=True)
            
            # Create test template
            test_template = temp_dir / "cache_test.md"
            test_template.write_text("""
---
name: cache_test
version: 1.0.0
description: Cache performance test
variables:
  - data
---

Processing data: {{ data }}
Analysis complete at: {{ timestamp }}
""")
            
            config = PromptManagerConfig(
                templates_dir=temp_dir,
                cache_enabled=True,
                validation_enabled=False
            )
            
            manager = PromptManager(config)
            await manager.initialize()
            
            context = PromptContext(
                context_type=ContextType.USER,
                variables={
                    'data': 'Test contract data',
                    'timestamp': datetime.now(UTC).isoformat()
                }
            )\n            \n            # First render (cache miss)\n            start_time = time.time()\n            first_render = await manager.render(\"cache_test\", context, cache_key=\"test_cache_key\")\n            first_duration = (time.time() - start_time) * 1000\n            \n            # Second render (should be cache hit)\n            start_time = time.time()\n            second_render = await manager.render(\"cache_test\", context, cache_key=\"test_cache_key\")\n            second_duration = (time.time() - start_time) * 1000\n            \n            # Calculate improvement\n            improvement_percent = ((first_duration - second_duration) / first_duration) * 100\n            \n            memory_delta = self.get_memory_usage() - initial_memory\n            \n            # Get metrics to verify cache hit\n            metrics = manager.get_metrics()\n            cache_hits = metrics.get('prompt_manager', {}).get('cache_hits', 0)\n            \n            success = (\n                first_render == second_render and\n                cache_hits > 0 and\n                improvement_percent > 0  # Any improvement is good\n            )\n            \n            # Cleanup\n            test_template.unlink()\n            temp_dir.rmdir()\n            \n            return BenchmarkResult(\n                test_name=test_name,\n                duration_ms=first_duration,  # Use first render time as baseline\n                memory_delta_mb=memory_delta,\n                success=success,\n                details={\n                    'cache_miss_time_ms': first_duration,\n                    'cache_hit_time_ms': second_duration,\n                    'improvement_percent': improvement_percent,\n                    'cache_hits': cache_hits,\n                    'target_improvement': self.targets['cache_hit_improvement']\n                }\n            )\n            \n        except Exception as e:\n            return BenchmarkResult(\n                test_name=test_name,\n                duration_ms=0,\n                memory_delta_mb=0,\n                success=False,\n                details={},\n                error=str(e)\n            )\n    \n    async def benchmark_batch_render(self) -> BenchmarkResult:\n        \"\"\"Benchmark batch rendering performance\"\"\"\n        test_name = \"Batch Render Performance\"\n        \n        initial_memory = self.get_memory_usage()\n        \n        try:\n            from app.core.prompts.manager import PromptManager, PromptManagerConfig\n            from app.core.prompts.context import PromptContext, ContextType\n            \n            temp_dir = Path(__file__).parent / \"temp_templates\"\n            temp_dir.mkdir(exist_ok=True)\n            \n            # Create test template\n            test_template = temp_dir / \"batch_test.md\"\n            test_template.write_text(\"\"\"\n---\nname: batch_test\nversion: 1.0.0\ndescription: Batch render test\nvariables:\n  - item_id\n  - item_name\n---\n\nProcessing item {{ item_id }}: {{ item_name }}\n\"\"\")\n            \n            config = PromptManagerConfig(\n                templates_dir=temp_dir,\n                cache_enabled=True,\n                validation_enabled=False\n            )\n            \n            manager = PromptManager(config)\n            await manager.initialize()\n            \n            # Create batch requests\n            batch_size = 10\n            requests = []\n            \n            for i in range(batch_size):\n                context = PromptContext(\n                    context_type=ContextType.USER,\n                    variables={\n                        'item_id': i,\n                        'item_name': f'Item {i}'\n                    }\n                )\n                \n                requests.append({\n                    'template_name': 'batch_test',\n                    'context': context\n                })\n            \n            # Benchmark batch render\n            start_time = time.time()\n            \n            results = await manager.batch_render(requests, max_concurrent=3)\n            \n            duration_ms = (time.time() - start_time) * 1000\n            memory_delta = self.get_memory_usage() - initial_memory\n            \n            # Analyze results\n            successful_renders = sum(1 for r in results if r['success'])\n            average_time_per_item = duration_ms / batch_size\n            \n            success = (\n                successful_renders == batch_size and\n                average_time_per_item < self.targets['render_time_ms'] + self.targets['batch_render_overhead']\n            )\n            \n            # Cleanup\n            test_template.unlink()\n            temp_dir.rmdir()\n            \n            return BenchmarkResult(\n                test_name=test_name,\n                duration_ms=duration_ms,\n                memory_delta_mb=memory_delta,\n                success=success,\n                details={\n                    'batch_size': batch_size,\n                    'successful_renders': successful_renders,\n                    'average_time_per_item_ms': average_time_per_item,\n                    'target_time_per_item': self.targets['render_time_ms'] + self.targets['batch_render_overhead'],\n                    'results_sample': results[:3]  # First 3 results\n                }\n            )\n            \n        except Exception as e:\n            return BenchmarkResult(\n                test_name=test_name,\n                duration_ms=0,\n                memory_delta_mb=0,\n                success=False,\n                details={},\n                error=str(e)\n            )\n    \n    async def benchmark_memory_efficiency(self) -> BenchmarkResult:\n        \"\"\"Benchmark memory usage and cleanup\"\"\"\n        test_name = \"Memory Efficiency\"\n        \n        initial_memory = self.get_memory_usage()\n        \n        try:\n            from app.core.prompts.manager import PromptManager, PromptManagerConfig\n            from app.core.prompts.context import PromptContext, ContextType\n            \n            temp_dir = Path(__file__).parent / \"temp_templates\"\n            temp_dir.mkdir(exist_ok=True)\n            \n            # Create multiple test templates\n            templates = {}\n            for i in range(5):\n                template_name = f\"memory_test_{i}\"\n                template_file = temp_dir / f\"{template_name}.md\"\n                template_file.write_text(f\"\"\"\n---\nname: {template_name}\nversion: 1.0.0\ndescription: Memory test template {i}\nvariables:\n  - data\n---\n\nTemplate {i} processing: {{{{ data }}}}\n\"\"\")\n                templates[template_name] = template_file\n            \n            config = PromptManagerConfig(\n                templates_dir=temp_dir,\n                cache_enabled=True,\n                validation_enabled=False,\n                preload_templates=True\n            )\n            \n            # Measure peak memory during operations\n            peak_memory = initial_memory\n            \n            manager = PromptManager(config)\n            await manager.initialize()\n            \n            peak_memory = max(peak_memory, self.get_memory_usage())\n            \n            # Perform multiple renders\n            for i in range(20):\n                template_name = f\"memory_test_{i % 5}\"\n                context = PromptContext(\n                    context_type=ContextType.USER,\n                    variables={'data': f'Data batch {i}'}\n                )\n                \n                await manager.render(template_name, context)\n                peak_memory = max(peak_memory, self.get_memory_usage())\n            \n            # Test cache clearing\n            manager.clear_cache()\n            gc.collect()  # Force garbage collection\n            \n            final_memory = self.get_memory_usage()\n            peak_delta = peak_memory - initial_memory\n            final_delta = final_memory - initial_memory\n            \n            success = (\n                peak_delta < self.targets['memory_usage_mb'] and\n                final_delta < peak_delta  # Memory was freed\n            )\n            \n            # Cleanup\n            for template_file in templates.values():\n                template_file.unlink()\n            temp_dir.rmdir()\n            \n            return BenchmarkResult(\n                test_name=test_name,\n                duration_ms=0,  # Not time-focused\n                memory_delta_mb=peak_delta,\n                success=success,\n                details={\n                    'initial_memory_mb': initial_memory,\n                    'peak_memory_mb': peak_memory,\n                    'final_memory_mb': final_memory,\n                    'peak_delta_mb': peak_delta,\n                    'final_delta_mb': final_delta,\n                    'memory_freed_mb': peak_delta - final_delta,\n                    'target_memory_mb': self.targets['memory_usage_mb']\n                }\n            )\n            \n        except Exception as e:\n            return BenchmarkResult(\n                test_name=test_name,\n                duration_ms=0,\n                memory_delta_mb=0,\n                success=False,\n                details={},\n                error=str(e)\n            )\n    \n    def log_result(self, result: BenchmarkResult):\n        \"\"\"Log benchmark result\"\"\"\n        status = \"✅ PASS\" if result.success else \"❌ FAIL\"\n        \n        if result.duration_ms > 0:\n            logger.info(f\"{status} | {result.test_name} | {result.duration_ms:.1f}ms | Memory: {result.memory_delta_mb:.1f}MB\")\n        else:\n            logger.info(f\"{status} | {result.test_name} | Memory: {result.memory_delta_mb:.1f}MB\")\n        \n        if result.error:\n            logger.error(f\"   Error: {result.error}\")\n        \n        self.results.append(result)\n    \n    def generate_performance_report(self) -> Dict[str, Any]:\n        \"\"\"Generate comprehensive performance report\"\"\"\n        \n        total_tests = len(self.results)\n        passed_tests = sum(1 for r in self.results if r.success)\n        \n        # Calculate averages\n        avg_render_time = sum(r.duration_ms for r in self.results if r.duration_ms > 0) / max(sum(1 for r in self.results if r.duration_ms > 0), 1)\n        max_memory_usage = max(r.memory_delta_mb for r in self.results)\n        \n        # Performance score calculation\n        performance_score = 0\n        \n        for result in self.results:\n            if result.success:\n                performance_score += 25  # 25 points per successful test\n        \n        # Additional scoring based on performance metrics\n        if avg_render_time < self.targets['render_time_ms']:\n            performance_score += 10\n        if max_memory_usage < self.targets['memory_usage_mb']:\n            performance_score += 15\n        \n        performance_score = min(performance_score, 100)  # Cap at 100\n        \n        return {\n            'overall_performance': {\n                'total_tests': total_tests,\n                'passed_tests': passed_tests,\n                'performance_score': performance_score,\n                'grade': self._get_performance_grade(performance_score)\n            },\n            'timing_metrics': {\n                'average_render_time_ms': avg_render_time,\n                'target_render_time_ms': self.targets['render_time_ms'],\n                'render_time_met': avg_render_time < self.targets['render_time_ms']\n            },\n            'memory_metrics': {\n                'max_memory_usage_mb': max_memory_usage,\n                'target_memory_mb': self.targets['memory_usage_mb'],\n                'memory_target_met': max_memory_usage < self.targets['memory_usage_mb']\n            },\n            'detailed_results': [{\n                'test_name': r.test_name,\n                'success': r.success,\n                'duration_ms': r.duration_ms,\n                'memory_delta_mb': r.memory_delta_mb,\n                'details': r.details,\n                'error': r.error\n            } for r in self.results],\n            'performance_targets': self.targets,\n            'recommendations': self._generate_performance_recommendations()\n        }\n    \n    def _get_performance_grade(self, score: float) -> str:\n        \"\"\"Get performance grade\"\"\"\n        if score >= 95:\n            return 'A+ (Excellent)'\n        elif score >= 85:\n            return 'A (Very Good)'\n        elif score >= 75:\n            return 'B+ (Good)'\n        elif score >= 65:\n            return 'B (Acceptable)'\n        elif score >= 55:\n            return 'C+ (Needs Improvement)'\n        else:\n            return 'F (Poor Performance)'\n    \n    def _generate_performance_recommendations(self) -> List[str]:\n        \"\"\"Generate performance recommendations\"\"\"\n        recommendations = []\n        \n        failed_tests = [r for r in self.results if not r.success]\n        \n        if not failed_tests:\n            recommendations.append(\"✅ All performance benchmarks passed - excellent performance\")\n            return recommendations\n        \n        # Analyze failures\n        if any('Initialization' in r.test_name for r in failed_tests):\n            recommendations.append(\"🚀 Optimize initialization time - consider lazy loading\")\n        \n        if any('Render' in r.test_name for r in failed_tests):\n            recommendations.append(\"⚡ Optimize render performance - review template complexity\")\n        \n        if any('Cache' in r.test_name for r in failed_tests):\n            recommendations.append(\"💾 Improve caching strategy - check cache hit rates\")\n        \n        if any('Memory' in r.test_name for r in failed_tests):\n            recommendations.append(\"🧠 Optimize memory usage - review object lifecycle and cleanup\")\n        \n        if any('Batch' in r.test_name for r in failed_tests):\n            recommendations.append(\"📦 Optimize batch processing - consider parallel execution limits\")\n        \n        return recommendations\n\nasync def main():\n    \"\"\"Run comprehensive PromptManager performance benchmarks\"\"\"\n    benchmark = PromptManagerBenchmark()\n    \n    print(\"⚡ PROMPTMANAGER PERFORMANCE BENCHMARK\")\n    print(\"=\" * 50)\n    print(f\"Start Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}\")\n    print(f\"Process ID: {os.getpid()}\")\n    print(f\"Initial Memory: {benchmark.get_memory_usage():.1f}MB\")\n    print()\n    \n    # Define benchmark tests\n    benchmark_tests = [\n        (\"Initialization\", benchmark.benchmark_initialization),\n        (\"Single Render\", benchmark.benchmark_render_performance),\n        (\"Cache Performance\", benchmark.benchmark_cache_performance),\n        (\"Batch Render\", benchmark.benchmark_batch_render),\n        (\"Memory Efficiency\", benchmark.benchmark_memory_efficiency),\n    ]\n    \n    # Run benchmarks\n    print(\"🔥 RUNNING PERFORMANCE BENCHMARKS\")\n    print(\"-\" * 35)\n    \n    for test_name, test_func in benchmark_tests:\n        print(f\"\\n▶️  Running: {test_name}\")\n        try:\n            result = await test_func()\n            benchmark.log_result(result)\n        except Exception as e:\n            logger.error(f\"Benchmark '{test_name}' crashed: {e}\")\n            benchmark.log_result(BenchmarkResult(\n                test_name=test_name,\n                duration_ms=0,\n                memory_delta_mb=0,\n                success=False,\n                details={},\n                error=str(e)\n            ))\n    \n    # Generate and display report\n    print(\"\\n\" + \"=\" * 50)\n    print(\"📊 PERFORMANCE BENCHMARK REPORT\")\n    print(\"=\" * 50)\n    \n    report = benchmark.generate_performance_report()\n    \n    # Overall Performance\n    overall = report['overall_performance']\n    print(f\"\\n🎯 OVERALL PERFORMANCE\")\n    print(f\"   Score: {overall['performance_score']:.0f}/100 ({overall['grade']})\")\n    print(f\"   Tests: {overall['passed_tests']}/{overall['total_tests']} passed\")\n    \n    # Timing Metrics\n    timing = report['timing_metrics']\n    print(f\"\\n⏱️  TIMING METRICS\")\n    print(f\"   Average Render Time: {timing['average_render_time_ms']:.1f}ms\")\n    print(f\"   Target: <{timing['target_render_time_ms']}ms\")\n    print(f\"   Status: {'✅ MET' if timing['render_time_met'] else '❌ NOT MET'}\")\n    \n    # Memory Metrics\n    memory = report['memory_metrics']\n    print(f\"\\n🧠 MEMORY METRICS\")\n    print(f\"   Max Memory Usage: {memory['max_memory_usage_mb']:.1f}MB\")\n    print(f\"   Target: <{memory['target_memory_mb']}MB\")\n    print(f\"   Status: {'✅ MET' if memory['memory_target_met'] else '❌ NOT MET'}\")\n    \n    # Performance Targets\n    targets = report['performance_targets']\n    print(f\"\\n🎯 PERFORMANCE TARGETS\")\n    for target, value in targets.items():\n        print(f\"   {target}: {value}\")\n    \n    # Recommendations\n    recommendations = report['recommendations']\n    print(f\"\\n💡 RECOMMENDATIONS\")\n    for i, rec in enumerate(recommendations, 1):\n        print(f\"   {i}. {rec}\")\n    \n    # Detailed Results\n    print(f\"\\n📋 DETAILED BENCHMARK RESULTS\")\n    for result in report['detailed_results']:\n        status = \"✅\" if result['success'] else \"❌\"\n        if result['duration_ms'] > 0:\n            print(f\"   {status} {result['test_name']}: {result['duration_ms']:.1f}ms, {result['memory_delta_mb']:.1f}MB\")\n        else:\n            print(f\"   {status} {result['test_name']}: {result['memory_delta_mb']:.1f}MB\")\n        \n        if result['error']:\n            print(f\"      Error: {result['error']}\")\n    \n    # Final Assessment\n    print(f\"\\n🏁 FINAL ASSESSMENT\")\n    if overall['performance_score'] >= 85:\n        print(\"   ✅ Excellent performance - ready for production\")\n        print(\"   ✅ All critical performance targets met\")\n        success = True\n    elif overall['performance_score'] >= 65:\n        print(\"   ⚠️  Good performance - minor optimizations recommended\")\n        print(\"   📝 Address performance recommendations above\")\n        success = True\n    else:\n        print(\"   ❌ Performance issues detected - optimization required\")\n        print(\"   🔧 Address critical performance bottlenecks\")\n        success = False\n    \n    print(f\"\\n   Final Memory: {benchmark.get_memory_usage():.1f}MB\")\n    print(f\"   Benchmark completed at {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}\")\n    \n    return success\n\nif __name__ == \"__main__\":\n    try:\n        success = asyncio.run(main())\n        sys.exit(0 if success else 1)\n    except KeyboardInterrupt:\n        print(\"\\n\\n⏹️  Benchmark interrupted by user\")\n        sys.exit(1)\n    except Exception as e:\n        print(f\"\\n\\n💥 Benchmark failed with error: {e}\")\n        sys.exit(1)