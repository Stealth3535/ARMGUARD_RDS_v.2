from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Core"

    def ready(self) -> None:  # noqa: D401
        # Import device models so Django registers them for migrations
        import core.device.models  # noqa: F401
