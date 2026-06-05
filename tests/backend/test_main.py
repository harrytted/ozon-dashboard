import unittest


class FastApiAppTest(unittest.TestCase):
    def test_app_imports_with_routes(self):
        from backend.main import app

        paths = {route.path for route in app.routes}
        self.assertIn("/api/health", paths)
        self.assertIn("/api/ozon/bind", paths)


if __name__ == "__main__":
    unittest.main()
