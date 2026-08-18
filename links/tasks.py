from celery import shared_task


@shared_task
def record_click(code: str, referrer: str = "", user_agent: str = ""):
    """Persist a click off the request path so redirects stay fast."""
    from .models import Click, Link

    try:
        link = Link.objects.get(code=code)
    except Link.DoesNotExist:
        return
    Click.objects.create(
        link=link,
        referrer=(referrer or "")[:500],
        user_agent=(user_agent or "")[:500],
    )
