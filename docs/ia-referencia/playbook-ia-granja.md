# Playbook: IA para Apoyar el Negocio de Granja Cabral

> Basado en la interacción real del 6 de abril de 2026 entre Laura Cabral y Erebus (IA).
> Este documento sirve como marco de referencia para futuras implementaciones de IA
> en el ecosistema de Granja Cabral y clientes similares del sector avícola.

---

## 1. Tipos de Consulta que Laura Hizo (y que Funcionaron)

### A. Cálculos Financieros en Tiempo Real
- **Entrada:** datos operativos crudos (aves, gastos diarios, precios por tipo de huevo)
- **Salida:** ganancia diaria, margen, punto de equilibrio
- **Valor:** toma de decisiones inmediata sin Excel

### B. Análisis de Datos Históricos
- **Entrada:** archivos CSV/Excel de ventas acumuladas (años)
- **Salida:** gráficos de ingresos mensuales, anuales, top clientes, comparativas de precios
- **Valor:** identificar tendencias, temporadas, clientes clave

### C. Investigación de Mercado
- **Entrada:** pregunta abierta ("¿por qué bajó el precio del huevo?")
- **Salida:** análisis de noticias locales, factores macroeconómicos, competencia
- **Valor:** contexto externo que el productor no tiene tiempo de buscar

### D. Procesamiento de Documentos
- **Entrada:** ZIPs con Excel, chats de Messaging exportados, audios
- **Salida:** parseo estructurado, corrección de errores, generación de bases limpias
- **Valor:** convertir caos de datos informales en información actionable

### E. Planificación Estratégica
- **Entrada:** ideas de negocio (marca propia, tienda física, nuevos formatos)
- **Salida:** research de créditos (CAH), análisis de viabilidad, pasos a seguir
- **Valor:** pensamiento estratégico sin costo de consultoría

---

## 2. Formato de Datos que Laura Usó (y que la IA Entendió)

### Mensajes de Texto Simple
```
1. Tengo 8.762 aves distribuidas en 4 Galpones
2. Gastos diarios:
Balanceado (42 bolsas de 25 kg) = 2.436.000 guaraníes
Personales = 298.000
...
3. Calcula la ganancia por dia...
```

### Registros de Venta (Messaging)
```
Dalila
35 C x 18 = 630.000
39 B x 20 = 780.000
35 A x 21 = 735.000
```

### Audios de Voz
- La IA transcribió y extrajo datos numéricos directamente del audio
- Útil para productores que prefieren hablar a escribir

### Archivos Adjuntos
- ZIP con Excel de ventas
- Chat de Messaging exportado (.txt)
- La IA parseó, limpió y generó CSVs/Excel de salida

---

## 3. Qué la IA Produjo (Entregables)

| Entregable | Formato | Ubicación |
|---|---|---|
| Cálculo de ganancia diaria | Mensaje Messaging | Sesión en vivo |
| Parser de ventas Messaging → CSV/Excel | Python script | `data/scripts/parse_messaging_cli.py` |
| Gráficos históricos de ingresos | PNG | `data/charts/` |
| Template de producción diaria | Excel (.xlsx) | `data/templates/` |
| Análisis de precios por temporada | PNG comparativo | `data/charts/granja_precios_temporada.png` |
| Investigación CAH | Resumen textual | Sesión en vivo + `01_core_operations/financial_tracking/` |
| Lista de clientes actualizados | Markdown | `clientes_actuales_abril_2026.md` |

---

## 4. Lecciones Aprendidas (Qué Funcionó y Qué No)

### ✅ Funcionó Bien
- **Mensajes estructurados con números claros:** la IA calculó al instante
- **Compartir archivos directamente:** ZIPs con Excel se procesaron sin problemas
- **Pedir gráficos específicos:** "compará precios Dic-Mar de cada año" → entregado
- **Correcciones en tiempo real:** Laura aclaró que eran maples de 30, la IA ajustó
- **Investigación contextual:** buscar noticias locales sobre precios del huevo

### ⚠️ Fricciones
- **Audios con datos complejos:** la transcripción era buena pero los números a veces se confundían
- **Datos con errores manuales:** mismatches aritméticos en el chat original (52 de 4,284 registros)
- **Formatos inconsistentes:** "30 A x 22 y 23 = 671.000" requirió lógica especial de parser
- **Precios ambiguos:** ¿Gs 500 por bolsa o Gs 500.000? Requirió heurísticas

### 🔧 Soluciones Implementadas
- Parser con múltiples patrones regex para cada formato de venta
- Heurística: precios < 1000 son guaraníes literales, > 1000 son miles
- Detección automática de errores de cálculo vs. datos correctos
- Plantilla Excel estandarizada para reemplazar cuadernos físicos

---

## 5. Recomendaciones para Futuras Interacciones

### Para Laura (Usuario)
1. **Usar mensajes estructurados** cuando sea posible (listas numeradas)
2. **Especificar unidades** (maples de 30, precios por maple vs. por unidad)
3. **Compartir archivos** en vez de dictar datos largos
4. **Plantilla Excel diaria** → reemplaza los cuadernos físicos y reduce errores
5. **Fotos de cuadernos** → la IA puede leerlas (con créditos de visión disponibles)

### Para la IA (Erebus)
1. **Siempre confirmar unidades** antes de calcular
2. **Guardar datos en el repo** inmediatamente, no solo responder en chat
3. **Generar entregables descargables** (Excel, PNG, PDF) además de mensajes de texto
4. **Crear parsers reutilizables** para formatos recurrentes (ventas Messaging)
5. **Mantener historial de correcciones** para no repetir preguntas

---

## 6. Extrapolación: ¿Cómo Escalar Esto a Otros Clientes?

| Patrón | Cliente A (Granja Cabral) | Cliente B (ej. Peluquería) | Cliente C (ej. Clínica) |
|---|---|---|---|
| Datos crudos → Cálculos | Aves, gastos, precios | Citas, servicios, productos | Pacientes, tratamientos, costos |
| Chat → Estructurado | Ventas Messaging → CSV | Agendamiento → calendario | Historias clínicas → base de datos |
| Investigación de mercado | Precio del huevo, CAH | Tendencias de belleza | Regulaciones sanitarias |
| Reportes automáticos | Gráficos mensuales | Ranking de servicios | Estadísticas de pacientes |

**Infraestructura reutilizable:**
- Messaging → Parser → Supabase/CSV → Dashboard
- Aplicable a cualquier PYME que opere vía Messaging

---

## 7. Archivos Relacionados

- `../interacciones-laura-2026-04-06.md` — mensajes originales de Laura
- `../../data/scripts/parse_messaging_cli.py` — parser de ventas Messaging
- `../../data/templates/granja_produccion_template.xlsx` — template de producción
- `../../data/charts/` — gráficos generados
- `../../01_core_operations/financial_tracking/numeros_clave.md` — números actualizados
- `../../01_core_operations/financial_tracking/clientes_actuales_abril_2026.md` — clientes

---

*Documento generado por Erebus el 18 de mayo de 2026.*
*Última actualización: sesiones Messaging del 6 de abril de 2026.*
