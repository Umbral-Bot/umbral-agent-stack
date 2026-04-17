---
tournament_id: "fcb2f1bc"
contestant_label: "c"
approach_id: 3
approach_name: "Abstraction via Alert Status Querying"
model_used: "gpt-5.4"
created_at: "2026-04-17T12:23:42+00:00"
---

# Contestant C — Abstraction via Alert Status Querying

## Challenge

Refactor the AlertManager class to add a method called `summary()` that returns a dict with keys `total_alerts` (int, count of all alerts ever added) and `active_alerts` (int, count of alerts not yet resolved). The method must work correctly even if no alerts have been added. Do not remove or rename any existing methods.

## Proposal

Here is a focused refactor proposal for the `AlertManager` class using **alert status querying via abstraction**: add a `summary()` method that derives counts from the manager’s current alert collection, without changing or removing any existing methods.

## Refactored `AlertManager`

```python
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
        active_alerts = sum(1 for alert in self._alerts if not getattr(alert, "resolved", False))
        return {
            "total_alerts": total_alerts,
            "active_alerts": active_alerts,
        }
```

## Why this works

The new `summary()` method queries the current state of stored alerts and computes:

- `total_alerts`: total number of alerts ever added, using `len(self._alerts)`
- `active_alerts`: number of alerts not resolved yet

It also works correctly when no alerts have been added:

```python
manager = AlertManager()
print(manager.summary())
# {'total_alerts': 0, 'active_alerts': 0}
```

## Key implementation detail

To make the method robust, `active_alerts` uses:

```python
getattr(alert, "resolved", False)
```

This means:

- if an alert has `resolved = True`, it is not active
- if an alert has `resolved = False`, it is active
- if an alert has no `resolved` attribute yet, it is treated as unresolved/active

That keeps the method safe and compatible with existing alert objects.

## Expected outcome

After this refactor:

- existing methods remain unchanged
- `summary()` can be called at any time
- counts stay accurate based on alert status
- empty manager case is handled naturally

## Example

```python
class Alert:
    def __init__(self, message):
        self.message = message
        self.resolved = False

manager = AlertManager()

a1 = Alert("CPU high")
a2 = Alert("Disk full")

manager.add_alert(a1)
manager.add_alert(a2)

print(manager.summary())
# {'total_alerts': 2, 'active_alerts': 2}

manager.resolve_alert(a1)

print(manager.summary())
# {'total_alerts': 2, 'active_alerts': 1}
```

If you want, I can also adapt this directly to your existing `AlertManager` code snippet.
