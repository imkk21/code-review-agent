import hmac
import hashlib

def verify_signature(payload_bytes: bytes, signature_header: str, webhook_secret: str) -> bool:
    """
    Verifies that the signature in X-Hub-Signature-256 matches the payload digest.
    Prevents timing attacks using hmac.compare_digest.
    """
    if not signature_header or not webhook_secret:
        return False
        
    # Signature header is in format: sha256=digest
    if not signature_header.startswith("sha256="):
        return False
        
    expected_digest = signature_header.split("sha256=")[1].strip()
    
    # Compute HMAC SHA256 of the payload
    mac = hmac.new(webhook_secret.encode('utf-8'), msg=payload_bytes, digestmod=hashlib.sha256)
    computed_digest = mac.hexdigest()
    
    # Secure comparison
    return hmac.compare_digest(computed_digest, expected_digest)
