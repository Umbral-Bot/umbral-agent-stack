class AlertManager:
    def __init__(self):
        self._alerts = []
        self._total_alerts = 0
        self._active_alerts = 0

    def add_alert(self, alert):
        self._alerts.append({
            "alert": alert,
            "resolved": False,
        })
        self._total_alerts += 1
        self._active_alerts += 1

    def resolve_alert(self, alert):
        for item in self._alerts:
            if item["alert"] == alert and not item["resolved"]:
                item["resolved"] = True
                self._active_alerts -= 1
                return True
        return False

    def get_alerts(self):
        return [item["alert"] for item in self._alerts]

    def summary(self):
        return {
            "total_alerts": self._total_alerts,
            "active_alerts": self._active_alerts,
        }
