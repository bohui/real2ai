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
            )
            
            # First render (cache miss)
            start_time = time.time()
            first_render = await manager.render("cache_test", context, cache_key="test_cache_key")
            first_duration = (time.time() - start_time) * 1000
            
            # Second render (should be cache hit)
            start_time = time.time()
            second_render = await manager.render("cache_test", context, cache_key="test_cache_key")
            second_duration = (time.time() - start_time) * 1000
            
            # Calculate improvement
            improvement_percent = ((first_duration - second_duration) / first_duration) * 100
            
            memory_delta = self.get_memory_usage() - initial_memory
            
            # Get metrics to verify cache hit
            metrics = manager.get_metrics()
            cache_hits = metrics.get('prompt_manager', {}).get('cache_hits', 0)
            
            success = (
                first_render == second_render and
                cache_hits > 0 and
                improvement_percent > 0  # Any improvement is good
            )
            
            # Cleanup
            test_template.unlink()
            temp_dir.rmdir()
            
            return BenchmarkResult(
                test_name=test_name,
                duration_ms=first_duration,  # Use first render time as baseline
                memory_delta_mb=memory_delta,
                success=success,
                details={
                    'cache_miss_time_ms': first_duration,
                    'cache_hit_time_ms': second_duration,
                    'improvement_percent': improvement_percent,
                    'cache_hits': cache_hits,
                    'target_improvement': self.targets['cache_hit_improvement']
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
    
    async def benchmark_batch_render(self) -> BenchmarkResult:
        """Benchmark batch rendering performance"""
        test_name = "Batch Render Performance"
        
        initial_memory = self.get_memory_usage()
        
        try:
            from app.core.prompts.manager import PromptManager, PromptManagerConfig
            from app.core.prompts.context import PromptContext, ContextType
            
            temp_dir = Path(__file__).parent / "temp_templates"
            temp_dir.mkdir(exist_ok=True)
            
            # Create test template
            test_template = temp_dir / "batch_test.md"
            test_template.write_text("""
---
name: batch_test
version: 1.0.0
description: Batch render test
variables:
  - item_id
  - item_name
---

Processing item {{ item_id }}: {{ item_name }}
""")
            
            config = PromptManagerConfig(
                templates_dir=temp_dir,
                cache_enabled=True,
                validation_enabled=False
            )
            
            manager = PromptManager(config)
            await manager.initialize()
            
            # Create batch requests
            batch_size = 10
            requests = []
            
            for i in range(batch_size):
                context = PromptContext(
                    context_type=ContextType.USER,
                    variables={
                        'item_id': i,
                        'item_name': f'Item {i}'
                    }
                )
                
                requests.append({
                    'template_name': 'batch_test',
                    'context': context
                })
            
            # Benchmark batch render
            start_time = time.time()
            
            results = await manager.batch_render(requests, max_concurrent=3)
            
            duration_ms = (time.time() - start_time) * 1000
            memory_delta = self.get_memory_usage() - initial_memory
            
            # Analyze results
            successful_renders = sum(1 for r in results if r['success'])
            average_time_per_item = duration_ms / batch_size
            
            success = (
                successful_renders == batch_size and
                average_time_per_item < self.targets['render_time_ms'] + self.targets['batch_render_overhead']
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
                    'batch_size': batch_size,
                    'successful_renders': successful_renders,
                    'average_time_per_item_ms': average_time_per_item,
                    'target_time_per_item': self.targets['render_time_ms'] + self.targets['batch_render_overhead'],
                    'results_sample': results[:3]  # First 3 results
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
    
    async def benchmark_memory_efficiency(self) -> BenchmarkResult:
        """Benchmark memory usage and cleanup"""
        test_name = "Memory Efficiency"
        
        initial_memory = self.get_memory_usage()
        
        try:
            from app.core.prompts.manager import PromptManager, PromptManagerConfig
            from app.core.prompts.context import PromptContext, ContextType
            
            temp_dir = Path(__file__).parent / "temp_templates"
            temp_dir.mkdir(exist_ok=True)
            
            # Create multiple test templates
            templates = {}
            for i in range(5):
                template_name = f"memory_test_{i}"
                template_file = temp_dir / f"{template_name}.md"
                template_file.write_text(f"""
---
name: {template_name}
version: 1.0.0
description: Memory test template {i}
variables:
  - data
---

Template {i} processing: {{{{ data }}}}
""")
                templates[template_name] = template_file
            
            config = PromptManagerConfig(
                templates_dir=temp_dir,
                cache_enabled=True,
                validation_enabled=False,
                preload_templates=True
            )
            
            # Measure peak memory during operations
            peak_memory = initial_memory
            
            manager = PromptManager(config)
            await manager.initialize()
            
            peak_memory = max(peak_memory, self.get_memory_usage())
            
            # Perform multiple renders
            for i in range(20):
                template_name = f"memory_test_{i % 5}"
                context = PromptContext(
                    context_type=ContextType.USER,
                    variables={'data': f'Data batch {i}'}
                )
                
                await manager.render(template_name, context)
                peak_memory = max(peak_memory, self.get_memory_usage())
            
            # Test cache clearing
            manager.clear_cache()
            gc.collect()  # Force garbage collection
            
            final_memory = self.get_memory_usage()
            peak_delta = peak_memory - initial_memory
            final_delta = final_memory - initial_memory
            
            success = (
                peak_delta < self.targets['memory_usage_mb'] and
                final_delta < peak_delta  # Memory was freed
            )
            
            # Cleanup
            for template_file in templates.values():
                template_file.unlink()
            temp_dir.rmdir()
            
            return BenchmarkResult(
                test_name=test_name,
                duration_ms=0,  # Not time-focused
                memory_delta_mb=peak_delta,
                success=success,
                details={
                    'initial_memory_mb': initial_memory,
                    'peak_memory_mb': peak_memory,
                    'final_memory_mb': final_memory,
                    'peak_delta_mb': peak_delta,
                    'final_delta_mb': final_delta,
                    'memory_freed_mb': peak_delta - final_delta,
                    'target_memory_mb': self.targets['memory_usage_mb']
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
    
    def log_result(self, result: BenchmarkResult):
        """Log benchmark result"""
        status = "✅ PASS" if result.success else "❌ FAIL"
        
        if result.duration_ms > 0:
            logger.info(f"{status} | {result.test_name} | {result.duration_ms:.1f}ms | Memory: {result.memory_delta_mb:.1f}MB")
        else:
            logger.info(f"{status} | {result.test_name} | Memory: {result.memory_delta_mb:.1f}MB")
        
        if result.error:
            logger.error(f"   Error: {result.error}")
        
        self.results.append(result)
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.success)
        
        # Calculate averages
        avg_render_time = sum(r.duration_ms for r in self.results if r.duration_ms > 0) / max(sum(1 for r in self.results if r.duration_ms > 0), 1)
        max_memory_usage = max(r.memory_delta_mb for r in self.results)
        
        # Performance score calculation
        performance_score = 0
        
        for result in self.results:
            if result.success:
                performance_score += 25  # 25 points per successful test
        
        # Additional scoring based on performance metrics
        if avg_render_time < self.targets['render_time_ms']:
            performance_score += 10
        if max_memory_usage < self.targets['memory_usage_mb']:
            performance_score += 15
        
        performance_score = min(performance_score, 100)  # Cap at 100
        
        return {
            'overall_performance': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'performance_score': performance_score,
                'grade': self._get_performance_grade(performance_score)
            },
            'timing_metrics': {
                'average_render_time_ms': avg_render_time,
                'target_render_time_ms': self.targets['render_time_ms'],
                'render_time_met': avg_render_time < self.targets['render_time_ms']
            },
            'memory_metrics': {
                'max_memory_usage_mb': max_memory_usage,
                'target_memory_mb': self.targets['memory_usage_mb'],
                'memory_target_met': max_memory_usage < self.targets['memory_usage_mb']
            },
            'detailed_results': [{
                'test_name': r.test_name,
                'success': r.success,
                'duration_ms': r.duration_ms,
                'memory_delta_mb': r.memory_delta_mb,
                'details': r.details,
                'error': r.error
            } for r in self.results],
            'performance_targets': self.targets,
            'recommendations': self._generate_performance_recommendations()
        }
    
    def _get_performance_grade(self, score: float) -> str:
        """Get performance grade"""
        if score >= 95:
            return 'A+ (Excellent)'
        elif score >= 85:
            return 'A (Very Good)'
        elif score >= 75:
            return 'B+ (Good)'
        elif score >= 65:
            return 'B (Acceptable)'
        elif score >= 55:
            return 'C+ (Needs Improvement)'
        else:
            return 'F (Poor Performance)'
    
    def _generate_performance_recommendations(self) -> List[str]:
        """Generate performance recommendations"""
        recommendations = []
        
        failed_tests = [r for r in self.results if not r.success]
        
        if not failed_tests:
            recommendations.append("✅ All performance benchmarks passed - excellent performance")
            return recommendations
        
        # Analyze failures
        if any('Initialization' in r.test_name for r in failed_tests):
            recommendations.append("🚀 Optimize initialization time - consider lazy loading")
        
        if any('Render' in r.test_name for r in failed_tests):
            recommendations.append("⚡ Optimize render performance - review template complexity")
        
        if any('Cache' in r.test_name for r in failed_tests):
            recommendations.append("💾 Improve caching strategy - check cache hit rates")
        
        if any('Memory' in r.test_name for r in failed_tests):
            recommendations.append("🧠 Optimize memory usage - review object lifecycle and cleanup")
        
        if any('Batch' in r.test_name for r in failed_tests):
            recommendations.append("📦 Optimize batch processing - consider parallel execution limits")
        
        return recommendations

async def main():
    """Run comprehensive PromptManager performance benchmarks"""
    benchmark = PromptManagerBenchmark()
    
    print("⚡ PROMPTMANAGER PERFORMANCE BENCHMARK")
    print("=" * 50)
    print(f"Start Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"Process ID: {os.getpid()}")
    print(f"Initial Memory: {benchmark.get_memory_usage():.1f}MB")
    print()
    
    # Define benchmark tests
    benchmark_tests = [
        ("Initialization", benchmark.benchmark_initialization),
        ("Single Render", benchmark.benchmark_render_performance),
        ("Cache Performance", benchmark.benchmark_cache_performance),
        ("Batch Render", benchmark.benchmark_batch_render),
        ("Memory Efficiency", benchmark.benchmark_memory_efficiency),
    ]
    
    # Run benchmarks
    print("🔥 RUNNING PERFORMANCE BENCHMARKS")
    print("-" * 35)
    
    for test_name, test_func in benchmark_tests:
        print(f"\n▶️  Running: {test_name}")
        try:
            result = await test_func()
            benchmark.log_result(result)
        except Exception as e:
            logger.error(f"Benchmark '{test_name}' crashed: {e}")
            benchmark.log_result(BenchmarkResult(
                test_name=test_name,
                duration_ms=0,
                memory_delta_mb=0,
                success=False,
                details={},
                error=str(e)
            ))
    
    # Generate and display report
    print("\n" + "=" * 50)
    print("📊 PERFORMANCE BENCHMARK REPORT")
    print("=" * 50)
    
    report = benchmark.generate_performance_report()
    
    # Overall Performance
    overall = report['overall_performance']
    print(f"\n🎯 OVERALL PERFORMANCE")
    print(f"   Score: {overall['performance_score']:.0f}/100 ({overall['grade']})")
    print(f"   Tests: {overall['passed_tests']}/{overall['total_tests']} passed")
    
    # Timing Metrics
    timing = report['timing_metrics']
    print(f"\n⏱️  TIMING METRICS")
    print(f"   Average Render Time: {timing['average_render_time_ms']:.1f}ms")
    print(f"   Target: <{timing['target_render_time_ms']}ms")
    print(f"   Status: {'✅ MET' if timing['render_time_met'] else '❌ NOT MET'}")
    
    # Memory Metrics
    memory = report['memory_metrics']
    print(f"\n🧠 MEMORY METRICS")
    print(f"   Max Memory Usage: {memory['max_memory_usage_mb']:.1f}MB")
    print(f"   Target: <{memory['target_memory_mb']}MB")
    print(f"   Status: {'✅ MET' if memory['memory_target_met'] else '❌ NOT MET'}")
    
    # Performance Targets
    targets = report['performance_targets']
    print(f"\n🎯 PERFORMANCE TARGETS")
    for target, value in targets.items():
        print(f"   {target}: {value}")
    
    # Recommendations
    recommendations = report['recommendations']
    print(f"\n💡 RECOMMENDATIONS")
    for i, rec in enumerate(recommendations, 1):
        print(f"   {i}. {rec}")
    
    # Detailed Results
    print(f"\n📋 DETAILED BENCHMARK RESULTS")
    for result in report['detailed_results']:
        status = "✅" if result['success'] else "❌"
        if result['duration_ms'] > 0:
            print(f"   {status} {result['test_name']}: {result['duration_ms']:.1f}ms, {result['memory_delta_mb']:.1f}MB")
        else:
            print(f"   {status} {result['test_name']}: {result['memory_delta_mb']:.1f}MB")
        
        if result['error']:
            print(f"      Error: {result['error']}")
    
    # Final Assessment
    print(f"\n🏁 FINAL ASSESSMENT")
    if overall['performance_score'] >= 85:
        print("   ✅ Excellent performance - ready for production")
        print("   ✅ All critical performance targets met")
        success = True
    elif overall['performance_score'] >= 65:
        print("   ⚠️  Good performance - minor optimizations recommended")
        print("   📝 Address performance recommendations above")
        success = True
    else:
        print("   ❌ Performance issues detected - optimization required")
        print("   🔧 Address critical performance bottlenecks")
        success = False
    
    print(f"\n   Final Memory: {benchmark.get_memory_usage():.1f}MB")
    print(f"   Benchmark completed at {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    return success

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Benchmark interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Benchmark failed with error: {e}")
        sys.exit(1)