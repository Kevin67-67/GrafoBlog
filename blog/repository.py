import uuid

from neo4j import GraphDatabase


class BlogRepository:
    def __init__(self, uri, user, password, database="neo4j"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.database = database

    def close(self):
        self.driver.close()

    def run(self, query, **params):
        with self.driver.session(database=self.database) as session:
            return [dict(record) for record in session.run(query, **params)]

    def one(self, query, **params):
        rows = self.run(query, **params)
        return rows[0] if rows else None

    def schema(self):
        statements = [
            "CREATE CONSTRAINT usuario_id IF NOT EXISTS FOR (u:Usuario) REQUIRE u.id IS UNIQUE",
            "CREATE CONSTRAINT usuario_email IF NOT EXISTS FOR (u:Usuario) REQUIRE u.email IS UNIQUE",
            "CREATE CONSTRAINT articulo_id IF NOT EXISTS FOR (a:Articulo) REQUIRE a.id IS UNIQUE",
            "CREATE CONSTRAINT etiqueta_id IF NOT EXISTS FOR (e:Etiqueta) REQUIRE e.id IS UNIQUE",
            "CREATE CONSTRAINT comentario_id IF NOT EXISTS FOR (c:Comentario) REQUIRE c.id IS UNIQUE",
            "CREATE INDEX articulo_creado IF NOT EXISTS FOR (a:Articulo) ON (a.creado)",
        ]
        for statement in statements:
            self.run(statement)

    def user_by_email(self, email):
        return self.one("MATCH (u:Usuario {email:$email}) RETURN u{.*} AS usuario", email=email)

    def user_by_id(self, user_id):
        return self.one("MATCH (u:Usuario {id:$id}) RETURN u{.*} AS usuario", id=user_id)

    def create_user(self, name, email, password_hash, role="USUARIO"):
        return self.one(
            "CREATE (u:Usuario {id:$id,nombre:$name,email:$email,"
            "password_hash:$password_hash,rol:$role,creado:datetime()}) "
            "RETURN u{.*} AS usuario",
            id=str(uuid.uuid4()), name=name, email=email,
            password_hash=password_hash, role=role,
        )

    def users(self):
        return self.run("MATCH (u:Usuario) RETURN u{.id,.nombre,.email,.rol} AS usuario ORDER BY u.nombre")

    def set_role(self, user_id, role):
        return self.one(
            "MATCH (u:Usuario {id:$id}) SET u.rol=$role RETURN u{.id,.rol} AS usuario",
            id=user_id, role=role,
        )

    def delete_user(self, user_id):
        self.run(
            "MATCH (u:Usuario {id:$id}) "
            "OPTIONAL MATCH (u)-[:PUBLICO]->(a:Articulo) "
            "OPTIONAL MATCH (a)<-[:EN_ARTICULO]-(ca:Comentario) "
            "WITH u,collect(DISTINCT a) AS articulos,collect(DISTINCT ca) AS respuestas "
            "OPTIONAL MATCH (u)-[:ESCRIBIO]->(cp:Comentario) "
            "WITH [u]+articulos+respuestas+collect(DISTINCT cp) AS nodos "
            "UNWIND nodos AS n WITH DISTINCT n WHERE n IS NOT NULL DETACH DELETE n",
            id=user_id,
        )

    def tags(self):
        return self.run("MATCH (e:Etiqueta) RETURN e{.id,.nombre} AS etiqueta ORDER BY e.nombre")

    def create_tag(self, name):
        return self.one(
            "CREATE (e:Etiqueta {id:$id,nombre:$name}) RETURN e{.id,.nombre} AS etiqueta",
            id=str(uuid.uuid4()), name=name,
        )

    def rename_tag(self, tag_id, name):
        return self.one(
            "MATCH (e:Etiqueta {id:$id}) SET e.nombre=$name RETURN e{.id,.nombre} AS etiqueta",
            id=tag_id, name=name,
        )

    def delete_tag(self, tag_id):
        self.run("MATCH (e:Etiqueta {id:$id}) DETACH DELETE e", id=tag_id)

    def articles(self):
        return self.run(
            "MATCH (a:Articulo) OPTIONAL MATCH (u:Usuario)-[:PUBLICO]->(a) "
            "OPTIONAL MATCH (a)-[:ETIQUETADO_CON]->(e:Etiqueta) "
            "RETURN a{.id,.titulo,.contenido,.creado,.actualizado} AS articulo, "
            "u{.id,.nombre} AS autor, collect(DISTINCT e{.id,.nombre}) AS etiquetas "
            "ORDER BY articulo.creado DESC"
        )

    def article(self, article_id):
        return self.one(
            "MATCH (a:Articulo {id:$id}) OPTIONAL MATCH (u:Usuario)-[:PUBLICO]->(a) "
            "OPTIONAL MATCH (a)-[:ETIQUETADO_CON]->(e:Etiqueta) "
            "RETURN a{.id,.titulo,.contenido,.creado,.actualizado} AS articulo, "
            "u{.id,.nombre} AS autor, collect(DISTINCT e{.id,.nombre}) AS etiquetas",
            id=article_id,
        )

    def create_article(self, user_id, title, content, tag_ids):
        article_id = str(uuid.uuid4())
        self.run(
            "MATCH (u:Usuario {id:$user_id}) CREATE (u)-[:PUBLICO]->"
            "(a:Articulo {id:$id,titulo:$title,contenido:$content,"
            "creado:datetime(),actualizado:datetime()}) "
            "WITH a OPTIONAL MATCH (e:Etiqueta) WHERE e.id IN $tag_ids "
            "WITH a,collect(e) AS etiquetas "
            "FOREACH (tag IN etiquetas | MERGE (a)-[:ETIQUETADO_CON]->(tag))",
            user_id=user_id, id=article_id, title=title,
            content=content, tag_ids=tag_ids,
        )
        return article_id

    def update_article(self, article_id, title, content, tag_ids):
        self.run(
            "MATCH (a:Articulo {id:$id}) SET a.titulo=$title,a.contenido=$content,"
            "a.actualizado=datetime() WITH a "
            "OPTIONAL MATCH (a)-[r:ETIQUETADO_CON]->(:Etiqueta) "
            "WITH a,collect(r) AS relaciones "
            "FOREACH (rel IN relaciones | DELETE rel) "
            "WITH a OPTIONAL MATCH (e:Etiqueta) WHERE e.id IN $tag_ids "
            "WITH a,collect(e) AS etiquetas "
            "FOREACH (tag IN etiquetas | MERGE (a)-[:ETIQUETADO_CON]->(tag))",
            id=article_id, title=title, content=content, tag_ids=tag_ids,
        )

    def delete_article(self, article_id):
        self.run(
            "MATCH (a:Articulo {id:$id}) OPTIONAL MATCH (a)<-[:EN_ARTICULO]-(c:Comentario) "
            "WITH a,collect(c) AS comentarios FOREACH (c IN comentarios | DETACH DELETE c) "
            "DETACH DELETE a",
            id=article_id,
        )

    def comments(self, article_id):
        return self.run(
            "MATCH (c:Comentario)-[:EN_ARTICULO]->(a:Articulo {id:$id}) "
            "OPTIONAL MATCH (u:Usuario)-[:ESCRIBIO]->(c) "
            "RETURN c{.id,.texto,.creado} AS comentario,u{.id,.nombre} AS autor "
            "ORDER BY comentario.creado",
            id=article_id,
        )

    def create_comment(self, user_id, article_id, text):
        return self.one(
            "MATCH (u:Usuario {id:$user_id}),(a:Articulo {id:$article_id}) "
            "CREATE (u)-[:ESCRIBIO]->(c:Comentario {id:$id,texto:$text,"
            "creado:datetime()})-[:EN_ARTICULO]->(a) RETURN c.id AS id",
            user_id=user_id, article_id=article_id, id=str(uuid.uuid4()), text=text,
        )

    def comment(self, comment_id):
        return self.one(
            "MATCH (c:Comentario {id:$id})-[:EN_ARTICULO]->(a:Articulo) "
            "OPTIONAL MATCH (u:Usuario)-[:ESCRIBIO]->(c) "
            "RETURN c{.id,.texto} AS comentario,u{.id} AS autor,a.id AS articulo_id",
            id=comment_id,
        )

    def update_comment(self, comment_id, text):
        self.run("MATCH (c:Comentario {id:$id}) SET c.texto=$text", id=comment_id, text=text)

    def delete_comment(self, comment_id):
        self.run("MATCH (c:Comentario {id:$id}) DETACH DELETE c", id=comment_id)
