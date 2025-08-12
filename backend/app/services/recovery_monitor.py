"""
Recovery Monitor Service - Monitors task recovery system health and performance
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from app.core.auth_context import AuthContext
from app.clients.factory import get_service_supabase_client
from app.services.repositories.recovery_repository import RecoveryRepository
from app.core.task_recovery import TaskState
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class RecoveryMonitor:
    """Monitors task recovery system health and metrics"""

    def __init__(self):
        self.settings = get_settings()
        self.monitoring_active = False
        self.monitoring_task = None

    async def start_monitoring(self):
        """Start background monitoring"""
        if self.monitoring_active:
            return

        self.monitoring_active = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Recovery monitoring started")

    async def stop_monitoring(self):
        """Stop background monitoring"""
        self.monitoring_active = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Recovery monitoring stopped")

    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Check system health every 5 minutes
                await self._check_recovery_health()
                await asyncio.sleep(300)  # 5 minutes

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Recovery monitoring error: {e}")
                await asyncio.sleep(60)  # Retry after 1 minute on error

    async def _check_recovery_health(self):
        """Check recovery system health"""
        try:
            health_status = await self.get_recovery_health_status()

            # Log metrics
            logger.info(f"Recovery Health: {health_status}")

            # Check for alerts
            await self._check_alerts(health_status)

        except Exception as e:
            logger.error(f"Failed to check recovery health: {e}")

    async def get_recovery_health_status(self) -> Dict[str, Any]:
        """Get current recovery system health status"""
        try:
            repo = RecoveryRepository()

            # Check recovery queue depth
            queue_depth = await repo.count_recovery_queue_pending()

            # Check recent failures
            one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
            recent_failures = await repo.count_recovery_queue_failed_since(one_hour_ago)

            # Check orphaned tasks
            ten_minutes_ago = (
                datetime.now(timezone.utc) - timedelta(minutes=10)
            ).isoformat()
            orphaned_count = await repo.count_task_registry_orphaned_before(
                ten_minutes_ago
            )

            # Check stuck tasks
            stuck_count = await repo.count_task_registry_stuck_before(ten_minutes_ago)

            # Determine overall health
            health_status = "healthy"
            if queue_depth > 20 or recent_failures > 5 or stuck_count > 3:
                health_status = "degraded"
            if queue_depth > 50 or recent_failures > 15 or orphaned_count > 10:
                health_status = "critical"

            return {
                "overall_health": health_status,
                "recovery_queue_depth": queue_depth,
                "recent_failure_count": recent_failures,
                "orphaned_task_count": orphaned_count,
                "stuck_task_count": stuck_count,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get recovery health status: {e}")
            return {
                "overall_health": "unknown",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    async def _check_alerts(self, health_status: Dict[str, Any]):
        """Check for alert conditions"""
        health = health_status.get("overall_health", "unknown")

        if health == "critical":
            await self._send_alert(
                "critical_recovery_health",
                f"Recovery system in critical state: {health_status}",
                "critical",
            )
        elif health == "degraded":
            await self._send_alert(
                "degraded_recovery_health",
                f"Recovery system degraded: {health_status}",
                "warning",
            )

        # Specific alerts
        queue_depth = health_status.get("recovery_queue_depth", 0)
        if queue_depth > 30:
            await self._send_alert(
                "high_recovery_queue_depth",
                f"Recovery queue depth: {queue_depth} (threshold: 30)",
                "warning",
            )

        stuck_tasks = health_status.get("stuck_task_count", 0)
        if stuck_tasks > 5:
            await self._send_alert(
                "stuck_recovery_tasks",
                f"Found {stuck_tasks} stuck recovery tasks",
                "critical",
            )

    async def _send_alert(self, alert_type: str, message: str, severity: str):
        """Send alert (placeholder - integrate with your alerting system)"""
        logger.warning(f"RECOVERY ALERT [{severity.upper()}] {alert_type}: {message}")

        # In production, integrate with:
        # - Slack notifications
        # - Email alerts
        # - PagerDuty
        # - Discord webhooks
        # etc.

    async def get_recovery_metrics(self) -> Dict[str, Any]:
        """Get detailed recovery metrics"""
        try:
            # Task state distribution
            state_distribution = {}
            for state in TaskState:
                repo = RecoveryRepository()
                # Reuse orphaned/stuck helpers where applicable, fallback to generic count
                if state == TaskState.ORPHANED:
                    ten_years_ago = (
                        datetime.now(timezone.utc) - timedelta(days=3650)
                    ).isoformat()
                    state_distribution[state.value] = (
                        await repo.count_task_registry_orphaned_before(ten_years_ago)
                    )
                elif state in (TaskState.PROCESSING, TaskState.RECOVERING):
                    ten_years_ago = (
                        datetime.now(timezone.utc) - timedelta(days=3650)
                    ).isoformat()
                    state_distribution[state.value] = (
                        await repo.count_task_registry_stuck_before(ten_years_ago)
                    )
                else:
                    # Generic count using raw SQL
                    from app.database.connection import fetchrow_raw_sql

                    row = await fetchrow_raw_sql(
                        "SELECT COUNT(*) AS c FROM task_registry WHERE current_state = $1",
                        state.value,
                    )
                    state_distribution[state.value] = int(row["c"]) if row else 0

            # Recovery success rates (last 24 hours)
            twenty_four_hours_ago = (
                datetime.now(timezone.utc) - timedelta(hours=24)
            ).isoformat()

            repo = RecoveryRepository()
            total_attempts = await repo.count_recovery_queue_since(
                twenty_four_hours_ago
            )
            successful_attempts = await repo.count_recovery_queue_completed_since(
                twenty_four_hours_ago
            )

            success_rate = (
                (successful_attempts / total_attempts * 100)
                if total_attempts > 0
                else 0
            )

            # Average recovery time
            avg_recovery_time = await self._calculate_average_recovery_time()

            return {
                "task_state_distribution": state_distribution,
                "recovery_success_rate_24h": round(success_rate, 2),
                "total_recovery_attempts_24h": total_attempts,
                "successful_recoveries_24h": successful_attempts,
                "average_recovery_time_seconds": avg_recovery_time,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get recovery metrics: {e}")
            return {"error": str(e)}

    async def _calculate_average_recovery_time(self) -> float:
        """Calculate average recovery time"""
        try:
            twenty_four_hours_ago = (
                datetime.now(timezone.utc) - timedelta(hours=24)
            ).isoformat()
            repo = RecoveryRepository()
            rows = await repo.fetch_completed_recoveries_with_timings_since(
                twenty_four_hours_ago
            )

            if not rows:
                return 0.0

            total_time = 0
            count = 0

            for row in rows:
                started = datetime.fromisoformat(
                    row["processing_started"].replace("Z", "+00:00")
                )
                completed = datetime.fromisoformat(
                    row["processing_completed"].replace("Z", "+00:00")
                )
                duration = (completed - started).total_seconds()
                total_time += duration
                count += 1

            return total_time / count if count > 0 else 0.0

        except Exception as e:
            logger.error(f"Failed to calculate average recovery time: {e}")
            return 0.0

    async def cleanup_old_records(self, days_to_keep: int = 30):
        """Clean up old recovery records"""
        try:
            repo = RecoveryRepository()
            cutoff_date = (
                datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            ).isoformat()

            # Clean up old completed task registry entries
            _ = await repo.delete_old_task_registry_completed_before(cutoff_date)

            # Clean up old recovery queue entries
            _ = await repo.delete_old_recovery_queue_before(cutoff_date)

            # Clean up old checkpoints for completed tasks
            await repo.cleanup_old_checkpoints(cutoff_date)

            logger.info(
                f"Cleanup completed: removed old recovery records older than {days_to_keep} days"
            )

        except Exception as e:
            logger.error(f"Failed to cleanup old recovery records: {e}")


# Global monitor instance
recovery_monitor = RecoveryMonitor()
