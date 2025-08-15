import time
import psutil
import gc
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from PySide6.QtCore import QObject, Signal, QTimer
from contextlib import contextmanager


@dataclass
class PerformanceMetrics:
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    memory_percent: float = 0.0
    operation_time: float = 0.0
    operation_name: str = ""


class PerformanceMonitor(QObject):
    """Monitor application performance and resource usage"""

    metrics_updated = Signal(object)  # PerformanceMetrics
    memory_warning = Signal(float)  # memory_mb

    def __init__(self, warning_threshold_mb: int = 1024):
        super().__init__()
        self.warning_threshold_mb = warning_threshold_mb
        self.metrics_history: List[PerformanceMetrics] = []
        self.max_history = 100

        # Start monitoring timer
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._collect_metrics)
        self.monitor_timer.start(5000)  # Every 5 seconds

    def _collect_metrics(self):
        """Collect current performance metrics"""
        try:
            process = psutil.Process()

            metrics = PerformanceMetrics(
                cpu_percent=process.cpu_percent(),
                memory_mb=process.memory_info().rss / 1024 / 1024,
                memory_percent=process.memory_percent()
            )

            # Add to history
            self.metrics_history.append(metrics)
            if len(self.metrics_history) > self.max_history:
                self.metrics_history.pop(0)

            # Emit signals
            self.metrics_updated.emit(metrics)

            if metrics.memory_mb > self.warning_threshold_mb:
                self.memory_warning.emit(metrics.memory_mb)

        except Exception as e:
            print(f"Error collecting performance metrics: {e}")

    @contextmanager
    def measure_operation(self, operation_name: str):
        """Context manager to measure operation performance"""
        start_time = time.perf_counter()
        try:
            yield
        finally:
            end_time = time.perf_counter()
            operation_time = end_time - start_time

            metrics = PerformanceMetrics(
                operation_time=operation_time,
                operation_name=operation_name
            )
            self.metrics_updated.emit(metrics)

    def get_average_memory_usage(self) -> float:
        """Get average memory usage from recent history"""
        if not self.metrics_history:
            return 0.0

        return sum(m.memory_mb for m in self.metrics_history) / len(self.metrics_history)

    def force_garbage_collection(self):
        """Force garbage collection and return freed memory"""
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024

        gc.collect()

        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        freed_memory = initial_memory - final_memory

        return max(0, freed_memory)


class MemoryOptimizer:
    """Optimize memory usage throughout the application"""

    def __init__(self, performance_monitor: PerformanceMonitor):
        self.performance_monitor = performance_monitor
        self.image_cache = {}
        self.thumbnail_cache = {}
        self.cache_limits = {
            'images': 50,  # Maximum cached images
            'thumbnails': 200  # Maximum cached thumbnails
        }

    def cache_image(self, image_id: str, image_data, cache_type: str = 'images'):
        """Cache image data with memory management"""
        cache = self.image_cache if cache_type == 'images' else self.thumbnail_cache
        limit = self.cache_limits[cache_type]

        # Remove oldest entries if at limit
        if len(cache) >= limit:
            oldest_key = next(iter(cache))
            del cache[oldest_key]

        cache[image_id] = {
            'data': image_data,
            'timestamp': time.time()
        }

    def get_cached_image(self, image_id: str, cache_type: str = 'images'):
        """Get cached image data"""
        cache = self.image_cache if cache_type == 'images' else self.thumbnail_cache
        cached_item = cache.get(image_id)

        if cached_item:
            # Update timestamp for LRU
            cached_item['timestamp'] = time.time()
            return cached_item['data']

        return None

    def clear_cache(self, cache_type: Optional[str] = None):
        """Clear image caches"""
        if cache_type == 'images' or cache_type is None:
            self.image_cache.clear()
        if cache_type == 'thumbnails' or cache_type is None:
            self.thumbnail_cache.clear()

        # Force garbage collection
        self.performance_monitor.force_garbage_collection()

    def optimize_memory_usage(self, current_memory_mb: float, target_memory_mb: float):
        """Optimize memory usage to reach target"""
        if current_memory_mb <= target_memory_mb:
            return

        # Clear thumbnail cache first
        self.clear_cache('thumbnails')

        # If still over target, clear image cache
        current_memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
        if current_memory_mb > target_memory_mb:
            self.clear_cache('images')

        # Force garbage collection
        self.performance_monitor.force_garbage_collection()
