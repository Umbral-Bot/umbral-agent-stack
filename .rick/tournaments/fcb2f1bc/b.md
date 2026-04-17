---
tournament_id: "fcb2f1bc"
contestant_label: "b"
approach_id: 2
approach_name: "Incremental Counter Tracking"
model_used: "gpt-5.4"
created_at: "2026-04-17T12:23:32+00:00"
---

# Contestant B — Incremental Counter Tracking

## Challenge

Refactor the AlertManager class to add a method called `summary()` that returns a dict with keys `total_alerts` (int, count of all alerts ever added) and `active_alerts` (int, count of alerts not yet resolved). The method must work correctly even if no alerts have been added. Do not remove or rename any existing methods.

## Proposal

```python
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
```

### What changed
- Added incremental counters:
  - `self._total_alerts` tracks every alert ever added
  - `self._active_alerts` tracks currently unresolved alerts
- Updated:
  - `add_alert()` to increment both counters
  - `resolve_alert()` to decrement only active alerts when an alert is actually resolved
- Added:
  - `summary()` returning the required dict

### Behavior
- If no alerts have been added yet, `summary()` returns:
```python
{"total_alerts": 0, "active_alerts": 0}
```

### Expected outcome
- `summary()` runs in constant time
- Counts stay accurate as alerts are added and resolved
- Existing method names remain unchanged
