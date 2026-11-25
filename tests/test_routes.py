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
        self.repo.tags.return_value = []
        self.repo.categories.return_value = [
            {"categoria": {"id": "c1", "nombre": "Tecnología"}},
            {"categoria": {"id": "c2", "nombre": "Educación"}},
        ]
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
            "a1", "Nuevo", "Actualizado", [], category_ids=[]
        )

    def test_article_accepts_multiple_categories_without_duplicates(self):
        self.login()
        self.repo.create_article.return_value = "a1"
        response = self.client.post("/articulos/nuevo", data={
            "csrf_token": "token", "titulo": "Título", "contenido": "Texto",
            "categories": ["c1", "c2", "c1"],
        })
        self.assertEqual(response.status_code, 302)
        self.repo.create_article.assert_called_once_with(
            "u1", "Título", "Texto", [], category_ids=["c1", "c2"]
        )

    def test_article_rejects_unknown_category(self):
        self.login()
        response = self.client.post("/articulos/nuevo", data={
            "csrf_token": "token", "titulo": "Título", "contenido": "Texto",
            "categories": ["missing"],
        })
        self.assertEqual(response.status_code, 400)
        self.repo.create_article.assert_not_called()

    def test_categories_render_in_article_and_edit_form(self):
        self.login()
        self.repo.comments.return_value = []
        self.repo.article.return_value = {
            "articulo": {"id": "a1", "titulo": "Título", "contenido": "Texto"},
            "autor": {"id": "u1", "nombre": "Ana"},
            "etiquetas": [],
            "categorias": [{"id": "c1", "nombre": "Tecnología"}],
        }
        detail = self.client.get("/articulos/a1")
        form = self.client.get("/articulos/a1/editar")
        self.assertIn("Categorías: Tecnología", detail.get_data(as_text=True))
        self.assertIn('name="categories" value="c1" checked', form.get_data(as_text=True))

    def test_only_admin_can_manage_categories(self):
        self.login()
        data = {"csrf_token": "token", "nombre": "Arte"}
        actions = [
            ("/admin/categorias", self.repo.create_category, ("Arte",)),
            ("/admin/categorias/c1/editar", self.repo.rename_category, ("c1", "Arte")),
            ("/admin/categorias/c1/eliminar", self.repo.delete_category, ("c1",)),
        ]
        for path, action, _ in actions:
            self.assertEqual(self.client.post(path, data=data).status_code, 403)
            action.assert_not_called()
        self.repo.user_by_id.side_effect = None
        self.repo.user_by_id.return_value = {
            "usuario": {"id": "u1", "nombre": "Ana", "rol": "ADMIN"}
        }
        for path, action, args in actions:
            self.assertEqual(self.client.post(path, data=data).status_code, 302)
            action.assert_called_once_with(*args)

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
