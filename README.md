# GrafoBlog - Python y Neo4j

Aplicación web para administrar un blog como grafo. Los usuarios pueden registrarse,
iniciar sesión, publicar artículos y comentar. Los administradores pueden gestionar
etiquetas, roles y cuentas.

## Modelo

| Nodo | Propiedades principales |
| --- | --- |
| Usuario | id, nombre, email, password_hash, rol, creado |
| Articulo | id, titulo, contenido, creado, actualizado, imagen e imagen_tipo (opcionales) |
| Etiqueta | id, nombre |
| Comentario | id, texto, creado |

Relaciones dirigidas: `(Usuario)-[:PUBLICO]->(Articulo)`,
`(Usuario)-[:ESCRIBIO]->(Comentario)`,
`(Comentario)-[:EN_ARTICULO]->(Articulo)` y
`(Articulo)-[:ETIQUETADO_CON]->(Etiqueta)`.

El rol se consulta en Neo4j en cada petición. El autor puede modificar sus artículos
y comentarios. El administrador puede gestionar el contenido de cualquier usuario.

## Requisitos

- Python 3.10.
- Una base de Neo4j en ejecución, local o en AuraDB, y sus credenciales.
- Las dependencias de `requirements.txt`..

## Inicio en PowerShell de la aplicación

Abre PowerShell en la carpeta `blog_neo4j`, donde están `run.py` y `requirements.txt`.
Inicia la base de Neo4j antes de preparar o arrancar el blog.

### 1. Preparar el entorno

```powershell
if (-not (Test-Path '.\.venv\Scripts\python.exe')) {
    python -m venv .venv
}
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Configurar la conexión

Ejecuta este bloque en cada nueva ventana de PowerShell. 

```powershell
$env:NEO4J_URI = 'neo4j://localhost:7687'
$env:NEO4J_USER = 'neo4j'
$env:NEO4J_DATABASE = 'neo4j'
$grafoPassword = Read-Host 'Contraseña de Neo4j' -AsSecureString
$env:NEO4J_PASSWORD = [pscredential]::new($env:NEO4J_USER, $grafoPassword).GetNetworkCredential().Password
$env:FLASK_SECRET_KEY = & .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Inicializar la base y crear el primer administrador


```powershell
& .\.venv\Scripts\python.exe -m flask --app run:app init-db
& .\.venv\Scripts\python.exe -m flask --app run:app create-admin
```

### 4. Arrancar el blog

```powershell
& .\.venv\Scripts\python.exe -m flask --app run:app run --host 127.0.0.1 --port 5000
```

Abre <http://127.0.0.1:5000> y usa **Ctrl+C** en PowerShell para detener el servidor.


## Funciones y rutas

| Función | Acceso |
| --- | --- |
| Ver publicaciones y comentarios | Público |
| Registrarse e ingresar | Público |
| Crear artículos y comentarios | Usuario autenticado |
| Editar o borrar contenido propio | Autor |
| Editar o borrar cualquier contenido | Administrador |
| Crear, editar o borrar etiquetas y gestionar cuentas y roles | Administrador |


## Pruebas

Desde la carpeta del proyecto, ejecuta las pruebas de rutas con el repositorio simulado.

```powershell
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
