# Base para template de respuesta API
class SuccessResponseTemplate:
    @staticmethod
    def create(data=None, message="Operación exitosa", actions=None, metadata=None):
        return {
            "success": True,
            "data": data,
            "message": message,
            "actions": actions or [],
            "metadata": metadata or {}
        }

# Se pueden agregar más templates aquí
