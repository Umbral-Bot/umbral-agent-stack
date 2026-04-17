class AlertManager:
    def __init__(self):
        self._alerts = []

    def add_alert(self, alert):
        self._alerts.append(alert)

    def resolve_alert(self, alert):
        if alert in self._alerts:
            alert.resolved = True

    def get_alerts(self):
        return self._alerts

    def summary(self):
        total_alerts = len(self._alerts)
        active_alerts = sum(
            1 for alert in self._alerts if not getattr(alert, "resolved", False)
        )
        return {
            "total_alerts": total_alerts,
            "active_alerts": active_alerts,
        }
