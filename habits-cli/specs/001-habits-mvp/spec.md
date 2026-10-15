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

**Interfaz de línea de comandos.** El ejecutable se llama `habits` y ofrece tres subcomandos con nombre en inglés: `habits add "<nombre>"`, `habits done "<nombre>"` y `habits list`. El nombre del hábito es un único argumento (entre comillas si contiene espacios). Todos los mensajes al usuario están en español.

**Códigos de salida.** 0 si el comando termina bien (incluido el aviso de RF-2.3 y el listado vacío); 1 ante cualquier error de negocio o de datos (nombre inválido o duplicado, hábito inexistente, datos dañados, fallo de escritura); 2 ante un uso incorrecto de la línea de comandos (RF-5.2).

**RF-1. Crear hábito** (`habits add`)
- RF-1.1 Cuando el usuario cree un hábito con un nombre válido, el sistema lo registrará sin días completados y confirmará la creación con un mensaje.
- RF-1.2 El sistema ignorará los espacios al inicio y al final del nombre. Por "espacio" se entiende cualquier carácter que `str.strip()` de Python elimina (incluidos tabuladores y espacios duros). Los espacios internos se respetan tal cual: "Leer  mucho" (dos espacios) y "Leer mucho" son hábitos distintos.
- RF-1.3 Si el nombre está vacío o solo contiene espacios, entonces el sistema rechazará la creación con un mensaje de error, terminará con fallo y no registrará nada.
- RF-1.4 Si ya existe un hábito cuyo nombre, ya sin espacios externos, coincide sin distinguir mayúsculas y minúsculas (comparación con `casefold()`, sin normalización Unicode), entonces el sistema rechazará la creación con un mensaje de error, terminará con fallo y no modificará los datos.
- RF-1.5 El sistema guardará y mostrará el nombre ya sin espacios externos y con su grafía original (mayúsculas y minúsculas tal como se escribieron).
- RF-1.6 Si el nombre, sin los espacios externos, supera los 120 caracteres (contados como caracteres de Python), entonces el sistema rechazará la creación con un mensaje de error que indique el límite, terminará con fallo y no registrará nada.
- RF-1.7 Un nombre es válido si, tras quitar los espacios externos, no está vacío y tiene 120 caracteres o menos. No existen otras restricciones sobre los caracteres permitidos.

**RF-2. Marcar hábito como hecho hoy** (`habits done`)
- RF-2.1 Cuando el usuario marque un hábito existente como hecho, el sistema registrará la fecha de hoy para ese hábito y confirmará con un mensaje.
- RF-2.2 El sistema identificará el hábito comparando el nombre indicado, sin espacios externos, con los nombres existentes sin distinguir mayúsculas y minúsculas (mismo criterio que RF-1.4).
- RF-2.3 Si el hábito ya estaba marcado hoy, entonces el sistema mostrará un aviso informativo, no duplicará el registro y terminará con éxito.
- RF-2.4 Si el hábito indicado no existe (incluido un nombre vacío o formado solo por espacios), entonces el sistema mostrará un mensaje de error indicando que no existe, terminará con fallo y no creará ningún hábito.
- RF-2.5 Si el hábito tiene fechas registradas posteriores a hoy, marcarlo como hecho igualmente registrará la fecha de hoy.

**RF-3. Listar hábitos con racha** (`habits list`)
- RF-3.1 Cuando el usuario pida el listado, el sistema mostrará una línea por hábito, en el orden en que aparecen en los datos guardados (orden de creación), con el formato `<nombre> · racha: N día(s) · hecho hoy` o `<nombre> · racha: N día(s) · pendiente`. Se escribirá "1 día" en singular y "N días" en los demás casos. Los nombres no se truncan ni se alinean.
- RF-3.2 La racha será el número de días consecutivos completados que terminan hoy o, si hoy aún no está marcado, que terminan ayer.
- RF-3.3 Mientras un hábito no esté marcado hoy ni ayer (incluido el que no tiene ningún día completado), el sistema mostrará su racha como 0.
- RF-3.4 Si no existe ningún hábito, entonces el sistema mostrará un mensaje amistoso que explique cómo crear el primero (con `habits add "<nombre>"`) y terminará con éxito.
- RF-3.5 Si un hábito tiene fechas registradas posteriores a hoy (por ejemplo, tras un cambio de zona horaria o por edición manual del archivo), entonces el sistema las tratará como datos válidos, las ignorará al calcular la racha y al determinar si está hecho hoy, y no las borrará ni modificará. Un hábito que solo tenga fechas futuras mostrará racha 0 y estará pendiente.

**RF-4. Conservación de los datos**
- RF-4.1 Cuando el usuario cierre la herramienta y la vuelva a usar, el sistema conservará los hábitos y sus días completados.
- RF-4.2 Si el usuario usa la herramienta por primera vez (o el archivo de datos no existe), entonces el sistema funcionará sin configuración previa, como si no hubiera hábitos. El directorio y el archivo se crean la primera vez que se guarda algo; `habits list` sin archivo no crea nada.
- RF-4.3 Si los datos guardados están dañados o no se pueden leer, entonces cualquier comando (`add`, `done` o `list`) mostrará un mensaje de error que explique qué ocurrió y qué hacer para resolverlo (corregir el archivo a mano o moverlo para empezar de cero), terminará con fallo y no modificará ni sobrescribirá esos datos. Se consideran dañados los datos cuando: el archivo no se puede leer, no es JSON válido, no tiene la estructura esperada, contiene un nombre inválido según RF-1.7, contiene nombres duplicados (sin distinguir mayúsculas y minúsculas) o contiene una fecha con formato inválido.
- RF-4.4 Las fechas duplicadas o desordenadas dentro de un hábito no se consideran datos dañados: se tratan como un conjunto de fechas.
- RF-4.5 Si no se puede escribir el archivo (por ejemplo, por permisos o disco lleno), entonces el sistema mostrará un mensaje de error en español, terminará con fallo y dejará intacto el contenido anterior del archivo.

