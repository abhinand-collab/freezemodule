# pyrefly: ignore [missing-import]
from celery import shared_task
from core.models.freeze_models import Freeze
from core.services.freeze_service import get_target_subscriptions, apply_freeze_to_subscription

@shared_task(bind=True)
def process_bulk_freeze(self, freeze_id):
    try:
        freeze = Freeze.objects.get(id=freeze_id)
    except Freeze.DoesNotExist:
        return f"Freeze {freeze_id} not found"

    freeze.status = 'processing'
    freeze.task_id = self.request.id
    freeze.save()

    try:
        # 1. Identify target members
        subscriptions = get_target_subscriptions(freeze)
        freeze.total_members = subscriptions.count()
        freeze.save()

        success_count = 0
        fail_count = 0
        error_logs = ""

        # 2. Process subscriptions
        for sub in subscriptions:
            try:
                # Check if already processed for THIS freeze
                if freeze.logs.filter(member_subscription=sub, status="success").exists():
                    success_count += 1
                    continue

                apply_freeze_to_subscription(freeze, sub)
                success_count += 1
            except Exception as e:
                fail_count += 1
                error_logs += f"Subscription {sub.id} (Member: {sub.member.full_name}): {str(e)}\n"
                freeze.error_logs = error_logs
                
                # Log failure to FreezeLog
                try:
                    from core.models.freeze_models import FreezeLog
                    from django.utils import timezone
                    old_end = sub.effective_end_date or sub.original_end_date
                    FreezeLog.objects.create(
                        freeze=freeze,
                        member_subscription=sub,
                        old_end_date=old_end,
                        new_end_date=None,
                        freeze_days=(freeze.end_date - freeze.start_date).days + 1,
                        status="failed",
                        error_message=str(e),
                        processed_at=timezone.now()
                    )
                except Exception:
                    pass
            
            # 3. Update progress
            freeze.processed_members = success_count + fail_count
            freeze.save()

        # Update error logs if any occurred
        if error_logs:
            freeze.error_logs = error_logs
            freeze.save()

        # 4. Final Status
        if fail_count == 0:
            freeze.status = 'completed'
        elif success_count > 0:
            freeze.status = 'partial_failed'
        else:
            freeze.status = 'failed'
        freeze.save()

        return f"Freeze {freeze_id} finished: {success_count} succeeded, {fail_count} failed"

    except (Exception, BaseException) as exc:
        # Check if we have processed any members successfully before the crash/stop
        if 'success_count' in locals() and success_count > 0:
            freeze.status = 'partial_failed'
        else:
            freeze.status = 'failed'
            
        freeze.error_logs = f"System Error / Interruption during Celery task: {str(exc)}"
        freeze.save()
        raise exc
