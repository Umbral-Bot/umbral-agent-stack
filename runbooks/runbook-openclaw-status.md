# Runbook: Estado de OpenClaw

## Verificar servicio

```bash
systemctl --user status openclaw
```

## Estado detallado

```bash
openclaw status --all
```

## Estado de modelos

```bash
openclaw models status
```

## Logs recientes

```bash
journalctl --user -u openclaw -n 50 --no-pager
```

## Logs en vivo

```bash
journalctl --user -u openclaw -f
```

## Si está caído → reiniciar

```bash
systemctl --user restart openclaw
systemctl --user status openclaw
```

## Verificar puertos

```bash
ss -lntp | grep -E '18789|18791'
```