**RF-5. Ayuda y uso incorrecto**
- RF-5.1 El sistema ofrecerá ayuda en español mediante `habits --help` y `habits <comando> --help`, con la sintaxis y una breve descripción de cada comando.
- RF-5.2 Si el usuario escribe un comando desconocido, omite argumentos obligatorios, añade argumentos de más o ejecuta `habits` sin comando, entonces el sistema mostrará un mensaje en español ("Uso incorrecto. Prueba: habits --help") junto con una línea con la sintaxis del comando, y terminará con código 2.

## 5. Requisitos no funcionales
- RNF-1. Los mensajes al usuario y la ayuda estarán en español, con un tono claro y sin jerga técnica. El núcleo (core) devolverá resultados o errores tipados sin texto; la CLI los traducirá a los mensajes en español.
- RNF-2. Cada error indicará qué ocurrió y, cuando sea posible, qué hacer para corregirlo.
- RNF-3. Cada comando terminará en menos de 1 segundo con 100 hábitos y 10 años de fechas completadas por hábito. No hay límite de número de hábitos, pero por encima de 100 no se garantiza ese tiempo.
- RNF-4. Los datos permanecerán en el equipo del usuario, en un único archivo JSON legible, ubicado por defecto en `~/.habits-cli/habits.json` (se puede cambiar con la variable de entorno `HABITS_FILE`), y la herramienta no usará la red. La estructura es `{"habits": [{"name": "...", "dates": ["2026-01-31", ...]}]}`, sin campo de versión; el orden de la lista es el orden de creación y las fechas son fechas locales en formato ISO, sin zona horaria.
- RNF-5. Un fallo durante la ejecución no deberá dejar los datos guardados en estado corrupto: la escritura se hará en un archivo temporal del mismo directorio que luego reemplaza al original de forma atómica. No se mantienen copias de seguridad.
- RNF-6. El comportamiento será verificable de forma automática, sin depender de la fecha real del día: la CLI obtiene la fecha de hoy y se la pasa al core como parámetro.
- RNF-7. "Hoy" será la fecha local del calendario según la zona horaria del equipo en el momento de ejecutar el comando; la CLI la lee una sola vez por ejecución. Si el usuario cambia de zona horaria, se aplicará la vigente, sin compensaciones.
- RNF-8. La salida se asume en UTF-8 y sin colores.

## 6. Casos límite
- Hábito marcado ayer y anteayer pero no hoy: racha 2, pendiente (RF-3.2).
- Hábito marcado hoy, ayer y anteayer: racha 3, hecho hoy.
- Un día sin marcar entre dos fechas completadas (marcado hoy y hace tres días, no ayer ni anteayer): racha 1.
- Hábito marcado hace dos días pero no ayer ni hoy: racha 0.
- Hábito recién creado y nunca marcado: racha 0, pendiente.
- Hábito con solo fechas posteriores a hoy: racha 0, pendiente (RF-3.5).
- Nombres que solo difieren en mayúsculas o en espacios externos: se consideran el mismo hábito.
- Nombres que difieren en espacios internos: son hábitos distintos.
- Nombre vacío o solo espacios en `add`: error (RF-1.3); en `done`: hábito inexistente (RF-2.4).
- Nombre de exactamente 120 caracteres: válido; de 121: error (RF-1.6).
- Marcar un hábito que no existe: error y no se crea ningún hábito (RF-2.4).
- Datos dañados: cualquier comando falla sin modificar el archivo (RF-4.3).
- Primer uso, sin datos previos: listado vacío con mensaje amistoso, sin errores.
- Marcar el mismo hábito varias veces en un día: un único registro.
- Cambio de día mientras la herramienta no está en uso: la racha se evalúa con la fecha del momento de la consulta.

## 7. Fuera de alcance
- Borrar o renombrar hábitos.
- Marcar días pasados o futuros, y desmarcar un día.
- Frecuencias distintas de la diaria, horarios y recordatorios.
- Mejor racha histórica, estadísticas y exportación de datos.
- Varios usuarios, sincronización y cualquier uso de red.
- Ejecuciones simultáneas de la herramienta sobre los mismos datos.
- Compensar cambios de zona horaria, de horario de verano o un reloj del sistema atrasado (un cambio de zona puede repetir o saltar un día).
- Salidas en codificaciones distintas de UTF-8.

## 8. Criterios de finalización
Verificables automáticamente (puerta de tests):
- [ ] Cada RF tiene al menos una prueba automática que cubre sus criterios de aceptación.
- [ ] Los casos límite de la sección 6 están cubiertos por pruebas.
- [ ] Todas las pruebas pasan en verde.

Revisión manual (fuera de la puerta de tests):
- [ ] Un estudiante nuevo puede crear un hábito, marcarlo y ver su racha sin leer documentación adicional.
- [ ] Ningún comportamiento implementado queda fuera de esta spec.

## 9. Dudas abiertas
Ninguna por ahora.
