
import sys
import os
import time
from minio import Minio
from minio.error import S3Error

# Ensure we can import from project root
sys.path.append(os.getcwd())

from config.settings import get_settings

def debug_minio():
    print("🛠️ Starting MinIO Debug...")
    
    try:
        settings = get_settings()
        print(f"📋 Configuration:")
        print(f"   Endpoint: {settings.minio_endpoint}")
        print(f"   Access Key: {settings.minio_access_key[:4]}***")
        print(f"   Secure: {settings.minio_secure}")
        print(f"   Bucket: {settings.minio_bucket}")

        client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
            cert_check=False
        )
        print("✅ Client initialized.")

        bucket_name = settings.minio_bucket
        
        print(f"🔍 Checking if bucket '{bucket_name}' exists...")
        start_time = time.time()
        exists = client.bucket_exists(bucket_name)
        end_time = time.time()
        print(f"   Result: {exists} (took {end_time - start_time:.2f}s)")

        if not exists:
            print(f"🔨 Making bucket '{bucket_name}'...")
            client.make_bucket(bucket_name)
            print("✅ Bucket created.")
        
        print("📤 Uploading test object...")
        import io
        data = b"Debug Data"
        client.put_object(
            bucket_name,
            "debug.txt",
            io.BytesIO(data),
            len(data)
        )
        print("✅ Upload successful.")

    except Exception as e:
        print(f"❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_minio()
