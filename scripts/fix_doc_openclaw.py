# One-off: fix duplicate line and simplify paragraph in docs/openclaw-rick-skill-y-modelos.md
import pathlib

p = pathlib.Path("docs/openclaw-rick-skill-y-modelos.md")
text = p.read_text(encoding="utf-8")

# Remove duplicate line: the standalone line that repeats "No hace falta reiniciar... lo tendrá disponible"
lines = text.splitlines()
new_lines = []
for line in lines:
    stripped = line.strip()
    # Skip line that is only that duplicate sentence (with or without unicode quotes)
    if stripped and "No hace falta reiniciar el gateway para que el skill exista" in stripped and "lo tendrá disponible" in stripped and "configurar agentes" in stripped:
        if len(stripped) < 200:  # the duplicate is a single line, not the long paragraph
            continue  # skip this duplicate line
    new_lines.append(line)
text = "\n".join(new_lines)

# Simplify the long paragraph: replace the verbose one with the shorter version
old_p = "Tras eso, OpenClaw cargará el skill desde `<workspace>/skills`. *(`sync_skills_to_vps.py` está pensado para ejecutarse desde tu PC y copiar por SCP; si estás ya en la VPS, usa esta Opción B.)* (prioridad sobre managed/bundled). No hace falta reiniciar el gateway para que el skill exista; el próximo turno que necesite configurar agentes/sesiones/workspace lo tendrá disponible."
new_p = "Tras eso, OpenClaw cargará el skill desde `<workspace>/skills` (prioridad sobre managed/bundled). No hace falta reiniciar el gateway; el próximo turno que necesite configurar agentes/sesiones/workspace lo tendrá disponible."
if old_p in text:
    text = text.replace(old_p, new_p, 1)

p.write_text(text, encoding="utf-8")
print("Done.")
