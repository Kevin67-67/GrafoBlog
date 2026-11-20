import unittest
from unittest.mock import MagicMock

try:
    from blog.web import create_app
except ImportError:
    create_app = None


@unittest.skipIf(create_app is None, "Instala requirements.txt para probar las rutas")
class RouteTests(unittest.TestCase):
    def setUp(self):
        self.repo = MagicMock()
        self.repo.articles.return_value = []
        self.repo.user_by_id.side_effect = lambda uid: (
            {"usuario": {"id": uid, "nombre": "Ana", "rol": "USUARIO"}}
            if uid else None
        )
        self.app = create_app(self.repo, {"TESTING": True, "SECRET_KEY": "test-secret"})
        self.client = self.app.test_client()

    def login(self, user_id="u1"):
        with self.client.session_transaction() as session:
            session["user_id"] = user_id
            session["csrf_token"] = "token"

    def test_public_home(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Publicaciones recientes", response.data)

    def test_admin_denied_to_regular_user(self):
        self.login()
        self.assertEqual(self.client.get("/admin").status_code, 403)

    def test_csrf_is_required(self):
        self.login()
        response = self.client.post("/articulos/nuevo", data={
            "titulo": "T", "contenido": "Texto"
        })
        self.assertEqual(response.status_code, 400)
        self.repo.create_article.assert_not_called()

    def test_author_can_update_own_article(self):
        self.login()
        self.repo.article.return_value = {
            "articulo": {"id": "a1", "titulo": "Original", "contenido": "Texto"},
            "autor": {"id": "u1", "nombre": "Ana"}, "etiquetas": []
        }
        self.repo.tags.return_value = []
        response = self.client.post("/articulos/a1/editar", data={
            "csrf_token": "token", "titulo": "Nuevo", "contenido": "Actualizado"
        })
        self.assertEqual(response.status_code, 302)
        self.repo.update_article.assert_called_once_with(
            "a1", "Nuevo", "Actualizado", []
        )

    def test_other_user_cannot_delete_article(self):
        self.login()
        self.repo.article.return_value = {
            "articulo": {"id": "a1"}, "autor": {"id": "u2"}, "etiquetas": []
        }
        response = self.client.post("/articulos/a1/eliminar",
                                    data={"csrf_token": "token"})
        self.assertEqual(response.status_code, 403)
        self.repo.delete_article.assert_not_called()

    def test_self_demote_denied(self):
        self.login()
        self.repo.user_by_id.side_effect = lambda uid: {
            "usuario": {"id": uid, "nombre": "Ana", "rol": "ADMIN"}
        }
        response = self.client.post("/admin/usuarios/u1/rol", data={
            "csrf_token": "token", "rol": "USUARIO"
        })
        self.assertEqual(response.status_code, 400)
        self.repo.set_role.assert_not_called()


if __name__ == "__main__":
    unittest.main()
