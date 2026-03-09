# Patrones de workflow recomendados

## 1. Barrido programado de fuentes de autoridad
Flujo:
`schedule -> cargar registro de fuentes -> filtrar viable/parcial -> capturar -> normalizar -> deduplicar -> score -> shortlist -> revision humana -> handoff aprobado -> auditoria`

Notas:
- excluir `bloqueada` de la captura automatica
- bajar frecuencia o peso de `parcial`
- mantener la traza completa desde la fuente hasta la shortlist

## 2. Monitor por beat o vertical editorial
Flujo:
`schedule -> seleccionar beat -> cargar fuentes del beat -> capturar -> normalizar -> score por beat -> rankear -> aplicar cuotas -> shortlist -> revision humana`

## 3. Workflow de gobernanza de salud de fuentes
Flujo:
`trigger periodico -> revisar accesibilidad y errores -> comprobar frescura -> reclasificar viable/parcial/bloqueada -> notificar owner editorial -> abrir tarea de remediacion`

## 4. Handoff a publicacion sin autopublicar
Flujo:
`shortlist aprobada -> enriquecer payload -> crear borrador o cola de publicacion -> asignar responsable -> notificar -> registrar handoff`

## 5. Auditoria de un pipeline existente
Checklist:
- schedule y captura separados de shortlist y aprobacion
- esquema comun de candidato editorial
- scoring explicito y auditable
- shortlist y revision persistidos
- handoff solo tras aprobacion
- fuentes bloqueadas fuera de automatizacion
