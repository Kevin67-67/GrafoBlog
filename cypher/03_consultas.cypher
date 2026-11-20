// Grafo completo de una publicación
MATCH (a:Articulo)
OPTIONAL MATCH (u:Usuario)-[:PUBLICO]->(a)
OPTIONAL MATCH (a)-[:ETIQUETADO_CON]->(e:Etiqueta)
OPTIONAL MATCH (a)<-[:EN_ARTICULO]-(c:Comentario)<-[:ESCRIBIO]-(lector:Usuario)
RETURN a,u,e,c,lector LIMIT 100;

// Artículos por etiqueta
MATCH (a:Articulo)-[:ETIQUETADO_CON]->(e:Etiqueta)
RETURN e.nombre AS etiqueta, collect(a.titulo) AS articulos ORDER BY etiqueta;

// Actividad por usuario
MATCH (u:Usuario)
OPTIONAL MATCH (u)-[:PUBLICO]->(a:Articulo)
OPTIONAL MATCH (u)-[:ESCRIBIO]->(c:Comentario)
RETURN u.nombre AS usuario, count(DISTINCT a) AS articulos,
       count(DISTINCT c) AS comentarios ORDER BY articulos DESC;
