from minio import Minio
from minio.error import S3Error


class Storage:
    def __init__(self, app=None):
        self.client = None
        self.bucket_name = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        server = app.config.get('MINIO_SERVER')
        access_key = app.config.get('MINIO_ACCESS_KEY')
        secret_key = app.config.get('MINIO_SECRET_KEY')
        secure = app.config.get('MINIO_SECURE', False)
        bucket = app.config.get('MINIO_BUCKET')

        if not server or not access_key or not secret_key or not bucket:
            raise RuntimeError("La configuración de MinIO es incompleta.")

        self.client = Minio(
            server,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )
        self.bucket_name = bucket

        try:
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
        except S3Error as exc:
            raise RuntimeError("No se pudo inicializar el bucket de MinIO.") from exc

        app.storage = self.client
        app.storage_bucket = bucket
        return app


storage = Storage()
