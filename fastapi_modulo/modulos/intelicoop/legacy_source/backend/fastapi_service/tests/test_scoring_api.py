import unittest

from fastapi.testclient import TestClient

from app.main import app


class ScoringApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_post_scoring_returns_expected_fields(self):
        payload = {
            "ingreso_mensual": 4000,
            "deuda_actual": 500,
            "antiguedad_meses": 48,
        }
        response = self.client.post("/api/ml/scoring/", json=payload)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("score", body)
        self.assertIn("recomendacion", body)
        self.assertIn("riesgo", body)
        self.assertEqual(body["score"], 0.73)
        self.assertEqual(body["recomendacion"], "evaluar")
        self.assertEqual(body["riesgo"], "medio")

    def test_post_scoring_returns_422_for_invalid_input(self):
        payload = {
            "ingreso_mensual": -100,
            "deuda_actual": 200,
            "antiguedad_meses": 12,
        }
        response = self.client.post("/api/ml/scoring/", json=payload)

        self.assertEqual(response.status_code, 422)

    def test_post_scoring_high_score_returns_aprobar(self):
        payload = {
            "ingreso_mensual": 6000,
            "deuda_actual": 300,
            "antiguedad_meses": 120,
        }
        response = self.client.post("/api/ml/scoring/", json=payload)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertGreaterEqual(body["score"], 0.8)
        self.assertEqual(body["recomendacion"], "aprobar")
        self.assertEqual(body["riesgo"], "bajo")

    def test_docs_endpoint_is_available(self):
        response = self.client.get("/docs")

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers.get("content-type", ""))

    def test_openapi_includes_scoring_route(self):
        response = self.client.get("/openapi.json")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("/api/ml/scoring", body.get("paths", {}))


if __name__ == "__main__":
    unittest.main()
