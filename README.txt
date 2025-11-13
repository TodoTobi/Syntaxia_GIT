DESCRIPCIÓN GENERAL DEL PROYECTO
SyntaxIA es un chatbot educativo pensado para la especialidad de Técnico en Informática de las Comunicaciones (TICs). El backend usa Flask para exponer una página web con interfaz de chat y servicios REST. Desde el navegador, el estudiante puede conversar con el asistente, enviar imágenes para detectar dispositivos TIC y, cuando corresponde, abrir un visor 3D con modelos OBJ relacionados. El público objetivo son docentes que evalúan el Proyecto Integrador II y estudiantes de secundaria con bases de programación.

TECNOLÓGÍAS UTILIZADAS
Lenguaje principal: Python 3 para el servidor Flask (app.py).
Framework web: Flask para ruteo, plantillas Jinja2 y entrega de archivos.
Frontend: plantillas HTML en templates/index.html y templates/viewer.html con CSS propio, Bootstrap 5 y JavaScript plano.
Bibliotecas de IA: cliente Groq (groq) para llamar al modelo Llama 3.1 desde api_client/mistral_client.py.
Visión por computadora: Ultralytics YOLOv5 (ultralytics) y OpenCV para analizar imágenes en api_client/yolo_client.py.
3D: Three.js cargado desde módulos ESM para renderizar OBJ en el navegador (templates/index.html y templates/viewer.html).
Audio: pyttsx3 para sintetizar en voz las respuestas generadas (voice_module/text_to_speech.py).
Manejo de configuraciones: python-dotenv opcional y utilidades en utils/config.py.

ARQUITECTURA Y ESTRUCTURA DE CARPETAS
app.py es el punto de entrada: define las rutas HTML, los endpoints /api/mensaje y /api/imagen, y orquesta las llamadas a la IA, YOLO y síntesis de voz.
api_client/ contiene los conectores externos. mistral_client.py envía prompts al modelo Groq y yolo_client.py ejecuta detección, selecciona modelos y arma la respuesta.
modelado_3d/ guarda generar_modelo.py, responsable de generar o copiar modelos OBJ de base cuando se necesita un placeholder.
voice_module/ text_to_speech.py encapsula pyttsx3 en un hilo para no bloquear Flask.
utils/ config.py centraliza el acceso a variables de entorno y rutas de trabajo (uploads, modelos3d, pedidos_modelado).
templates/ incluye index.html (chat principal) y viewer.html (visor dedicado) con la lógica de interfaz en JavaScript.
assets/ almacena assets 3D curados. assets/models/index.json lista archivos OBJ disponibles y library/ guarda los recursos.
config/ contiene settings.example.env (ejemplo de variables) y mapping.yaml (referencias de clases a modelos preferidos; actualmente no se ve usado directamente en código).
data/ se usa para generar carpetas en tiempo de ejecución (uploads, modelos3d, pedidos_modelado, base_models con placeholders).
scripts/ agrupa utilidades para mantener la biblioteca 3D (build_index.py, add_to_library.py, test_yolo.py, etc.).
Raíz del proyecto: yolov5su.pt (pesos YOLO), requirements.txt y app.py.

CÓMO LEVANTAR EL PROYECTO (INSTALACIÓN Y EJECUCIÓN)
Requisitos previos: Python 3.10+ y pip instalados. Se recomienda crear un entorno virtual.
1. Instalar dependencias: pip install -r requirements.txt.
2. Configurar variables (ver sección siguiente) antes de iniciar.
3. Ejecutar el servidor: python app.py. El modo debug está activado por defecto (app.run(debug=True)).
4. Abrir el navegador en http://127.0.0.1:5000/ para usar el chat. Flask permite cambiar host y puerto mediante variables de entorno FLASK_HOST y FLASK_PORT si se configuran y se adapta el arranque manualmente.
Para entornos de producción se puede usar gunicorn o waitress, pero no hay scripts listos en el repositorio.

CONFIGURACIONES Y PARÁMETROS IMPORTANTES
utils/config.py carga .env o api.env automáticamente si existen en la raíz y valida que GROQ_API_KEY esté presente. Sin esa clave el servidor no arranca.
Variables soportadas: GROQ_API_KEY (obligatoria), LLM_MODEL (modelo Groq a usar, por defecto llama a llama-3.1-8b-instant), BASE_URL (endpoint Groq opcional). settings.ensure_dirs crea data/uploads, data/modelos3d y data/pedidos_modelado si faltan.
config/settings.example.env muestra una configuración antigua para Mistral; hoy el flujo real requiere GROQ_API_KEY y no usa MISTRAL_API_KEY. Documentar este cambio cuando se distribuya el archivo de ejemplo.
Para visión por computadora, el archivo yolov5su.pt debe estar presente en la raíz; yolo_client.py falla con FileNotFoundError si no lo encuentra.
Si se desea desactivar la voz, se puede omitir pyttsx3 o envolver las llamadas a voice_module.text_to_speech.hablar.

