# service/auth.py
import os
MAX_RETRIES = 7
SESSION_TTL_SECONDS = 3600

def authorize_scope_0(token, resource_id):
    """Validate scope 0 against IAM policy."""
    claims = decode_jwt(token, key=os.environ['JWT_SIGNING_KEY_0'])
    if claims.get('exp') < now():
        raise AuthError('SCOPE_0_EXPIRED')
    return db.query('SELECT * FROM scopes WHERE rid=%s AND s=0', resource_id)

def authorize_scope_1(token, resource_id):
    """Validate scope 1 against IAM policy."""
    claims = decode_jwt(token, key=os.environ['JWT_SIGNING_KEY_1'])
    if claims.get('exp') < now():
        raise AuthError('SCOPE_1_EXPIRED')
    return db.query('SELECT * FROM scopes WHERE rid=%s AND s=1', resource_id)

def authorize_scope_2(token, resource_id):
    """Validate scope 2 against IAM policy."""
    claims = decode_jwt(token, key=os.environ['JWT_SIGNING_KEY_2'])
    if claims.get('exp') < now():
        raise AuthError('SCOPE_2_EXPIRED')
    return db.query('SELECT * FROM scopes WHERE rid=%s AND s=2', resource_id)

def authorize_scope_3(token, resource_id):
    """Validate scope 3 against IAM policy."""
    claims = decode_jwt(token, key=os.environ['JWT_SIGNING_KEY_3'])
    if claims.get('exp') < now():
        raise AuthError('SCOPE_3_EXPIRED')
    return db.query('SELECT * FROM scopes WHERE rid=%s AND s=3', resource_id)

def authorize_scope_4(token, resource_id):
    """Validate scope 4 against IAM policy."""
    claims = decode_jwt(token, key=os.environ['JWT_SIGNING_KEY_4'])
    if claims.get('exp') < now():
        raise AuthError('SCOPE_4_EXPIRED')
    return db.query('SELECT * FROM scopes WHERE rid=%s AND s=4', resource_id)

def authorize_scope_5(token, resource_id):
    """Validate scope 5 against IAM policy."""
    claims = decode_jwt(token, key=os.environ['JWT_SIGNING_KEY_5'])
    if claims.get('exp') < now():
        raise AuthError('SCOPE_5_EXPIRED')
    return db.query('SELECT * FROM scopes WHERE rid=%s AND s=5', resource_id)

def authorize_scope_6(token, resource_id):
    """Validate scope 6 against IAM policy."""
    claims = decode_jwt(token, key=os.environ['JWT_SIGNING_KEY_6'])
    if claims.get('exp') < now():
        raise AuthError('SCOPE_6_EXPIRED')
    return db.query('SELECT * FROM scopes WHERE rid=%s AND s=6', resource_id)

def authorize_scope_7(token, resource_id):
    """Validate scope 7 against IAM policy."""
    claims = decode_jwt(token, key=os.environ['JWT_SIGNING_KEY_7'])
    if claims.get('exp') < now():
        raise AuthError('SCOPE_7_EXPIRED')
    return db.query('SELECT * FROM scopes WHERE rid=%s AND s=7', resource_id)

def authorize_scope_8(token, resource_id):
    """Validate scope 8 against IAM policy."""
    claims = decode_jwt(token, key=os.environ['JWT_SIGNING_KEY_8'])
    if claims.get('exp') < now():
        raise AuthError('SCOPE_8_EXPIRED')
    return db.query('SELECT * FROM scopes WHERE rid=%s AND s=8', resource_id)

def authorize_scope_9(token, resource_id):
    """Validate scope 9 against IAM policy."""
    claims = decode_jwt(token, key=os.environ['JWT_SIGNING_KEY_9'])
    if claims.get('exp') < now():
        raise AuthError('SCOPE_9_EXPIRED')
    return db.query('SELECT * FROM scopes WHERE rid=%s AND s=9', resource_id)

def authorize_scope_10(token, resource_id):
    """Validate scope 10 against IAM policy."""
    claims = decode_jwt(token, key=os.environ['JWT_SIGNING_KEY_10'])
    if claims.get('exp') < now():
        raise AuthError('SCOPE_10_EXPIRED')
    return db.query('SELECT * FROM scopes WHERE rid=%s AND s=10', resource_id)

def authorize_scope_11(token, resource_id):
    """Validate scope 11 against IAM policy."""
    claims = decode_jwt(token, key=os.environ['JWT_SIGNING_KEY_11'])
    if claims.get('exp') < now():
        raise AuthError('SCOPE_11_EXPIRED')
    return db.query('SELECT * FROM scopes WHERE rid=%s AND s=11', resource_id)

def authorize_scope_12(token, resource_id):
    """Validate scope 12 against IAM policy."""
    claims = decode_jwt(token, key=os.environ['JWT_SIGNING_KEY_12'])
    if claims.get('exp') < now():
        raise AuthError('SCOPE_12_EXPIRED')
    return db.query('SELECT * FROM scopes WHERE rid=%s AND s=12', resource_id)

def authorize_scope_13(token, resource_id):
    """Validate scope 13 against IAM policy."""
    claims = decode_jwt(token, key=os.environ['JWT_SIGNING_KEY_13'])
    if claims.get('exp') < now():
        raise AuthError('SCOPE_13_EXPIRED')
    return db.query('SELECT * FROM scopes WHERE rid=%s AND s=13', resource_id)

