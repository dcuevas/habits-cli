# Spec 001 — MVP de habits-cli

## 1. Contexto y objetivo
Quien estudia con constancia necesita ver de un vistazo si mantiene el hábito. habits-cli es una herramienta de terminal que permite registrar hábitos de estudio y ver cuántos días consecutivos lleva cada uno (su racha). El objetivo del MVP es el ciclo mínimo completo: crear un hábito, marcarlo como hecho hoy y consultar la racha de todos. Es un proyecto educativo, de modo que la claridad pesa más que las funciones.

## 2. Usuarios
- **Estudiante individual**: usa la herramienta en su propio equipo, de forma local, sin cuenta ni conexión. Es el único usuario del MVP.

## 3. Historias de usuario
- HU-1. Como estudiante, quiero crear un hábito con un nombre, para empezar a registrarlo.
- HU-2. Como estudiante, quiero marcar un hábito como hecho hoy, para llevar el registro de mi constancia.
- HU-3. Como estudiante, quiero listar mis hábitos con su racha y si ya los hice hoy, para saber qué me falta y motivarme a no romper la racha.

## 4. Requisitos funcionales

**RF-1. Crear hábito**
- RF-1.1 Cuando el usuario cree un hábito con un nombre válido, el sistema lo registrará sin días completados y confirmará la creación con un mensaje.
- RF-1.2 El sistema ignorará los espacios al inicio y al final del nombre.
- RF-1.3 Si el nombre está vacío o solo contiene espacios, entonces el sistema rechazará la creación con un mensaje de error y no registrará nada.
- RF-1.4 Si ya existe un hábito cuyo nombre coincide sin distinguir mayúsculas y minúsculas, entonces el sistema rechazará la creación con un mensaje de error y no modificará los datos.
- RF-1.5 El sistema conservará la grafía original del nombre al mostrarlo.
- RF-1.6 Si el nombre, sin los espacios externos, supera los 120 caracteres, entonces el sistema rechazará la creación con un mensaje de error que indique el límite y no registrará nada.

**RF-2. Marcar hábito como hecho hoy**
- RF-2.1 Cuando el usuario marque un hábito existente como hecho, el sistema registrará la fecha de hoy para ese hábito y confirmará con un mensaje.
- RF-2.2 El sistema identificará el hábito sin distinguir mayúsculas y minúsculas ni espacios en los extremos.
- RF-2.3 Si el hábito ya estaba marcado hoy, entonces el sistema mostrará un aviso informativo, no duplicará el registro y terminará con éxito.
- RF-2.4 Si el hábito indicado no existe, entonces el sistema mostrará un mensaje de error indicando que no existe, terminará con fallo y no creará ningún hábito.

**RF-3. Listar hábitos con racha**
- RF-3.1 Cuando el usuario pida el listado, el sistema mostrará, por cada hábito y en orden de creación, su nombre, su racha actual en días y si está hecho hoy.
- RF-3.2 La racha será el número de días consecutivos completados que terminan hoy o, si hoy aún no está marcado, que terminan ayer.
- RF-3.3 Mientras un hábito no esté marcado hoy ni ayer, el sistema mostrará su racha como 0.
- RF-3.4 Mientras un hábito no tenga ningún día completado, el sistema mostrará su racha como 0.
- RF-3.5 Si no existe ningún hábito, entonces el sistema mostrará un mensaje amistoso que explique cómo crear el primero.
- RF-3.6 Si un hábito tiene fechas registradas posteriores a hoy, entonces el sistema las ignorará al calcular la racha y al determinar si está hecho hoy, sin borrarlas ni modificarlas.

**RF-4. Conservación de los datos**
- RF-4.1 Cuando el usuario cierre la herramienta y la vuelva a usar, el sistema conservará los hábitos y sus días completados.
- RF-4.2 Si el usuario usa la herramienta por primera vez, entonces el sistema funcionará sin configuración previa, como si no hubiera hábitos.
- RF-4.3 Si los datos guardados están dañados o no se pueden leer, entonces el sistema mostrará un mensaje de error que explique qué ocurrió y qué hacer para resolverlo, terminará con fallo y no modificará ni sobrescribirá esos datos.

## 5. Requisitos no funcionales
- RNF-1. Los mensajes al usuario y la ayuda estarán en español, con un tono claro y sin jerga técnica.
- RNF-2. Cada error indicará qué ocurrió y, cuando sea posible, qué hacer para corregirlo.
- RNF-3. Cada comando responderá de forma inmediata para hasta 100 hábitos con años de historial.
- RNF-4. Los datos permanecerán en el equipo del usuario, en un formato que una persona pueda leer, y la herramienta no usará la red.
- RNF-5. Un fallo durante la ejecución no deberá dejar los datos guardados en estado corrupto.
- RNF-6. El comportamiento será verificable de forma automática, sin depender de la fecha real del día.
- RNF-7. "Hoy" será la fecha del calendario según la zona horaria del equipo en el momento de ejecutar el comando; si el usuario cambia de zona horaria, se aplicará la vigente.

## 6. Casos límite
- Hábito marcado ayer y anteayer pero no hoy: la racha se mantiene (RF-3.2).
- Un día sin marcar entre dos fechas completadas: la racha se reinicia contando desde la fecha más reciente.
- Hábito recién creado y nunca marcado: racha 0, no hecho hoy.
- Nombres que solo difieren en mayúsculas o en espacios externos: se consideran el mismo hábito.
- Primer uso, sin datos previos: listado vacío con mensaje amistoso, sin errores.
- Marcar el mismo hábito varias veces en un día: un único registro.
- Cambio de día mientras la herramienta no está en uso: la racha se evalúa con la fecha del momento de la consulta.

## 7. Fuera de alcance
- Borrar o renombrar hábitos.
- Marcar días pasados o futuros, y desmarcar un día.
- Frecuencias distintas de la diaria, horarios y recordatorios.
- Mejor racha histórica, estadísticas y exportación de datos.
- Varios usuarios, sincronización y cualquier uso de red.

## 8. Criterios de finalización
- [ ] Cada RF tiene al menos una prueba automática que cubre sus criterios de aceptación.
- [ ] Los casos límite de la sección 6 están cubiertos por pruebas.
- [ ] Todas las pruebas pasan en verde.
- [ ] Un estudiante nuevo puede crear un hábito, marcarlo y ver su racha sin leer documentación adicional.
- [ ] Ningún comportamiento implementado queda fuera de esta spec.

## 9. Dudas abiertas
Ninguna por ahora.