LÓGICA INTERNA DEL CHATBOT
En templates/index.html el área de chat captura la entrada del usuario con JavaScript, arma un mensaje y lo muestra en pantalla. Al enviar texto se realiza fetch POST a /api/mensaje con JSON {"mensaje": texto}. Si hay una imagen adjunta usa FormData y llama a /api/imagen.
El backend (app.py) recibe /api/mensaje, valida que el mensaje no esté vacío y delega en api_client/mistral_client.responder_mensaje_texto. Ese módulo arma un prompt con system_prompt educativo y llama al cliente Groq. La respuesta se devuelve como texto y, si menciona “modelo 3d”, se guarda un registro en data/pedidos_modelado.
Después de enviar la respuesta al navegador, app.py intenta sintetizarla usando voice_module.text_to_speech.hablar en un hilo para no bloquear. El frontend renderiza el Markdown, guarda la conversación en localStorage y muestra la respuesta en pantalla.

LÓGICA DEL VISOR 3D Y PROCESAMIENTO DE IMÁGENES
Cuando el usuario adjunta una imagen, el frontend envía la foto y un texto opcional a /api/imagen. En el servidor, api_client/yolo_client.analizar_imagen_yolo guarda la imagen en data/uploads/entrada.jpg, ejecuta YOLO sobre ella y arma una lista de objetos relevantes (clase + confianza).
El módulo filtra clases TIC (laptop, router, monitor, etc.), resume lo detectado y busca un modelo 3D para la clase objetivo. Primero intenta encontrar un asset curado en assets/models/index.json, luego generar un placeholder con modelado_3d/generar_modelo.py y finalmente aplica un fallback genérico si existe. La ruta resultante (por ejemplo /modelos/laptop.obj) se devuelve al frontend.
En la interfaz, la función mostrarModelo cambia del chat al visor embebido y llama a cargarModelo3D, que trae Three.js y los cargadores OBJ/MTL desde esm.sh. Se arma la escena con cámara, luces hemisférica/ambiental/direccional y una grilla de referencia. El visor dedicado viewer.html repite la lógica pero agrega comandos de texto para rotar, escalar, cambiar color u otras transformaciones sobre el modelo cargado.

FLUJO DE USO PARA UN USUARIO FINAL
1. Entrar a http://127.0.0.1:5000/ y esperar a que cargue el chat.
2. Escribir una pregunta sobre TICs en el cuadro de texto y presionar Enviar (Enter o botón).
3. Leer la respuesta del asistente; si hay audio disponible se reproduce automáticamente.
4. Opcional: adjuntar una imagen desde el botón de clip, confirmar y volver a Enviar. El sistema detecta dispositivos TIC en la foto y puede proponer un modelo 3D.
5. Si aparece un enlace a “Abrir en visor 3D”, hacer clic para ver el modelo en pantalla completa y usar los comandos disponibles (rotar, escalar, color, wireframe, etc.).

DECISIONES DE DISEÑO Y BUENAS PRÁCTICAS
Separación clara entre backend y frontend: Flask solo sirve endpoints y delega en módulos especializados (api_client, modelado_3d, voice_module), facilitando mantenimiento.
Configuración centralizada en utils/config.py con validación temprana de claves, lo que evita fallos silenciosos.
En el frontend se usa una única plantilla con JavaScript modular (funciones addMessage, showTyping, enviar, cargarModelo3D) que mantienen la lógica del chat y el visor encapsulada.
Uso de localStorage para conservar el historial del chat entre recargas y de fetch asíncrono con indicadores de escritura, mejorando la experiencia del usuario.
En el visor 3D se normalizan modelos OBJ (reescritura de rutas MTL, copia de texturas) para garantizar que los recursos funcionen aunque tengan rutas complejas.
Estas decisiones hacen que el código sea más mantenible, permitan agregar nuevos proveedores de IA o nuevos modelos 3D sin reescribir la app completa y simplifican la prueba por parte de docentes.

PROBLEMAS FRECUENTES Y SOLUCIONES (FAQ TÉCNICA)
Si al iniciar Flask aparece “GROQ_API_KEY no está configurada”, crear un archivo .env en la raíz con GROQ_API_KEY=tu_clave y reiniciar.
Si /api/imagen devuelve “No se encontró YOLO”, verificar que yolov5su.pt exista en la raíz. En caso contrario descargar el peso correcto y colocarlo ahí.
Si el visor 3D no muestra nada y la consola indica errores al cargar módulos desde esm.sh, revisar la conexión a Internet porque Three.js se carga desde CDN.
Si pyttsx3 lanza errores en Linux sin servidor de audio, se puede deshabilitar la síntesis modificando app.py para omitir hablar().
Si un modelo OBJ cargado pierde texturas, confirmar que assets/models/index.json apunte a carpetas con archivos .mtl y texturas. Usar scripts/build_index.py para regenerar el índice cuando se agregan modelos.

CRÉDITOS Y LICENCIA
Proyecto desarrollado por estudiantes de 5°2 de la Escuela Técnica N°20 D.E. 20 “Carolina Muzzilli” en el marco del Proyecto Integrador II. Uso educativo sin fines comerciales. Si se reutiliza, citar al equipo original y la escuela.
