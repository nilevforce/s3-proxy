from fastapi import FastAPI, UploadFile, File, Header, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse, JSONResponse

import boto3
from botocore.exceptions import ClientError
from cuid2 import cuid_wrapper
import os

app = FastAPI()
create_cuid = cuid_wrapper()

# ---------------- S3 CLIENT ----------------

def get_s3_client(access, secret, endpoint, region=None):
    return boto3.client(
        "s3",
        aws_access_key_id=access,
        aws_secret_access_key=secret,
        endpoint_url=endpoint,
        region_name=region or "us-east-1",
    )

# ---------------- HEADERS DEPENDENCY ----------------

def get_headers(
    x_s3_access_key: str = Header(...),
    x_s3_secret_key: str = Header(...),
    x_s3_endpoint: str = Header(...),
    x_s3_bucket: str = Header(...),
    x_s3_region: str = Header(None),
):
    return {
        "access": x_s3_access_key,
        "secret": x_s3_secret_key,
        "endpoint": x_s3_endpoint,
        "bucket": x_s3_bucket,
        "region": x_s3_region,
    }

# ---------------- ERROR HANDLING ----------------

def handle_s3_error(e: ClientError):
    code = e.response["Error"]["Code"]

    if code in ["NoSuchKey", "404"]:
        raise HTTPException(404, "File not found")

    if code in ["AccessDenied"]:
        raise HTTPException(403, "Access denied")

    if code in ["InvalidAccessKeyId", "SignatureDoesNotMatch"]:
        raise HTTPException(401, "Invalid S3 credentials")

    raise HTTPException(500, f"S3 error: {code}")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "internal_error", "detail": str(exc)},
    )

# ---------------- UPLOAD ----------------

@app.post("/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    h=Depends(get_headers),
):
    client = get_s3_client(h["access"], h["secret"], h["endpoint"], h["region"])
    bucket = h["bucket"]

    cuid = create_cuid()
    ext = os.path.splitext(file.filename)[1]
    key = f"{cuid}{ext}"

    try:
        client.upload_fileobj(
            file.file,
            bucket,
            key,
            ExtraArgs={
                "ContentType": file.content_type or "application/octet-stream"
            },
        )
    except ClientError as e:
        handle_s3_error(e)

    return {
        "success": True,
        "bucket": bucket,
        "key": key,
    }

# ---------------- DOWNLOAD (STREAM) ----------------

@app.get("/files/{key}")
def download_file(key: str, h=Depends(get_headers)):
    client = get_s3_client(h["access"], h["secret"], h["endpoint"], h["region"])
    bucket = h["bucket"]

    try:
        obj = client.get_object(Bucket=bucket, Key=key)
    except ClientError as e:
        handle_s3_error(e)

    content_type = obj.get("ContentType", "application/octet-stream")

    def stream():
        for chunk in obj["Body"].iter_chunks(1024 * 1024):
            if chunk:
                yield chunk

    return StreamingResponse(
        stream(),
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{key}"'
        },
    )

# ---------------- DELETE ----------------

@app.delete("/files/{key}")
def delete_file(key: str, h=Depends(get_headers)):
    client = get_s3_client(h["access"], h["secret"], h["endpoint"], h["region"])
    bucket = h["bucket"]

    try:
        client.delete_object(Bucket=bucket, Key=key)
    except ClientError as e:
        handle_s3_error(e)

    return {
        "success": True,
        "key": key
    }

# ---------------- PRESIGN DOWNLOAD ----------------

@app.get("/files/{key}/presign")
def presign_download(
    key: str,
    expires_in: int = 900,
    h=Depends(get_headers),
):
    client = get_s3_client(h["access"], h["secret"], h["endpoint"], h["region"])

    try:
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": h["bucket"], "Key": key},
            ExpiresIn=expires_in,
        )
    except ClientError as e:
        handle_s3_error(e)

    return {
        "success": True,
        "url": url,
        "expires_in": expires_in
    }
