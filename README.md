# GrafoBlog - Python y Neo4j

Aplicación web para administrar un blog como grafo. Los usuarios pueden registrarse,
iniciar sesión, publicar artículos y comentar. Los administradores pueden gestionar
etiquetas, roles y cuentas.

## Modelo

| Nodo | Propiedades principales |
| --- | --- |
| Usuario | id, nombre, email, password_hash, rol, creado |
| Articulo | id, titulo, contenido, creado, actualizado |
| Etiqueta | id, nombre |
| Comentario | id, texto, creado |

Relaciones dirigidas: `(Usuario)-[:PUBLICO]->(Articulo)`,
`(Usuario)-[:ESCRIBIO]->(Comentario)`,
`(Comentario)-[:EN_ARTICULO]->(Articulo)` y
`(Articulo)-[:ETIQUETADO_CON]->(Etiqueta)`.

El rol se consulta en Neo4j en cada petición. Un usuario normal solo modifica
sus artículos y comentarios, mientras que el administrador puede gestionar cualquier
contenido.

## Requisitos

- Python 3.10 o superior.
- Neo4j Desktop o AuraDB accesible con Bolt.
- Paquetes indicados en `requirements.txt`.

## Inicio en PowerShell

Para iniciar el blog: 

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:NEO4J_URI = 'neo4j://localhost:7687'
$env:NEO4J_USER = 'neo4j'
$env:NEO4J_PASSWORD = 'TU_CONTRASENA'
$env:NEO4J_DATABASE = 'neo4j'
$env:FLASK_SECRET_KEY = 'UNA_CLAVE_LARGA_Y_ALEATORIA'
flask --app run:app init-db
flask --app run:app create-admin
flask --app run:app run --debug
```

Abre <http://127.0.0.1:5000>. 

La cuenta administrativa inicial se crea mediante una orden que solicita
nombre, correo y contraseña. Después, la administración puede cambiar roles.
En el archivo `cypher/01_schema.cypher` se documentaron las restricciones creadas por
`init-db`. 

## Funciones y rutas

| Función | Acceso |
| --- | --- |
| Ver publicaciones y comentarios | Público |
| Registrarse e ingresar | Público |
| Crear artículos y comentarios | Usuario autenticado |
| Editar o borrar contenido propio | Autor |
| Editar o borrar cualquier contenido | Administrador |
| Crear, editar, borrar etiquetas; gestionar cuentas y roles | Administrador |
