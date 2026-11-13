# Calidad de datos

Periodo 2026-08-25 a 2026-10-23 · Generado el 2026-11-11

## Hallazgos

- CDR: 15.553 filas; casos: 11.422 filas. Periodo 2026-08-25 a 2026-10-23 (60 días con datos).
- IDs duplicados: 0 en id_llamada, 0 en id_caso, 0 llamadas con más de un caso.
- id_agente vacío: 2.155 filas, todas abandonadas. Ninguna llamada atendida sin agente. escalado_a vacío: 10.503 (no escaladas, esperado).
- Valores imposibles: 0 esperas, duraciones o ACW negativos; 0 abandonadas con duración > 0; CSAT siempre entre 1 y 5.
- Casos con id_llamada ausente en el CDR: 0. Casos de llamadas abandonadas: 0. Agente, cliente y fecha coinciden con el CDR en todos los casos.
- Semanas incompletas: S35 (6 días, falta el lunes 24-ago) y S43 (5 días, hasta el viernes 23-oct). Se marcan con * y no se usan para concluir tendencias.
- 239 llamadas salientes (15,1 %) figuran como abandonadas y con espera. Es raro en salientes; revisa la definición. No entran en A2–A5.
- 1.976 llamadas atendidas (14,7 %) no tienen caso. FCR, CSAT y resolución cubren el 85,3 % de las atendidas. 1.148 casos vienen de llamadas salientes.
- Reincidencia = 1 coincide exactamente con estado reabierto (639 casos): C2 y C3 miden el mismo grupo.
- horas_resolucion y csat vienen informados también en casos pendientes y reabiertos. C5 usa solo casos resueltos; el CSAT usa todos los casos.

## Supuestos aplicados

- Semana ISO (lunes a domingo). A2–A5 sobre llamadas entrantes. B1–B4 sobre llamadas atendidas (entrantes y salientes). C y D sobre casos.
- Semáforo: cumple si alcanza la meta; en riesgo si está a menos de 10 % relativo de la meta; fuera de meta si pasa de ahí. Se aplica sobre el valor sin redondear.
- Diferencia con la línea base: ASA (22,06 s, 10,3 % sobre la meta) y reincidencia (5,59 %, 11,8 % sobre la meta) caen en «fuera de meta» con esta regla estricta. La línea base los marcó «en riesgo». Los valores coinciden con la línea base.
- No hay metas propias de Cesta en Recursos/: se usan las metas estándar del CLAUDE.md. Recursos/ solo contiene la hoja de marca v1.0.
- Franjas pico: 10–13 h y 19–21 h (nivel de servicio por hora bajo 55 %). Área esperada de escalamiento: Logística para estado_envio, devolucion, cambio_producto y reclamo_calidad; Billing para problema_pago y facturacion. Es un supuesto a validar con la operación.
- Cobertura: el CDR no trae turnos. Los agentes con llamadas por hora son una aproximación, no la dotación real.
- Antigüedad del backlog: días entre fecha_apertura y 2026-10-23. Valor en riesgo: suma de valor_orden sin doble conteo, en moneda local.
- No hay ejecución previa en Salidas/: no se calculan variaciones. El recálculo coincide con la línea base del CLAUDE.md.
