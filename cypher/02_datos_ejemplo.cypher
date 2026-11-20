// Datos ficticios para explorar el grafo
MERGE (e1:Etiqueta {id:'tag-python'}) SET e1.nombre='Python';
MERGE (e2:Etiqueta {id:'tag-neo4j'}) SET e2.nombre='Neo4j';
MERGE (e3:Etiqueta {id:'tag-grafos'}) SET e3.nombre='Grafos';
MERGE (a:Articulo {id:'art-demo-1'})
SET a.titulo='Primeros pasos con Neo4j',
    a.contenido='Neo4j almacena entidades como nodos y conexiones como relaciones.',
    a.creado=datetime('2026-11-18T12:00:00Z'),
    a.actualizado=datetime('2026-11-18T12:00:00Z');
MERGE (a)-[:ETIQUETADO_CON]->(e2);
MERGE (a)-[:ETIQUETADO_CON]->(e3);

