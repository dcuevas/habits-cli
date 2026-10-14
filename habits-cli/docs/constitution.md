# Constitución de habits-cli

Principios innegociables. Toda spec, plan y tarea debe cumplirlos.

1. **Simplicidad primero**: Python 3.12+ y solo biblioteca estándar en la
   aplicación. Única dependencia de desarrollo permitida: pytest.
2. **La spec manda**: ningún comportamiento se implementa si no está en la
   spec activa. Si falta una decisión, se detiene el trabajo y se pregunta.
3. **Lógica separada de interfaz**: el núcleo (core) no imprime ni lee de
   consola. La CLI es una capa fina. Todo el core es testeable sin la CLI.
4. **Tests como puerta**: cada tarea termina con sus tests en verde.
   Prohibido avanzar con tests en rojo.
5. **Datos locales y transparentes**: persistencia en un único archivo JSON
   legible. Nada de bases de datos ni de red.
6. **Idioma**: código e identificadores en inglés; mensajes al usuario y
   documentación en español.