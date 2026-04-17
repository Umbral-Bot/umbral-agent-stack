class AlertManager:
    def __init__(self):
        self.alerts = []
        self._total_alerts = 0
        self._active_alerts = 0

    def add_alert(self, alert):
        self.alerts.append(alert)
        self._total_alerts += 1
        self._active_alerts += 1

    def resolve_alert(self, alert):
        if alert in self.alerts:
            self.alerts.remove(alert)
            self._active_alerts -= 1

    def summary(self):
        return {
            "total_alerts": self._total_alerts,
            "active_alerts": self._active_alerts,
        }
