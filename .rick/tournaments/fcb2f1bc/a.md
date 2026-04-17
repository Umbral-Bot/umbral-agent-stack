---
tournament_id: "fcb2f1bc"
contestant_label: "a"
approach_id: 1
approach_name: "Internal State Aggregation"
model_used: "gpt-5.4"
created_at: "2026-04-17T12:23:22+00:00"
---

# Contestant A — Internal State Aggregation

## Challenge

Refactor the AlertManager class to add a method called `summary()` that returns a dict with keys `total_alerts` (int, count of all alerts ever added) and `active_alerts` (int, count of alerts not yet resolved). The method must work correctly even if no alerts have been added. Do not remove or rename any existing methods.

## Proposal

Below is a refactor of `AlertManager` that adds internal state aggregation so `summary()` is constant-time and always correct, including when no alerts have been added.

```python
class AlertManager:
    def __init__(self):
        self._alerts = []
        self._total_alerts = 0
        self._active_alerts = 0

    def add_alert(self, alert):
        self._alerts.append({
            "alert": alert,
            "resolved": False
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
```

### What changed
- Added two internal counters in `__init__`:
  - `_total_alerts`: tracks every alert ever added
  - `_active_alerts`: tracks alerts not yet resolved
- Updated `add_alert()` to increment both counters.
- Updated `resolve_alert()` to decrement `_active_alerts` only when an unresolved matching alert is actually resolved.
- Added `summary()` to return the required dict.

### Behavior
```python
am = AlertManager()
print(am.summary())
# {'total_alerts': 0, 'active_alerts': 0}

am.add_alert("CPU high")
am.add_alert("Disk low")
print(am.summary())
# {'total_alerts': 2, 'active_alerts': 2}

am.resolve_alert("CPU high")
print(am.summary())
# {'total_alerts': 2, 'active_alerts': 1}
```

### Expected outcomes
- Correct when no alerts exist.
- `summary()` is fast because it reads maintained state instead of recalculating from the list.
- Existing methods remain intact and unrenamed.
